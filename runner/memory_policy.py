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
from .semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)

HIGH_PRIORITY_KEYWORDS = [
    "люблю", "важно", "навсегда", "никогда", "запомни",
    "нравится", "не нравится", "хочу", "мечтаю", "боюсь",
]


class MemoryPolicy:
    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama
        self.semantic = SemanticMemory(ollama_client=ollama)

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
                logger.warning(f"LLM importance rating failed: {e}")
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
                    mm.append_heart(f"{text}")
                elif entry_type == "pattern":
                    mm.append_intuition(text)
                elif entry_type == "lesson":
                    mm.append_lesson(text, importance=importance)
                else:
                    mm.append_memory(text, importance=importance)

                self.semantic.add(text, source=entry_type, importance=importance)
                transferred += 1
            else:
                remaining.append(entry)

        if transferred > 0:
            mm.clear_session_buffer()
            for entry in remaining:
                mm.append_to_session_buffer(entry)
            logger.info(f"Consolidated {transferred} items to LTM, {len(remaining)} kept in buffer")
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
        """Удаляет старые низкоприоритетные факты с низким access_count."""
        memory = mm.read_memory()
        lines = memory.split("\n")
        facts = [l for l in lines if l.strip().startswith("- ")]

        if len(facts) <= max_facts:
            return 0

        keep = []
        removed = 0
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("- "):
                imp = 5
                import re
                m = re.search(r"\[importance:\s*(\d+)", stripped)
                if m:
                    imp = int(m.group(1))
                has_access = "[access:" in stripped
                if imp >= 3 or has_access:
                    keep.append(line)
                elif removed < len(facts) - max_facts:
                    removed += 1
                    continue
                else:
                    keep.append(line)
            else:
                keep.append(line)

        mm._write_raw(mm.MEMORY_PATH, "\n".join(keep))
        logger.info(f"Forgot {removed} low-priority facts")
        return removed

    # --- Полный цикл ---

    def tick(self):
        """Один тик консолидации памяти."""
        transferred = self.consolidate()
        forgotten = self.forget_low_priority()
        if transferred or forgotten:
            logger.info(f"Memory tick: {transferred} consolidated, {forgotten} forgotten")
