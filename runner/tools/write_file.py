from ..file_manager import write
from .registry import register
from ._safe import resolve_path


def write_file_tool(args: dict) -> dict:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return {"success": False, "error": "path is required"}
    try:
        safe = resolve_path(path)
        write(str(safe), content)
        return {"success": True, "path": path, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("write_file", write_file_tool)
