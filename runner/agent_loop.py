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
from .mcp_client import MCPClient, register_mcp_servers
from . import health as health_mod

MCP_TOOL_PREFIX = "mcp_"

def _load_max_context_tokens() -> int:
    cfg_path = Path(__file__).parent.parent / "config.json"
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return int(cfg.get("max_context_tokens", 4096))
    except Exception:
        return 4096


def estimate_tokens(text: str) -> int:
    return len(text.encode("utf-8")) // 4


MAX_CONTEXT_TOKENS = _load_max_context_tokens()


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


def _build_system_prompt() -> str:
    prompt = "You are a local AI agent."
    agents_md = Path(__file__).parent.parent / "AGENTS.md"
    if agents_md.exists():
        prompt += "\n\n" + agents_md.read_text(encoding="utf-8")
    prompt += """

Available tools:
- list_files(directory, pattern) — list files in a directory
- read_file(path) — read a file
- write_file(path, content) — write content to a file
- run_command(command) — execute a shell command (only if in allowlist)
- web_search(query, max_results) — search the web via DuckDuckGo (no API key needed)
- mcp_<tool_name>(args) — MCP-connected tools from external servers (use tools/list to see available ones)

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
    return prompt


SYSTEM_PROMPT = _build_system_prompt()


class AgentLoop:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.ollama = OllamaClient(base_url, model)
        self.mood = mood_manager.load()
        self.agent_root = Path(__file__).parent.parent.resolve()
        self.memory_policy = MemoryPolicy(ollama=self.ollama)
        self.semantic = SemanticMemory(ollama_client=self.ollama)
        self.mcp = register_mcp_servers()
        self._mcp_tool_names: list[str] = []
        self._mode = health_mod.current_mode()
        self._history: list[dict] = []
        self._max_history = 6
        self._temperature = 0.7
        cfg_path = self.agent_root / "config.json"
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            self._temperature = float(cfg.get("temperature", 0.7))
        except Exception:
            pass
        for name, server in self.mcp.servers.items():
            for tool in server.list_tools():
                self._mcp_tool_names.append(f"{MCP_TOOL_PREFIX}{tool['name']}")
        self._startup_health_check()
        logging.info(f"Agent initialized with model: {model}" + (f", MCP servers: {list(self.mcp.servers.keys())}" if self.mcp.servers else "") + f" mode={self._mode}")

    def _startup_health_check(self):
        check = health_mod.checkup()
        if self._mode == "readonly":
            logging.warning("Agent in READONLY mode — tools and memory updates disabled")
        if not health_mod.disk_ok():
            logging.warning("Low disk space, rotating old backups")
            self._rotate_backups_if_needed()
        health_mod.backup_state()

    def _rotate_backups_if_needed(self):
        import shutil
        bdir = self.agent_root / "backups"
        if bdir.exists():
            backups = sorted(bdir.iterdir())
            while len(backups) > 5:
                shutil.rmtree(backups.pop(0))

    def _mcp_context(self) -> str:
        if not self.mcp.servers:
            return ""
        lines = ["\n--- MCP Tools ---"]
        for name, server in self.mcp.servers.items():
            lines.append(f"[{name}]")
            try:
                for tool in server.list_tools():
                    desc = tool.get("description", "").replace("\n", " ")
                    lines.append(f"  - mcp_{tool['name']}: {desc}")
            except Exception as e:
                logging.warning(f"MCP server [{name}] failed to list tools: {e}")
        return "\n".join(lines)

    def _build_context(self, user_message: str = "") -> str:
        base = memory_manager.get_all_context()
        associations = self.semantic.associate(user_message)
        if associations:
            base += "\n\n" + associations
        mcp_part = self._mcp_context()
        if mcp_part:
            base += "\n\n" + mcp_part
        return base

    def step(self, user_message: str) -> str:
        self._mode = health_mod.current_mode()

        queue_data = queue_manager.read()
        if queue_data.get("text"):
            user_message = f"[QUEUE]: {queue_data['text']}\n\n(User also says: {user_message})"

        if self._mode == "readonly":
            return "Извини, я в аварийном режиме. Состояние повреждено, инструменты отключены. Попробуй позже."

        context = self._build_context(user_message)
        mode_note = f"\n[Mode: {self._mode}]" if self._mode != "normal" else ""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"CURRENT CONTEXT:\n{context}{mode_note}\nMood: {self.mood.get('mood', 'neutral')}, energy: {self.mood.get('energy', 50)}"},
        ]

        for h in self._history[-self._max_history:]:
            messages.append(h)

        messages.append({"role": "user", "content": user_message})

        messages = trim_context(messages)
        result = self._chat_with_tools(messages)

        if self._mode != "readonly":
            memory_updates = list(result.get("memory_updates", []))

            insight = ref.reflect(user_message, result.get("reply", ""), self.ollama)
            if insight:
                memory_updates.append(insight)
                logging.info(f"Reflection: {insight['type']}: {insight['content']}")

            review = ref.self_review(user_message, result.get("reply", ""), self.ollama)
            if review:
                memory_updates.append(review)
                logging.info(f"Self-review: {review['content']}")

            for mu in memory_updates:
                if mu.get("type") == "fact":
                    memory_manager.append_memory(mu["content"], importance=mu.get("importance", 5))
                elif mu.get("type") == "lesson":
                    memory_manager.append_lesson(mu["content"], importance=mu.get("importance", 5))

            mood_upd = result.get("mood_update")
            if mood_upd:
                mood_manager.update(mood_upd)

        if queue_data.get("text"):
            queue_manager.clear()

        reply = result.get("reply", "")

        self._history.append({"role": "user", "content": user_message})
        self._history.append({"role": "assistant", "content": reply})

        if len(self._history) > self._max_history * 2:
            self._history = self._history[-self._max_history:]

        event_logger.append("interaction", {"user": user_message, "assistant": reply})
        analytics.record_interaction(user_message, reply, self.mood)

        if self._mode != "readonly":
            memory_manager.append_to_session_buffer({
                "role": "user", "content": user_message, "type": "interaction"
            })
            transferred = self.memory_policy.consolidate()
            if transferred:
                logging.info(f"Consolidated {transferred} items to long-term memory")

        self.mood = mood_manager.load()
        return reply

    def _maybe_recover(self) -> bool:
        corrupted = health_mod.verify_state()
        if not corrupted:
            return True
        repaired = health_mod.repair_state()
        if repaired:
            health_mod.change_mode("safe")
            self._mode = "safe"
            logging.info(f"Repaired {repaired}, entering safe mode")
            return True
        health_mod.change_mode("readonly")
        self._mode = "readonly"
        logging.error("Could not repair state, entering readonly mode")
        return False

    def close(self):
        self.mcp.stop_all()

    def _chat_with_tools(self, messages: list) -> dict:
        max_iter = 5
        max_retries = 3
        session_allowlist = []

        for iteration in range(max_iter):
            raw = None
            result = None
            for attempt in range(max_retries):
                try:
                    raw = self.ollama.chat(messages, temperature=self._temperature, response_format="json")
                    result = self._parse_json_response(raw)
                    if "reply" in result or "tool_calls" in result or "request_permission" in result:
                        break
                    logging.warning(f"Parse attempt {attempt + 1} failed, retrying...")
                except Exception as e:
                    logging.warning(f"Ollama error attempt {attempt + 1}: {e}")
                    result = None
            if result is None:
                return {"reply": "Извини, не смогла обработать ответ. Попробуй переформулировать."}

            perm = result.get("request_permission")
            if perm:
                cmd = perm.get("command", "")
                reason = perm.get("reason", "")
                print(f"\n🔐 Вика хочет выполнить команду:\n   {cmd}\n   Причина: {reason}")
                answer = input("   Разрешить? (y/n): ").strip().lower()
                if answer in ("y", "yes"):
                    tool_registry._session_allowlist.add(cmd)
                    messages.append({
                        "role": "user",
                        "content": f"Permission granted for: {cmd}",
                    })
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
                tool_result = tool_registry.call_with_resilience(tc.get("name", ""), tc.get("arguments", {}))
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                    "name": tc.get("name", "?"),
                })

            messages = trim_context(messages)

        try:
            raw = self.ollama.chat(messages, temperature=self._temperature, response_format="json")
            return self._parse_json_response(raw)
        except Exception as e:
            logging.error(f"Final chat failed after max_iter: {e}")
            return {"reply": "Извини, не смогла обработать. Попробуй ещё раз."}

    def _parse_json_response(self, raw: str) -> dict:
        raw = normalize_json(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"reply": raw}
