from ..file_manager import write
from .registry import register


def write_file_tool(args: dict) -> dict:
    path = args.get("path", "")
    content = args.get("content", "")
    if not path:
        return {"success": False, "error": "path is required"}
    try:
        write(path, content)
        return {"success": True, "path": path, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("write_file", write_file_tool)
