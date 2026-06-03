from . import mood_manager, queue_manager, memory_manager, event_logger
from . import reflection as ref
from . import analytics
from .ollama_client import OllamaClient
from .tools import registry as tool_registry

SYSTEM_PROMPT = """You are a local AI agent. Follow the instructions in AGENTS.md.

Available tools:
- list_files(directory, pattern) — list files in a directory
- read_file(path) — read a file
- write_file(path, content) — write content to a file
- run_command(command) — execute a shell command (only if in allowlist)

You can respond with text or call a tool. Format tool calls as:
TOOL_CALL: tool_name | {"arg": "value"}

Always confirm before destructive operations."""


class AgentLoop:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.ollama = OllamaClient(base_url, model)
        self.mood = mood_manager.load()

    def step(self, user_message: str) -> str:
        queue_manager.read()
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"[Current mood: {self.mood.get('mood', 'neutral')}, energy: {self.mood.get('energy', 50)}]\n{user_message}"},
        ]
        response = self.ollama.chat(messages)
        response = self._handle_tool_calls(response)
        event_logger.append("interaction", {"user": user_message, "assistant": response})
        analytics.record_interaction(user_message, response, self.mood)
        insight = ref.reflect(user_message, response, self.ollama)
        self.mood = mood_manager.load()
        return response

    def _handle_tool_calls(self, response: str) -> str:
        lines = response.strip().split("\n")
        output = []
        for line in lines:
            if line.startswith("TOOL_CALL:"):
                parts = line[len("TOOL_CALL:"):].strip().split("|", 1)
                tool_name = parts[0].strip()
                args = {}
                if len(parts) > 1:
                    import json as _json
                    try:
                        args = _json.loads(parts[1].strip())
                    except _json.JSONDecodeError:
                        args = {"raw": parts[1].strip()}
                tool_fn = tool_registry.get(tool_name)
                if tool_fn:
                    result = tool_fn(args)
                    output.append(f"  → {tool_name}: {result}")
                else:
                    output.append(f"  → unknown tool: {tool_name}")
            else:
                output.append(line)
        return "\n".join(output)
