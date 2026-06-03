import json
from datetime import datetime
from . import file_manager

MOOD_PATH = "mood.json"

DEFAULT_MOOD = {
    "mood": "neutral",
    "emoji": "",
    "energy": 50,
    "note": "",
    "updated": datetime.now().strftime("%Y-%m-%dT%H:%M"),
}


def load() -> dict:
    try:
        raw = file_manager.read(MOOD_PATH)
        return json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_MOOD)


def save(mood_data: dict) -> None:
    mood_data["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
    file_manager.write(MOOD_PATH, json.dumps(mood_data, ensure_ascii=False, indent=2))
