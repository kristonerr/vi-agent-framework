from . import file_manager

MEMORY_PATH = "memory.md"
LESSONS_PATH = "lessons.md"
SUMMARY_PATH = "summary.md"


def read_memory() -> str:
    try:
        return file_manager.read(MEMORY_PATH)
    except FileNotFoundError:
        return "# Memory\n\n## Facts\n\n"


def read_lessons() -> str:
    try:
        return file_manager.read(LESSONS_PATH)
    except FileNotFoundError:
        return "# Lessons\n\n"


def read_summary() -> str:
    try:
        return file_manager.read(SUMMARY_PATH)
    except FileNotFoundError:
        return "# Summary\n\n"


def append_lesson(lesson: str) -> None:
    content = read_lessons()
    content += f"\n- {lesson}"
    file_manager.write(LESSONS_PATH, content)


def append_memory(fact: str) -> None:
    content = read_memory()
    if "# Facts" in content:
        idx = content.index("# Facts")
        line_start = content.index("\n", idx) + 1
        content = content[:line_start] + f"- {fact}\n" + content[line_start:]
    else:
        content += f"\n- {fact}\n"
    file_manager.write(MEMORY_PATH, content)


def update_summary(summary: str) -> None:
    file_manager.write(SUMMARY_PATH, summary)
