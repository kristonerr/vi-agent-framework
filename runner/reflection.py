"""Self-reflection module for vi-agent.

Two modes:
1. **reflect()** — insight about the user (mood, needs, patterns). Writes to memory/intuition.
2. **self_review()** — quality assessment of own response. Finds mistakes, logs lessons.
"""

from datetime import datetime
from . import event_logger
from .ollama_client import OllamaClient


def reflect(user_message: str, agent_response: str, ollama: OllamaClient) -> dict | None:
    """After each interaction, returns an insight dict about the user or None.
    
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


def self_review(user_message: str, agent_response: str, ollama: OllamaClient) -> dict | None:
    """Evaluate the quality of own response. Returns a lesson if improvement needed.
    
    Checks:
    - Was the response helpful and on-topic?
    - Tone — right for the user's mood?
    - Structure — JSON format correct?
    - Facts — any hallucination risk?
    - Overall — what could be better next time?
    
    Returns:
        {"type": "lesson", "content": "..."} if improvement found, or None
    """
    prompt = f"""You are a self-improving AI assistant. Review your own last response.

User message: {user_message}
Your response: {agent_response}

Evaluate on a scale 1-10:
1. RELEVANCE — did you answer the actual question?
2. TONE — was your tone appropriate for the user's mood?
3. ACCURACY — any risk of incorrect facts?
4. HELPFULNESS — did you actually help or just talk?

If any score is below 7 OR you spot a clear mistake, output:
TYPE: lesson
TEXT: what you learned and how to improve next time (1 sentence in Russian)

If everything is good, just say "no insight"."""

    try:
        result = ollama.chat([{"role": "user", "content": prompt}], temperature=0.2)
        lines = [l.strip() for l in result.strip().split("\n")]
        insight_type = "none"
        insight_text = ""
        for l in lines:
            if l.startswith("TYPE:"):
                insight_type = l.replace("TYPE:", "").strip()
            elif l.startswith("TEXT:"):
                insight_text = l.replace("TEXT:", "").strip()

        if insight_type == "lesson" and insight_text:
            event_logger.append("self_review", {"text": insight_text})
            return {"type": "lesson", "content": f"[self-review] {insight_text}"}
    except Exception:
        pass

    return None
