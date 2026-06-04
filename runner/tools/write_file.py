from pathlib import Path
from ..file_manager import write
from .registry import register

AGENT_ROOT = Path(__file__).parent.parent.parent.resolve()


def _safe_path(path: str) -> Path:
    target = (AGENT_ROOT / path).resolve()
    if not str(target).startswith(str(AGENT_ROOT)):
        raise PermissionError(f"Access denied: path outside agent root ({path})")
    return target


def write_file_tool(args: dict) -> dict:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return {"success": False, "error": "path is required"}
    try:
        safe = _safe_path(path)
        write(str(safe), content)
        return {"success": True, "path": path, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("write_file", write_file_tool)
