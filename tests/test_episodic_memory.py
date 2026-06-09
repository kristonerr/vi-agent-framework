"""Tests for EpisodicMemory — timeline with time awareness."""
import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))


def test_import():
    from runner.episodic_memory import EpisodicMemory, _time_of_day, _weekday_name, _classify_day
    from datetime import datetime
    assert EpisodicMemory
    assert _time_of_day(10) == "late_morning"
    assert _time_of_day(3) == "night"
    assert _time_of_day(14) == "afternoon"
    # _weekday_name expects a datetime, not an int
    assert _weekday_name(datetime(2026, 6, 8)) == "Monday"   # 2026-06-08 is Monday
    assert _weekday_name(datetime(2026, 6, 14)) == "Sunday"  # 2026-06-14 is Sunday
    assert _classify_day(5) == "weekend"
    assert _classify_day(4) == "workday"


def test_record_and_read(tmp_path):
    from runner.episodic_memory import EpisodicMemory

    mem = EpisodicMemory(root=tmp_path)
    assert mem.count() == 0

    mem.record("hi", "hello!", "happy", 80)
    assert mem.count() == 1

    recent = mem.recent(5)
    assert len(recent) == 1
    assert recent[0]["user"] == "hi"
    assert recent[0]["agent"] == "hello!"
    assert recent[0]["mood"] == "happy"
    assert recent[0]["energy"] == 80
    assert "weekday" in recent[0]
    assert "time_of_day" in recent[0]
    assert "day_type" in recent[0]


def test_recent_limit(tmp_path):
    from runner.episodic_memory import EpisodicMemory

    mem = EpisodicMemory(root=tmp_path)
    for i in range(20):
        mem.record(f"msg{i}", f"reply{i}", "neutral", 50)

    assert mem.count() == 20
    recent = mem.recent(5)
    assert len(recent) == 5
    assert recent[0]["user"] == "msg15"
    assert recent[-1]["user"] == "msg19"


def test_get_context_string(tmp_path):
    from runner.episodic_memory import EpisodicMemory

    mem = EpisodicMemory(root=tmp_path)
    assert mem.get_context_string() == ""

    mem.record("hello", "world", "happy", 100)
    ctx = mem.get_context_string()
    assert "RECENT INTERACTIONS" in ctx
    assert "hello" in ctx
    assert "happy" in ctx


def test_time_since_last(tmp_path):
    from runner.episodic_memory import EpisodicMemory

    mem = EpisodicMemory(root=tmp_path)
    assert mem.time_since_last() == "no history"

    mem.record("test", "ok", "neutral", 50)
    assert "just now" in mem.time_since_last() or "minutes" in mem.time_since_last() or "ago" in mem.time_since_last()


def test_rotation(tmp_path):
    from runner.episodic_memory import EpisodicMemory, MAX_LINES

    mem = EpisodicMemory(root=tmp_path)
    # Write enough to trigger rotation at least twice
    n = MAX_LINES * 2 + 100  # ~10100
    for i in range(n):
        mem.record(f"msg{i}", f"reply{i}", "neutral", 50)

    # After multiple rotations, file stays well below max
    assert mem.count() <= MAX_LINES // 2 + 100


def test_stats(tmp_path):
    from runner.episodic_memory import EpisodicMemory

    mem = EpisodicMemory(root=tmp_path)
    assert mem.stats() == {"total": 0}

    mem.record("hi", "hello", "happy", 80)
    mem.record("how are you", "good!", "happy", 90)
    stats = mem.stats()
    assert stats["total"] == 2
    assert stats["recent"] == 2
    assert "by_weekday" in stats
    assert "by_time_of_day" in stats


def test_memory_manager_integration(tmp_path):
    from runner.memory_manager import get_episodic_context

    ctx = get_episodic_context()
    assert isinstance(ctx, str)
