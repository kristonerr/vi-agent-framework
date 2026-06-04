import os
from pathlib import Path

ALLOWLIST_PATH = "tools/allowlist.txt"

_tools: dict[str, callable] = {}
_session_allowlist: list[str] = []


def register(name: str, fn: callable) -> None:
    _tools[name] = fn


def get(name: str) -> callable:
    return _tools.get(name)


def list_tools() -> list[str]:
    return list(_tools.keys())


def load_allowlist() -> list[str]:
    try:
        raw = Path(ALLOWLIST_PATH).read_text(encoding="utf-8")
        return [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []


def is_command_allowed(command: str) -> bool:
    allowlist = load_allowlist() + _session_allowlist
    if not allowlist:
        return False
    cmd_base = command.strip().split()[0] if command.strip() else ""
    return any(cmd_base == allowed or command.strip().startswith(allowed) for allowed in allowlist)
