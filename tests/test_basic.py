"""Basic tests for vi-agent runner modules."""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))


def test_imports():
    from runner.ollama_client import OllamaClient
    from runner.semantic_memory import SemanticMemory
    from runner.memory_policy import MemoryPolicy
    from runner.agent_loop import AgentLoop
    from runner.reflection import reflect
    from runner.analytics import record_interaction, session_start, get_summary, _guess_user_mood
    from runner.tools.registry import register, get, is_command_allowed, list_tools, load_allowlist
    assert OllamaClient
    assert SemanticMemory
    assert MemoryPolicy


def test_mood_guess():
    from runner.analytics import _guess_user_mood
    assert _guess_user_mood("мне грустно сегодня") == "sad"
    assert _guess_user_mood("я так рад!") == "happy"
    assert _guess_user_mood("всё нормально") == "neutral"
    assert _guess_user_mood("это пиздец") == "angry"


def test_normalize_json():
    from runner.agent_loop import normalize_json
    cases = [
        ('{"reply": "hi"}', '{"reply": "hi"}'),
        ('```json\n{"reply": "hi"}\n```', '{"reply": "hi"}'),
        ("{'reply': 'hi'}", '{"reply": "hi"}'),
    ]
    for raw, expected in cases:
        assert normalize_json(raw) == expected, f"Failed: {raw!r}"


def test_sort_tool_calls():
    from runner.agent_loop import sort_tool_calls
    calls = [
        {"name": "write_file", "arguments": {}},
        {"name": "run_command", "arguments": {}},
        {"name": "read_file", "arguments": {}},
    ]
    sorted_calls = sort_tool_calls(calls)
    names = [c["name"] for c in sorted_calls]
    assert names == ["read_file", "write_file", "run_command"]


def test_estimate_tokens():
    from runner.agent_loop import estimate_tokens
    result = estimate_tokens("hello world")
    assert isinstance(result, int) and result > 0


def test_trim_context():
    from runner.agent_loop import trim_context
    msgs = [
        {"role": "user", "content": "a" * 500},
        {"role": "assistant", "content": "b" * 500},
    ]
    trimmed = trim_context(msgs, max_tokens=50)
    assert len(trimmed) < len(msgs)


def test_file_manager():
    from runner.file_manager import read, write, list_files
    test_content = "test data"
    test_path = "test_tmp.txt"
    write(test_path, test_content)
    assert read(test_path) == test_content
    files = list_files(".", "*.txt")
    assert any("test_tmp" in f for f in files)
    os.unlink(test_path)


def test_memory_manager():
    from runner import memory_manager as mm
    test_fact = "test fact"
    mm.append_memory(test_fact)
    memory = mm.read_memory()
    assert test_fact in memory


def test_health_checksums():
    from runner.health import update_checksums, verify_state, _sha256, _read_health
    import tempfile
    from pathlib import Path
    update_checksums()
    health = _read_health()
    assert "checksums" in health
    assert len(health["checksums"]) > 0


def test_health_backup_rotate():
    from runner.health import backup_state, _read_health
    ts = backup_state()
    assert ts is not None
    health = _read_health()
    assert ts in health.get("backups", [])


def test_import_standalone():
    """Verify no ImportError from any runner module."""
    modules = [
        "runner.ollama_client",
        "runner.file_manager",
        "runner.memory_manager",
        "runner.event_logger",
        "runner.mood_manager",
        "runner.queue_manager",
        "runner.reflection",
        "runner.analytics",
        "runner.memory_policy",
        "runner.semantic_memory",
        "runner.agent_loop",
        "runner.tools.registry",
        "runner.tools.read_file",
        "runner.tools.write_file",
        "runner.tools.list_files",
        "runner.tools.run_command",
        "runner.tools.web_search",
        "runner.mcp_client",
        "runner.health",
        "runner.watchdog",
    ]
    for mod_name in modules:
        __import__(mod_name)
