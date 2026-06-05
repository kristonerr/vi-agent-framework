import json
import logging
import os
from datetime import datetime
from . import file_manager

EVENTS_PATH = "events.jsonl"
MAX_LOG_SIZE = 5 * 1024 * 1024
MAX_LINES_KEEP = 1000


def _rotate_if_needed():
    if not os.path.exists(EVENTS_PATH):
        return
    try:
        size = os.path.getsize(EVENTS_PATH)
        if size < MAX_LOG_SIZE:
            return
        with open(EVENTS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) <= MAX_LINES_KEEP:
            return
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines[-MAX_LINES_KEEP:])
        archive_path = EVENTS_PATH.replace(".jsonl", ".archive.jsonl")
        with open(archive_path, "a", encoding="utf-8") as f:
            f.writelines(lines[:-MAX_LINES_KEEP])
    except Exception as e:
        logging.warning(f"Log rotation failed: {e}")


def append(event_type: str, data: dict) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data,
    }
    _rotate_if_needed()
    with open(EVENTS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
