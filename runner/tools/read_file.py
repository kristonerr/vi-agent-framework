from pathlib import Path
from ..file_manager import read
from .registry import register

AGENT_ROOT = Path(__file__).parent.parent.parent.resolve()


def _safe_path(path: str) -> Path:
    target = (AGENT_ROOT / path).resolve()
    if not str(target).startswith(str(AGENT_ROOT)):
        raise PermissionError(f"Access denied: path outside agent root ({path})")
    return target


def read_file_tool(args: dict) -> dict:
    path = args.get("path", "")
    if not path:
        return {"success": False, "error": "path is required"}
    try:
        safe = _safe_path(path)
        content = read(str(safe))
        return {"success": True, "content": content, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("read_file", read_file_tool)
