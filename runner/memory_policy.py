"""Memory policy — decides what to remember, what to forget, and how to consolidate.
Simulates human-like memory:
- STM (session buffer) → LTM (memory.md, heart.md, intuition.md)
- Importance scoring
- Forgetting low-priority facts
- Emotional tagging
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from . import memory_manager as mm
from .ollama_client import OllamaClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

HIGH_PRIORITY_KEYWORDS = [
    "люблю", "важно", "навсегда", "никогда", "запомни",
    "нравится", "не нравится", "хочу", "мечтаю", "боюсь",
]


class MemoryPolicy:
    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama

    # --- Оценка важности ---

    def _keyword_score(self, text: str) -> int:
        text_lower = text.lower()
        score = 0
        for kw in HIGH_PRIORITY_KEYWORDS:
            if kw in text_lower:
                score += 1
        return score

    def rate_importance(self, text: str) -> int:
        """Оценивает важность воспоминания от 0 (мусор) до 10 (критично)."""
        keyword_score = self._keyword_score(text)
        length_bonus = 1 if len(text.split()) > 10 else 0
        base = min(keyword_score * 2, 5) + length_bonus

        if self.ollama and base < 4:
            try:
                prompt = (
                    f"Rate how important this memory is for an AI agent's relationship with its user "
                    f"on 0-10 scale. Consider emotional weight, personal relevance, and uniqueness.\n"
                    f"Memory: {text}\n\nReply with a single number (0-10)."
                )
                resp = self.ollama.chat([
                    {"role": "system", "content": "You rate memory importance. Reply only a number."},
                    {"role": "user", "content": prompt},
                ], temperature=0.1)
                llm_score = int(resp.strip())
                base = max(base, min(llm_score, 10))
            except (ValueError, Exception) as e:
                logging.warning(f"LLM importance rating failed: {e}")
        return min(base, 10)

    # --- Консолидация STM → LTM ---

    def consolidate(self, force: bool = False) -> int:
        """Переносит важные записи из буфера сессии в долговременную память."""
        buffer = mm.read_session_buffer()
        if not buffer:
            return 0

        transferred = 0
        remaining = []

        for entry in buffer:
            text = entry.get("text", entry.get("content", ""))
            if not text:
                continue

            importance = self.rate_importance(text)
            entry_type = self._classify(text, importance)

            if importance >= 5 or force:
                if entry_type == "emotional":
                    mm.append_heart(f"{text} [importance: {importance}/10]")
                elif entry_type == "pattern":
                    mm.append_intuition(text)
                elif entry_type == "lesson":
                    mm.append_lesson(text)
                else:
                    mm.append_memory(f"{text} [importance: {importance}/10]")
                transferred += 1
            else:
                remaining.append(entry)

        if transferred > 0:
            mm.clear_session_buffer()
            for entry in remaining:
                mm.append_to_session_buffer(entry)
            logging.info(f"Consolidated {transferred} items to LTM, {len(remaining)} kept in buffer")
        return transferred

    # --- Классификация типа воспоминания ---

    def _classify(self, text: str, importance: int) -> str:
        """Определяет тип: fact, emotional, pattern, lesson."""
        text_lower = text.lower()
        emotional_words = ["чувству", "сердц", "любл", "тепл", "груст", "счаст", "обид"]
        pattern_words = ["всегда", "обычно", "часто", "иногда", "никогда"]
        lesson_words = ["понял", "научил", "урок", "вывод", "осознал"]

        if any(w in text_lower for w in emotional_words) and importance > 5:
            return "emotional"
        if any(w in text_lower for w in pattern_words):
            return "pattern"
        if any(w in text_lower for w in lesson_words):
            return "lesson"
        return "fact"

    # --- Забывание (удаление низкоприоритетных фактов) ---

    def forget_low_priority(self, max_facts: int = 100) -> int:
        """Удаляет самые старые низкоприоритетные факты, если память разрослась."""
        memory = mm.read_memory()
        lines = memory.split("\n")
        facts = [l for l in lines if l.strip().startswith("- ")]

        if len(facts) <= max_facts:
            return 0

        # Удаляем факты без [importance] в начале
        to_remove = []
        for fact in facts[max_facts:]:
            if "[importance:" not in fact:
                to_remove.append(fact)

        if not to_remove:
            return 0

        for fact in to_remove:
            memory = memory.replace(fact + "\n", "")
            memory = memory.replace(fact, "")

        mm._write_raw(memory)
        logging.info(f"Forgot {len(to_remove)} low-priority facts")
        return len(to_remove)

    # --- Полный цикл ---

    def tick(self):
        """Один тик консолидации памяти."""
        transferred = self.consolidate()
        forgotten = self.forget_low_priority()
        if transferred or forgotten:
            logging.info(f"Memory tick: {transferred} consolidated, {forgotten} forgotten")
