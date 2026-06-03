import sys
import json
from . import mood_manager, queue_manager, memory_manager, event_logger, analytics
from .agent_loop import AgentLoop

import_dir = "tools"
if import_dir not in sys.modules:
    from .tools import list_files, read_file, write_file, run_command


def main():
    config_path = "config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.loads(f.read())
    except FileNotFoundError:
        config = {"model": "qwen2.5:7b", "base_url": "http://localhost:11434"}

    agent = AgentLoop(model=config.get("model", "qwen2.5:7b"), base_url=config.get("base_url", "http://localhost:11434"))

    if not agent.ollama.ping():
        print("Ollama is not running. Start it first.")
        sys.exit(1)

    print(f"vi-agent-framework | model: {agent.ollama.model}")
    print("---")

    queue = queue_manager.read()
    if queue.get("text"):
        print(f"[queue] {queue['text']}")
        queue_manager.clear()

    memory = memory_manager.read_memory()
    print(f"[memory] {len(memory)} chars loaded")

    mood = mood_manager.load()
    print(f"[mood] {mood.get('mood', 'neutral')} | energy {mood.get('energy', 50)}")

    analytics.session_start()

    stats = analytics.get_summary()
    print(f"[analytics] {stats['sessions']} sessions, {stats['total_interactions']} total interactions")
    print(f"[analytics] recent mood: {stats['recent_mood']} | trend: {stats['mood_trend']}")

    event_logger.append("session_start", {"config": config})

    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        response = agent.step(user_input)
        print(response)
        return

    print("\nInteractive mode. Type 'exit' to quit.\n")
    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if user_input.lower() in ("exit", "quit"):
            event_logger.append("session_end", {})
            break
        response = agent.step(user_input)
        print(response)


if __name__ == "__main__":
    main()
