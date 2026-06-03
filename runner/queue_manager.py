import json
from . import file_manager

QUEUE_PATH = "queue.json"


def read() -> dict:
    try:
        raw = file_manager.read(QUEUE_PATH)
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def clear() -> None:
    file_manager.write(QUEUE_PATH, "{}")
