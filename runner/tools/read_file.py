from ..file_manager import read
from .registry import register
from ._safe import resolve_path


def read_file_tool(args: dict) -> dict:
    path = args.get("path", "")
    if not path:
        return {"success": False, "error": "path is required"}
    try:
        safe = resolve_path(path)
        content = read(str(safe))
        return {"success": True, "content": content, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("read_file", read_file_tool)
