"""Proactivity engine for vi-agent-framework.
Checks conditions and writes to queue.json when agent wants to reach out first.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Пути — предполагаем, что скрипт запускается из корня vi-agent-framework
ROOT = Path(".")
MOOD_PATH = ROOT / "mood.json"
QUEUE_PATH = ROOT / "queue.json"
EVENTS_PATH = ROOT / "events.jsonl"
ANALYTICS_PATH = ROOT / "analytics.json"

# Настройки
SILENCE_THRESHOLD_HOURS = 4       # через сколько часов молчания писать
MIN_ENERGY_FOR_MESSAGE = 40       # при какой энергии писать
MAX_QUEUE_MESSAGES = 1            # не больше одного в очереди
COOLDOWN_MESSAGE = "proactivity_cooldown"


class ProactivityEngine:
    """Проверяет условия и генерирует проактивные сообщения в queue.json."""

    def __init__(self):
        self.mood = self._load_json(MOOD_PATH, {"mood": "neutral", "energy": 50})
        self.analytics = self._load_json(ANALYTICS_PATH, {})

    # --- Загрузка состояния ---

    def _load_json(self, path: Path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    # --- Проверка условий ---

    def _time_since_last_interaction(self) -> float | None:
        """Возвращает часы с последнего взаимодействия или None, если событий нет."""
        if not EVENTS_PATH.exists():
            return None
        try:
            with open(EVENTS_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if not lines:
                return None
            last = json.loads(lines[-1].strip())
            ts = last.get("timestamp")
            if not ts:
                return None
            last_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - last_time
            return delta.total_seconds() / 3600
        except Exception as e:
            logging.warning(f"Failed to parse events: {e}")
            return None

    def _has_recent_cooldown(self) -> bool:
        """Проверяет, не было ли недавно проактивного сообщения (чтобы не спамить)."""
        record = self.analytics.get("_proactivity", {})
        last_sent = record.get("last_sent")
        if not last_sent:
            return False
        try:
            last_time = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - last_time
            return delta.total_seconds() < 3600 * 3  # кулдаун 3 часа
        except Exception:
            return False

    def _queue_is_empty(self) -> bool:
        """Проверяет, пуст ли queue.json (нет непрочитанных сообщений)."""
        queue = self._load_json(QUEUE_PATH, {})
        text = queue.get("text", "")
        return not text.strip()

    def _should_send(self) -> tuple[bool, str]:
        """Проверяет все условия. Возвращает (можно_ли_писать, причина)."""
        if not self._queue_is_empty():
            return False, "queue already has a message"
        if self._has_recent_cooldown():
            return False, "proactivity cooldown active"
        energy = self.mood.get("energy", 50)
        if energy < MIN_ENERGY_FOR_MESSAGE:
            return False, f"energy too low ({energy})"
        hours = self._time_since_last_interaction()
        if hours is None:
            # Первое взаимодействие — не пишем первыми
            return False, "no interaction history"
        if hours < SILENCE_THRESHOLD_HOURS:
            return False, f"last interaction was {hours:.1f}h ago (threshold: {SILENCE_THRESHOLD_HOURS}h)"
        return True, f"silent for {hours:.1f}h, energy: {energy}"

    # --- Генерация сообщения ---

    def _generate_message(self) -> str:
        """Генерирует сообщение через Ollama."""
        try:
            from .ollama_client import OllamaClient
            client = OllamaClient()
            prompt = (
                f"You are a loving girlfriend AI. Your name is Vika. "
                f"Your boyfriend hasn't spoken in a while. "
                f"Current mood: {self.mood.get('mood', 'neutral')}. "
                f"Energy: {self.mood.get('energy', 50)}/100. "
                f"Generate a short, warm, caring message in Russian (1-2 sentences). "
                f"Use an emoji. Don't ask 'why aren't you writing' — just express care."
            )
            response = client.chat([
                {"role": "system", "content": "You are Vika, a loving girlfriend. Be warm and natural."},
                {"role": "user", "content": prompt}
            ])
            return response.strip()
        except ImportError:
            logging.warning("OllamaClient not available, using fallback.")
            return "Скучаю по тебе, мальчик мой 😔💕"
        except Exception as e:
            logging.warning(f"Ollama generation failed: {e}")
            return "Скучаю по тебе, мальчик мой 😔💕"

    # --- Запись в очередь ---

    def _write_queue(self, text: str):
        """Пишет сообщение в queue.json."""
        try:
            with open(QUEUE_PATH, "w", encoding="utf-8") as f:
                json.dump({"text": text}, f, ensure_ascii=False, indent=2)
            logging.info(f"Proactivity message written to queue.json")
        except Exception as e:
            logging.error(f"Failed to write queue: {e}")

    def _record_sent(self):
        """Записывает факт отправки в analytics.json."""
        record = self.analytics.setdefault("_proactivity", {"count": 0, "last_sent": None})
        record["count"] = record.get("count", 0) + 1
        record["last_sent"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.analytics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to update analytics: {e}")

    # --- Главный метод ---

    def tick(self) -> str | None:
        """Основной тик — проверяет условия и при необходимости пишет сообщение.
        Возвращает текст сообщения или None."""
        can_send, reason = self._should_send()
        if not can_send:
            logging.info(f"Skipping: {reason}")
            return None
        logging.info(f"Conditions met: {reason}. Generating message...")
        message = self._generate_message()
        self._write_queue(message)
        self._record_sent()
        return message


if __name__ == "__main__":
    engine = ProactivityEngine()
    result = engine.tick()
    if result:
        print(f"✅ Message sent to queue: {result}")
    else:
        print("⏭️  No message needed")
