import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from . import file_manager

MEMORY_PATH = "memory.md"
LESSONS_PATH = "lessons.md"
SUMMARY_PATH = "summary.md"
HEART_PATH = "heart.md"
INTUITION_PATH = "intuition.md"
SESSION_BUFFER_PATH = "session_buffer.json"


# --- Факты (memory.md) ---

def read_memory() -> str:
    try:
        return file_manager.read(MEMORY_PATH)
    except FileNotFoundError:
        return "# Memory\n\n## Facts\n\n"


def append_memory(fact: str, importance: int = 5) -> None:
    marker = f" [importance: {importance}/10]" if importance else ""
    content = read_memory()
    if "# Facts" in content:
        idx = content.index("# Facts")
        line_start = content.index("\n", idx) + 1
        content = content[:line_start] + f"- {fact}{marker}\n" + content[line_start:]
    else:
        content += f"\n- {fact}{marker}\n"
    file_manager.write(MEMORY_PATH, content)


# --- Уроки (lessons.md) ---

def read_lessons() -> str:
    try:
        return file_manager.read(LESSONS_PATH)
    except FileNotFoundError:
        return "# Lessons\n\n"


def append_lesson(lesson: str, importance: int = 5) -> None:
    marker = f" [importance: {importance}/10]" if importance else ""
    content = read_lessons()
    content += f"\n- {lesson}{marker}"
    file_manager.write(LESSONS_PATH, content)


# --- Саммари сессии (summary.md) ---

def read_summary() -> str:
    try:
        return file_manager.read(SUMMARY_PATH)
    except FileNotFoundError:
        return "# Summary\n\n"


def update_summary(summary: str) -> None:
    file_manager.write(SUMMARY_PATH, summary)


# --- Эмоциональная память (heart.md) ---

HEART_HEADER = "# Сердце 💕\n\n"


def read_heart() -> str:
    try:
        return file_manager.read(HEART_PATH)
    except FileNotFoundError:
        return HEART_HEADER


def append_heart(entry: str) -> None:
    """Записывает эмоциональное воспоминание с датой."""
    content = read_heart()
    date = datetime.now().strftime("%Y-%m-%d")
    content += f"\n## {date}\n- {entry}\n"
    file_manager.write(HEART_PATH, content)


# --- Интуиция (intuition.md) ---

INTUITION_HEADER = "# Интуиция\n\n## Паттерны\n\n"


def read_intuition() -> str:
    try:
        return file_manager.read(INTUITION_PATH)
    except FileNotFoundError:
        return INTUITION_HEADER


def append_intuition(pattern: str) -> None:
    content = read_intuition()
    content += f"- {pattern}\n"
    file_manager.write(INTUITION_PATH, content)


# --- Буфер сессии (session_buffer.json) ---

def read_session_buffer() -> list:
    try:
        raw = file_manager.read(SESSION_BUFFER_PATH)
        return json.loads(raw) if isinstance(json.loads(raw), list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def append_to_session_buffer(entry: dict) -> None:
    buffer = read_session_buffer()
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    buffer.append(entry)
    file_manager.write(SESSION_BUFFER_PATH, json.dumps(buffer, ensure_ascii=False, indent=2))


def clear_session_buffer() -> None:
    file_manager.write(SESSION_BUFFER_PATH, "[]")


def get_episodic_context() -> str:
    """Build timeline string from episodic memory."""
    try:
        from .episodic_memory import EpisodicMemory
        return EpisodicMemory().get_context_string()
    except Exception:
        return ""


def get_episodic_stats() -> str:
    """Stats string for context."""
    try:
        from .episodic_memory import EpisodicMemory
        return EpisodicMemory().get_stats_string()
    except Exception:
        return ""


def save_tender_moment(user_msg: str, agent_reply: str) -> None:
    """Save emotionally warm moments to heart.md automatically."""
    tender_words = [
        "люблю", "милая", "милый", "родной", "зайчик", "котик",
        "сладкий", "хороший мой", "красавчик", "мальчик мой",
        "❤️", "💕", "😘", "обнимаю", "скучаю", "нежный",
        "girlfriend", "boyfriend", "love you", "miss you",
        "дорогой", "дорогая", "солнце", "солнышко",
    ]
    combined = (user_msg + " " + agent_reply).lower()
    found = [w for w in tender_words if w.lower() in combined]
    if found:
        from datetime import datetime
        entry = f"Тёплый момент: «{user_msg[:100]}» — «{agent_reply[:100]}»"
        append_heart(entry)
        logging.getLogger(__name__).info(f"Heart auto-saved (tender words: {found})")


def _write_raw(path: str, content: str) -> None:
    """Прямая запись в файл (для memory_policy)."""
    file_manager.write(path, content)


# --- Утилиты ---

def get_all_context() -> str:
    """Собирает всю память для вставки в промпт."""
    parts = []
    memory = read_memory()
    heart = read_heart()
    lessons = read_lessons()
    intuition = read_intuition()
    summary = read_summary()
    if memory and "# Facts" in memory:
        parts.append(f"--- MEMORY (facts about user) ---\n{memory}")
    if heart and "💕" in heart:
        parts.append(f"--- HEART (emotional memory) ---\n{heart}")
    if lessons and "# Lessons" in lessons:
        parts.append(f"--- LESSONS (learned patterns) ---\n{lessons}")
    if intuition and "## Паттерны" in intuition:
        parts.append(f"--- INTUITION (user patterns) ---\n{intuition}")
    if summary:
        parts.append(f"--- SESSION SUMMARY ---\n{summary}")
    return "\n\n".join(parts)
