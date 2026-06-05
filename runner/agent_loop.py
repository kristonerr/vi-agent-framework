import json
import logging
import re
from pathlib import Path
from . import mood_manager, queue_manager, memory_manager, event_logger
from . import reflection as ref
from . import analytics
from .memory_policy import MemoryPolicy
from .ollama_client import OllamaClient
from .semantic_memory import SemanticMemory
from .tools import registry as tool_registry

MAX_CONTEXT_TOKENS = 4096


def estimate_tokens(text: str) -> int:
    return len(text) // 2


def trim_context(messages: list[dict], max_tokens: int = MAX_CONTEXT_TOKENS) -> list[dict]:
    total = 0
    trimmed = []
    for msg in reversed(messages):
        tokens = estimate_tokens(msg.get("content", ""))
        if total + tokens > max_tokens:
            continue
        total += tokens
        trimmed.insert(0, msg)
    return trimmed


def normalize_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()
    raw = raw.replace("'", '"')
    raw = re.sub(r'(?<!\\)"(.*?)"(?=\s*:)', lambda m: '"' + m.group(1) + '"', raw)
    return raw


TOOL_PRIORITY = {"read_file": 0, "list_files": 1, "write_file": 2, "run_command": 3}


def sort_tool_calls(tool_calls: list[dict]) -> list[dict]:
    return sorted(tool_calls, key=lambda tc: TOOL_PRIORITY.get(tc.get("name", ""), 99))


SYSTEM_PROMPT = """You are a local AI agent. Follow the instructions in AGENTS.md.

Available tools:
- list_files(directory, pattern) — list files in a directory
- read_file(path) — read a file
- write_file(path, content) — write content to a file
- run_command(command) — execute a shell command (only if in allowlist)

If you want to run a command NOT in the allowlist, you can request permission:
{
  "request_permission": {"command": "pip install pandas", "reason": "Need it for data analysis"}
}
The user will decide. Always explain why you need it.

Otherwise respond in JSON:
{
  "reply": "your text response to the user",
  "tool_calls": [
    {"name": "tool_name", "arguments": {"arg": "value"}}
  ],
  "request_permission": {"command": "...", "reason": "..."} | null,
  "memory_updates": [
    {"type": "fact", "content": "something new about the user"}
  ],
  "mood_update": {"mood": "happy", "energy": 80} | null
}

Always confirm before destructive operations."""


class AgentLoop:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.ollama = OllamaClient(base_url, model)
        self.mood = mood_manager.load()
        self.agent_root = Path(__file__).parent.parent.resolve()
        self.memory_policy = MemoryPolicy(ollama=self.ollama)
        self.semantic = SemanticMemory(ollama_client=self.ollama)
        logging.info(f"Agent initialized with model: {model}")

    def _build_context(self, user_message: str = "") -> str:
        base = memory_manager.get_all_context()
        associations = self.semantic.associate(user_message)
        if associations:
            base += "\n\n" + associations
        return base

    def step(self, user_message: str) -> str:
        queue_data = queue_manager.read()
        if queue_data.get("text"):
            user_message = f"[QUEUE]: {queue_data['text']}\n\n(User also says: {user_message})"

        context = self._build_context(user_message)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"CURRENT CONTEXT:\n{context}\nMood: {self.mood.get('mood', 'neutral')}, energy: {self.mood.get('energy', 50)}"},
            {"role": "user", "content": user_message},
        ]

        messages = trim_context(messages)
        result = self._chat_with_tools(messages)

        for mu in result.get("memory_updates", []):
            if mu.get("type") == "fact":
                memory_manager.append_memory(mu["content"])
            elif mu.get("type") == "lesson":
                memory_manager.append_lesson(mu["content"])

        mood_upd = result.get("mood_update")
        if mood_upd:
            mood_manager.update(mood_upd)

        if queue_data.get("text"):
            queue_manager.clear()

        reply = result.get("reply", "")

        event_logger.append("interaction", {"user": user_message, "assistant": reply})
        analytics.record_interaction(user_message, reply, self.mood)

        memory_manager.append_to_session_buffer({
            "role": "user", "content": user_message, "type": "interaction"
        })
        transferred = self.memory_policy.consolidate()
        if transferred:
            logging.info(f"Consolidated {transferred} items to long-term memory")

        insight = ref.reflect(user_message, reply, self.ollama)
        if insight:
            logging.info(f"Insight: {insight}")

        self.mood = mood_manager.load()
        return reply

    def _chat_with_tools(self, messages: list) -> dict:
        max_iter = 5
        session_allowlist = []

        for iteration in range(max_iter):
            raw = self.ollama.chat(messages, response_format="json")
            result = self._parse_json_response(raw)

            perm = result.get("request_permission")
            if perm:
                cmd = perm.get("command", "")
                reason = perm.get("reason", "")
                print(f"\n🔐 Вика хочет выполнить команду:\n   {cmd}\n   Причина: {reason}")
                answer = input("   Разрешить? (y/n): ").strip().lower()
                if answer in ("y", "yes"):
                    session_allowlist.append(cmd.split()[0])
                    messages.append({
                        "role": "user",
                        "content": f"Permission granted for: {cmd}",
                    })
                    from .tools import registry as tr
                    tr._session_allowlist = session_allowlist
                    import shlex
                    cmd_list = shlex.split(cmd)
                    try:
                        import subprocess
                        sub_result = subprocess.run(cmd_list, shell=False, capture_output=True, text=True, timeout=30)
                        output = sub_result.stdout + sub_result.stderr
                        messages.append({
                            "role": "tool",
                            "name": "run_command",
                            "content": json.dumps({"success": True, "output": output[:1000]}, ensure_ascii=False),
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "name": "run_command",
                            "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                        })
                else:
                    messages.append({
                        "role": "user",
                        "content": f"Permission denied for: {cmd}",
                    })
                continue

            tool_calls = result.get("tool_calls", [])
            if not tool_calls:
                return result

            tool_calls = sort_tool_calls(tool_calls)

            for tc in tool_calls:
                fn = tool_registry.get(tc.get("name", ""))
                if fn:
                    try:
                        tool_result = fn(tc.get("arguments", {}))
                        messages.append({
                            "role": "tool",
                            "content": json.dumps(tool_result, ensure_ascii=False),
                            "name": tc["name"],
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "content": json.dumps({"error": str(e)}, ensure_ascii=False),
                            "name": tc["name"],
                        })
                else:
                    messages.append({
                        "role": "tool",
                        "content": json.dumps({"error": f"unknown tool: {tc.get('name')}"}),
                        "name": tc.get("name", "?"),
                    })

            messages = trim_context(messages)

        raw = self.ollama.chat(messages, response_format="json")
        return self._parse_json_response(raw)

    def _parse_json_response(self, raw: str) -> dict:
        raw = normalize_json(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"reply": raw}
