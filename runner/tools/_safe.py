import os
from pathlib import Path

AGENT_ROOT = Path(__file__).parent.parent.parent.resolve()


def resolve_path(path: str) -> Path:
    target = (AGENT_ROOT / path).resolve()
    if not str(target).startswith(str(AGENT_ROOT)):
        raise PermissionError(f"Access denied: path outside agent root ({path})")
    if target.is_symlink() or target != target.resolve():
        raise PermissionError(f"Symlinks not allowed: {path}")
    return target
