from datetime import datetime
from . import event_logger
from .ollama_client import OllamaClient


def reflect(user_message: str, agent_response: str, ollama: OllamaClient) -> dict | None:
    """After each interaction, returns an insight dict or None.
    
    Returns:
        {"type": "fact" | "lesson", "content": "..."} or None
    """
    prompt = f"""You are a self-improving agent. Based on this interaction, write ONE short insight (1-2 sentences) if anything worth learning emerged.

User: {user_message}
You: {agent_response}

If there's a useful lesson about the user (mood, preference, habit, need), write it as a fact for memory.md.
If there's a lesson about yourself (mistake, improvement, pattern), write it for lessons.md.
If nothing notable, just say "no insight".

Format:
TYPE: memory | lesson | none
TEXT: ..."""

    try:
        result = ollama.chat([{"role": "user", "content": prompt}], temperature=0.3)
        lines = [l.strip() for l in result.strip().split("\n")]
        insight_type = "none"
        insight_text = ""
        for l in lines:
            if l.startswith("TYPE:"):
                insight_type = l.replace("TYPE:", "").strip()
            elif l.startswith("TEXT:"):
                insight_text = l.replace("TEXT:", "").strip()

        if insight_type in ("memory", "lesson") and insight_text:
            mapped = {"memory": "fact", "lesson": "lesson"}
            event_logger.append("reflection", {"type": insight_type, "text": insight_text})
            return {"type": mapped[insight_type], "content": insight_text}
    except Exception:
        pass

    return None
