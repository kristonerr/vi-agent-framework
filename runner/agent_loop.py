import json
import logging
from pathlib import Path
from . import mood_manager, queue_manager, memory_manager, event_logger
from . import reflection as ref
from . import analytics
from .memory_policy import MemoryPolicy
from .ollama_client import OllamaClient
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
        logging.info(f"Agent initialized with model: {model}")

    def _build_context(self) -> str:
        return memory_manager.get_all_context()

    def step(self, user_message: str) -> str:
        queue_data = queue_manager.read()
        if queue_data.get("text"):
            user_message = f"[QUEUE]: {queue_data['text']}\n\n(User also says: {user_message})"

        context = self._build_context()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"CURRENT CONTEXT:\n{context}\nMood: {self.mood.get('mood', 'neutral')}, energy: {self.mood.get('energy', 50)}"},
            {"role": "user", "content": user_message},
        ]

        raw = self.ollama.chat(messages, response_format="json")
        result = self._parse_json_response(raw)
        reply = result.get("reply", raw)

        tool_calls = result.get("tool_calls", [])
        for tc in tool_calls:
            fn = tool_registry.get(tc.get("name", ""))
            if fn:
                try:
                    fn(tc.get("arguments", {}))
                except Exception as e:
                    logging.warning(f"Tool {tc['name']} failed: {e}")

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

    def _parse_json_response(self, raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"reply": raw}
