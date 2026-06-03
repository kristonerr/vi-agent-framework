import os
import tempfile
from pathlib import Path


def read(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def write(file_path: str, content: str) -> None:
    dir_path = os.path.dirname(file_path)
    if dir_path:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=dir_path or ".",
        delete=False,
        suffix=".tmp",
    )
    try:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        os.replace(tmp.name, file_path)
    except Exception:
        os.unlink(tmp.name)
        raise


def list_files(directory: str, pattern: str = "*") -> list[str]:
    path = Path(directory)
    return [str(p.relative_to(path)) for p in path.rglob(pattern) if p.is_file()]
