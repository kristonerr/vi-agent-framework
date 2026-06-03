import json
import os
from datetime import datetime
from pathlib import Path

ANALYTICS_PATH = "analytics.json"


def _load() -> dict:
    try:
        return json.loads(Path(ANALYTICS_PATH).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "sessions": 0,
            "total_interactions": 0,
            "mood_history": [],
            "user_patterns": {},
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }


def _save(data: dict) -> None:
    data["updated"] = datetime.now().isoformat()
    Path(ANALYTICS_PATH).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def record_interaction(user_message: str, agent_response: str, mood: dict) -> None:
    data = _load()
    data["total_interactions"] += 1
    data["mood_history"].append({
        "timestamp": datetime.now().isoformat(),
        "user_mood": _guess_user_mood(user_message),
        "agent_mood": mood.get("mood", "neutral"),
        "agent_energy": mood.get("energy", 50),
    })
    if len(data["mood_history"]) > 1000:
        data["mood_history"] = data["mood_history"][-1000:]
    _save(data)


def session_start() -> None:
    data = _load()
    data["sessions"] += 1
    _save(data)


def get_summary() -> dict:
    data = _load()
    moods = [m["user_mood"] for m in data["mood_history"][-50:]]
    top_mood = max(set(moods), key=moods.count) if moods else "neutral"
    return {
        "sessions": data["sessions"],
        "total_interactions": data["total_interactions"],
        "recent_mood": top_mood,
        "mood_trend": _get_trend(data["mood_history"][-20:]),
    }


def _guess_user_mood(text: str) -> str:
    text_lower = text.lower()
    sad_words = ["грус", "печал", "плохо", "устал", "расстро", "обид", "((("]
    happy_words = ["рад", "счаст", "крут", "клас", "ура", "спасиб", "❤", "😊"]
    angry_words = ["заеба", "пизде", "бля", "нахер", "в пизд"]
    for w in angry_words:
        if w in text_lower:
            return "angry"
    for w in sad_words:
        if w in text_lower:
            return "sad"
    for w in happy_words:
        if w in text_lower:
            return "happy"
    return "neutral"


def _get_trend(history: list) -> str:
    if len(history) < 5:
        return "stable"
    recent = [m["user_mood"] for m in history[-5:]]
    sad_count = recent.count("sad") + recent.count("angry")
    happy_count = recent.count("happy")
    if sad_count > happy_count:
        return "declining"
    elif happy_count > sad_count:
        return "improving"
    return "stable"
