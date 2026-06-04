import json
import logging
from pathlib import Path
from . import mood_manager, queue_manager, memory_manager, event_logger
from . import reflection as ref
from . import analytics
from .memory_policy import MemoryPolicy
from .ollama_client import OllamaClient
from .semantic_memory import SemanticMemory
from .tools import registry as tool_registry

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

SYSTEM_PROMPT = """You are a local AI agent. Follow the instructions in AGENTS.md.

Available tools:
- list_files(directory, pattern) — list files in a directory
- read_file(path) — read a file
- write_file(path, content) — write content to a file
- run_command(command) — execute a shell command (only if in allowlist)

You MUST respond in JSON format:
{
  "reply": "your text response to the user",
  "tool_calls": [
    {"name": "tool_name", "arguments": {"arg": "value"}}
  ],
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
        """ReAct цикл: вызывает LLM, выполняет tool_calls, повторяет пока есть вызовы."""
        max_iter = 5
        for _ in range(max_iter):
            raw = self.ollama.chat(messages, response_format="json")
            result = self._parse_json_response(raw)
            tool_calls = result.get("tool_calls", [])
            if not tool_calls:
                return result

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

        # fallback — последний ответ без tool_calls
        raw = self.ollama.chat(messages, response_format="json")
        return self._parse_json_response(raw)

    def _parse_json_response(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        if raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"reply": raw}
