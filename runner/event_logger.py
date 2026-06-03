import json
from datetime import datetime
from . import file_manager

EVENTS_PATH = "events.jsonl"


def append(event_type: str, data: dict) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data,
    }
    with open(EVENTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
