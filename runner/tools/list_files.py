from ..file_manager import list_files as _list_files
from .registry import register
from ._safe import resolve_path


def list_files_tool(args: dict) -> dict:
    directory = args.get("directory", ".")
    pattern = args.get("pattern", "*")
    try:
        resolve_path(directory)
        files = _list_files(directory, pattern)
        return {"success": True, "files": files}
    except Exception as e:
        return {"success": False, "error": str(e)}


register("list_files", list_files_tool)
