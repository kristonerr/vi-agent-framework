"""Episodic memory — timeline of interactions with time awareness.

Each interaction is recorded with:
- date, time, weekday
- user message, agent response
- agent mood at the moment
- auto-tags (time of day, day type)

This lets the agent say things like:
"We haven't talked since Tuesday evening."
"Last time you were sad, it was nighttime."
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

EPISODIC_PATH = "episodic_memory.jsonl"
MAX_LINES = 5000
MAX_CONTEXT = 10

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

TIME_OF_DAY = [
    (0, 5, "night"),
    (6, 8, "morning"),
    (9, 11, "late_morning"),
    (12, 14, "afternoon"),
    (15, 17, "mid_afternoon"),
    (18, 20, "evening"),
    (21, 23, "late_evening"),
]


def _time_of_day(hour: int) -> str:
    for start, end, label in TIME_OF_DAY:
        if start <= hour <= end:
            return label
    return "night"


def _weekday_name(dt: datetime) -> str:
    return WEEKDAYS[dt.weekday()]


def _classify_day(weekday: int) -> str:
    return "weekend" if weekday >= 5 else "workday"


class EpisodicMemory:
    def __init__(self, root: Optional[Path] = None):
        if root is None:
            root = Path(__file__).parent.parent
        self.path: Path = root / EPISODIC_PATH

    def record(self, user_message: str, agent_response: str, mood: str, energy: int, tags: list[str] | None = None):
        now = datetime.now()
        entry = {
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "hour": now.hour,
            "weekday": _weekday_name(now),
            "day_type": _classify_day(now.weekday()),
            "time_of_day": _time_of_day(now.hour),
            "user": user_message[:200],
            "agent": agent_response[:500],
            "mood": mood,
            "energy": energy,
            "tags": tags or [],
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._rotate_if_needed()
        except Exception as e:
            logger.warning(f"Failed to record episodic memory: {e}")

    def recent(self, limit: int = MAX_CONTEXT) -> list[dict]:
        """Return last N episodes."""
        if not self.path.exists():
            return []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            result = []
            for l in lines[-limit:]:
                try:
                    result.append(json.loads(l))
                except json.JSONDecodeError:
                    continue
            return result
        except Exception:
            return []

    def get_context_string(self, limit: int = MAX_CONTEXT) -> str:
        """Build a human-readable timeline for the system prompt."""
        episodes = self.recent(limit)
        if not episodes:
            return ""

        lines = ["--- RECENT INTERACTIONS (timeline) ---"]
        for e in episodes:
            ts = e.get("timestamp", "?")
            tag = e.get("time_of_day", "?")
            wd = e.get("weekday", "?")
            mood = e.get("mood", "?")
            msg = e.get("user", "")[:80]
            lines.append(f"[{ts}] {wd}, {tag} | you: {msg} | mood: {mood}")

        return "\n".join(lines)

    def time_since_last(self) -> str:
        """Human-readable time since last interaction."""
        episodes = self.recent(1)
        if not episodes:
            return "no history"
        try:
            last_ts = episodes[0].get("timestamp", "")
            last_dt = datetime.fromisoformat(last_ts)
            delta = datetime.now() - last_dt
            secs = int(delta.total_seconds())
            if secs < 60:
                return "just now"
            if secs < 3600:
                return f"{secs // 60} minutes ago"
            if secs < 86400:
                return f"{secs // 3600} hours ago"
            days = secs // 86400
            return f"{days} day{'s' if days > 1 else ''} ago"
        except Exception:
            return "recently"

    def _rotate_if_needed(self):
        if not self.path.exists():
            return
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            if len(lines) > MAX_LINES:
                with open(self.path, "w", encoding="utf-8") as f:
                    f.writelines(f"{l}\n" for l in lines[-MAX_LINES // 2:])
                logger.info(f"Episodic memory rotated to {MAX_LINES // 2} lines")
        except Exception as e:
            logger.warning(f"Episodic rotation failed: {e}")

    def count(self) -> int:
        if not self.path.exists():
            return 0
        try:
            return len(self.path.read_text(encoding="utf-8").splitlines())
        except Exception:
            return 0

    def get_stats_string(self, limit: int = 100) -> str:
        """Human-readable stats summary for context."""
        episodes = self.recent(limit)
        if not episodes:
            return ""
        by_day = {}
        by_time = {}
        for e in episodes:
            wd = e.get("weekday", "?")
            by_day[wd] = by_day.get(wd, 0) + 1
            tod = e.get("time_of_day", "?")
            by_time[tod] = by_time.get(tod, 0) + 1

        most_day = max(by_day, key=by_day.get) if by_day else "?"
        most_time = max(by_time, key=by_time.get) if by_time else "?"
        last = self.time_since_last()
        total = self.count()

        return (
            f"--- EPISODIC STATS ---\n"
            f"Total episodes: {total} | Last: {last}\n"
            f"Most active day: {most_day} | Most active time: {most_time}"
        )

    def stats(self) -> dict:
        """Return stats about recent interactions."""
        episodes = self.recent(100)
        if not episodes:
            return {"total": 0}

        by_day = {}
        by_time = {}
        for e in episodes:
            wd = e.get("weekday", "?")
            by_day[wd] = by_day.get(wd, 0) + 1
            tod = e.get("time_of_day", "?")
            by_time[tod] = by_time.get(tod, 0) + 1

        return {
            "total": self.count(),
            "recent": len(episodes),
            "last": self.time_since_last(),
            "by_weekday": by_day,
            "by_time_of_day": by_time,
            "most_active_day": max(by_day, key=by_day.get) if by_day else "?",
            "most_active_time": max(by_time, key=by_time.get) if by_time else "?",
        }
