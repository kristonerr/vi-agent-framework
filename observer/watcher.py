"""Active window monitor — reads only the window title, nothing else.
Safe: no keystrokes, no screenshots, no content.

Uses Windows API via ctypes.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ACTIVITY_LOG = "activity_log.jsonl"
POLL_INTERVAL = 5
MAX_BATCH = 50

# --- Windows API (ctypes) ---

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
GetForegroundWindow = user32.GetForegroundWindow
GetWindowTextLengthW = user32.GetWindowTextLengthW
GetWindowTextW = user32.GetWindowTextW
GetWindowThreadProcessId = user32.GetWindowThreadProcessId


def _get_active_window_title() -> Optional[str]:
    hwnd = GetForegroundWindow()
    if not hwnd:
        return "(desktop)"
    length = GetWindowTextLengthW(hwnd) + 1
    if length <= 1:
        return "(desktop)"
    buf = ctypes.create_unicode_buffer(length)
    GetWindowTextW(hwnd, buf, length)
    return buf.value.strip() or "(desktop)"


def _sanitize(title: str) -> str:
    """Remove non-printable characters, limit length."""
    clean = "".join(c for c in title if c.isprintable())
    return clean[:120]


def get_active_window() -> dict:
    """Return safe window info dict."""
    raw = _get_active_window_title()
    title = _sanitize(raw) if raw else "(desktop)"
    return {
        "title": title,
        "timestamp": datetime.now().isoformat(),
    }


# --- Потоковый мониторинг ---

def _log_path(root: Path) -> Path:
    return root / ACTIVITY_LOG


def _append(entry: dict, root: Path):
    with open(_log_path(root), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _rotate_if_big(root: Path):
    path = _log_path(root)
    if not path.exists():
        return
    try:
        size = path.stat().st_size
        if size < 2 * 1024 * 1024:
            return
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= 1000:
            return
        archive = path.with_suffix(".archive.jsonl")
        with open(archive, "a", encoding="utf-8") as a:
            for l in lines[:-500]:
                a.write(l + "\n")
        path.write_text("\n".join(lines[-500:]), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Log rotation failed: {e}")


def watch(interval: int = POLL_INTERVAL, root: Optional[Path] = None, callback=None):
    """Run watcher loop: every `interval` seconds log active window.
    
    If callback is provided, call it with (new_title, prev_title) on change.
    """
    if root is None:
        root = Path(__file__).parent.parent
    last_title = None
    logger.info(f"Watcher started (interval={interval}s)")

    while True:
        try:
            info = get_active_window()
            title = info["title"]

            if title != last_title:
                _append(info, root)
                logger.debug(f"Active window: {title}")
                if callback and last_title is not None:
                    try:
                        callback(title, last_title)
                    except Exception as e:
                        logger.warning(f"Watcher callback failed: {e}")
                last_title = title
                _rotate_if_big(root)

            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Watcher stopped")
            break
        except Exception as e:
            logger.warning(f"Watcher error: {e}")
            time.sleep(interval)


# --- Чтение лога активности ---

def read_activity(root: Optional[Path] = None, limit: int = 100) -> list[dict]:
    if root is None:
        root = Path(__file__).parent.parent
    path = _log_path(root)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    entries = []
    for l in lines[-limit:]:
        try:
            entries.append(json.loads(l))
        except json.JSONDecodeError:
            continue
    return entries


def get_recent_themes(root: Optional[Path] = None, window: int = 50) -> list[str]:
    """Extract unique non-trivial window titles from recent activity."""
    entries = read_activity(root, limit=window)
    seen = set()
    themes = []
    for e in entries:
        title = e.get("title", "")
        if title.lower() in seen:
            continue
        seen.add(title.lower())
        themes.append(title)
    return themes


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    watch()
