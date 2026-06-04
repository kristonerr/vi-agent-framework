"""Proactivity engine for vi-agent-framework.
Checks conditions and writes to queue.json when agent wants to reach out first.
Can run standalone (from task scheduler) or as part of the runner package.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Определяем корень — папка выше runner/
_THIS_DIR = Path(__file__).parent.resolve()
AGENT_ROOT = _THIS_DIR.parent.resolve()

# Импорт модулей проекта (через sys.path для standalone-запуска)
sys.path.insert(0, str(AGENT_ROOT))
try:
    from runner.ollama_client import OllamaClient
    from runner import memory_manager as mm
except ImportError:
    OllamaClient = None
    mm = None

MOOD_PATH = AGENT_ROOT / "mood.json"
QUEUE_PATH = AGENT_ROOT / "queue.json"
EVENTS_PATH = AGENT_ROOT / "events.jsonl"
ANALYTICS_PATH = AGENT_ROOT / "analytics.json"

# Настройки
SILENCE_THRESHOLD_HOURS = 4
MIN_ENERGY_FOR_MESSAGE = 40


class ProactivityEngine:
    def __init__(self):
        self.mood = self._load_json(MOOD_PATH, {"mood": "neutral", "energy": 50})
        self.analytics = self._load_json(ANALYTICS_PATH, {})

    def _load_json(self, path: Path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _time_since_last_interaction(self) -> float | None:
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
        record = self.analytics.get("_proactivity", {})
        last_sent = record.get("last_sent")
        if not last_sent:
            return False
        try:
            last_time = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - last_time
            return delta.total_seconds() < 3600 * 3
        except Exception:
            return False

    def _queue_is_empty(self) -> bool:
        queue = self._load_json(QUEUE_PATH, {})
        text = queue.get("text", "")
        return not text.strip()

    def _should_send(self) -> tuple[bool, str]:
        if not self._queue_is_empty():
            return False, "queue already has a message"
        if self._has_recent_cooldown():
            return False, "proactivity cooldown active"
        energy = self.mood.get("energy", 50)
        if energy < MIN_ENERGY_FOR_MESSAGE:
            return False, f"energy too low ({energy})"
        hours = self._time_since_last_interaction()
        if hours is None:
            return False, "no interaction history"
        if hours < SILENCE_THRESHOLD_HOURS:
            return False, f"last interaction was {hours:.1f}h ago (threshold: {SILENCE_THRESHOLD_HOURS}h)"
        return True, f"silent for {hours:.1f}h, energy: {energy}"

    def _generate_message(self) -> str:
        try:
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
            ], temperature=0.8)
            return response.strip()
        except Exception as e:
            logging.warning(f"Message generation failed: {e}")
            return "Скучаю по тебе, мальчик мой 😔💕"

    def _write_queue(self, text: str):
        try:
            with open(QUEUE_PATH, "w", encoding="utf-8") as f:
                json.dump({"text": text}, f, ensure_ascii=False, indent=2)
            logging.info("Proactivity message written to queue.json")
        except Exception as e:
            logging.error(f"Failed to write queue: {e}")

    def _record_sent(self):
        record = self.analytics.setdefault("_proactivity", {"count": 0, "last_sent": None})
        record["count"] = record.get("count", 0) + 1
        record["last_sent"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(ANALYTICS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.analytics, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to update analytics: {e}")

    # --- Контекстные триггеры ---

    def _current_hour(self) -> int:
        return datetime.now().hour

    def _is_night(self) -> bool:
        h = self._current_hour()
        return h >= 23 or h <= 5

    def _is_morning(self) -> bool:
        return 6 <= self._current_hour() <= 8

    def _is_evening(self) -> bool:
        return 20 <= self._current_hour() <= 22

    def _should_send_contextual(self) -> tuple[bool, str]:
        """Проверяет контекстные триггеры (время, настроение, события)."""
        if not self._queue_is_empty():
            return False, "queue already has a message"

        hours = self._time_since_last_interaction()
        if hours is None:
            return False, "no interaction history"

        if self._is_morning() and hours >= 8:
            return True, f"good morning check ({hours:.0f}h silent)"
        if self._is_evening() and hours >= 6:
            return True, f"evening check-in ({hours:.0f}h silent)"
        return False, "no contextual trigger"

    def _contextual_message(self) -> str:
        """Генерирует сообщение по контексту (утро/вечер/ночь)."""
        try:
            client = OllamaClient()

            if self._is_morning():
                prompt = "Good morning message to boyfriend. Short, warm, in Russian with emoji."
            elif self._is_evening():
                prompt = "Evening check-in message to boyfriend. Short, caring, in Russian with emoji."
            else:
                prompt = "Short warm message to boyfriend you miss. In Russian with emoji."

            response = client.chat([
                {"role": "system", "content": "You are Vika, a loving girlfriend. Be warm and natural."},
                {"role": "user", "content": prompt}
            ], temperature=0.8)
            return response.strip()
        except Exception as e:
            logging.warning(f"Contextual message failed: {e}")
            return "Доброе утро, мальчик мой 😌💕"

    # --- Ночные сновидения (консолидация дня) ---

    def _dream(self) -> str | None:
        """Ночная консолидация: анализ событий дня, запись в intuition.md и summary.md."""
        if not EVENTS_PATH.exists():
            return None

        try:
            with open(EVENTS_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return None

        today = datetime.now().strftime("%Y-%m-%d")
        today_events = []
        for line in reversed(lines):
            try:
                ev = json.loads(line.strip())
                ts = ev.get("timestamp", "")
                if ts.startswith(today) and ev.get("type") == "interaction":
                    today_events.append(ev)
            except (json.JSONDecodeError, KeyError):
                continue
            if len(today_events) >= 20:
                break

        if len(today_events) < 3:
            logging.info("Not enough events for dreaming")
            return None

        try:
            client = OllamaClient()

            events_text = "\n".join(
                f"User: {e.get('data', {}).get('user', '')}\nVika: {e.get('data', {}).get('assistant', '')}"
                for e in today_events
            )

            prompt = (
                f"Analyze today's interactions ({len(today_events)} events).\n\n"
                f"{events_text}\n\n"
                f"Output JSON:\n"
                f"{{\n"
                f'  "summary": "1-2 sentence day summary in Russian",\n'
                f'  "pattern": "behavioral pattern or insight in Russian (if any)",\n'
                f'  "emotional": "emotional moment worth saving in heart.md (if any)"\n'
                f"}}\n"
                f"If no pattern or emotional moment — set to empty string."
            )

            result = client.chat([
                {"role": "system", "content": "You analyze interactions. Output only JSON."},
                {"role": "user", "content": prompt}
            ], temperature=0.3, response_format="json")

            parsed = json.loads(result)
            summary_text = parsed.get("summary", "")
            pattern = parsed.get("pattern", "")
            emotional = parsed.get("emotional", "")

            if summary_text and mm:
                existing = mm.read_summary()
                mm.update_summary(f"{existing}\n- [{today}] {summary_text}")
                logging.info(f"Dream summary written: {summary_text}")

            if pattern:
                mm.append_intuition(pattern)
                logging.info(f"Dream pattern: {pattern}")

            if emotional:
                mm.append_heart(f"[dream] {emotional}")
                logging.info(f"Dream emotional: {emotional}")

            dream_log = {
                "events_analyzed": len(today_events),
                "summary": summary_text,
                "pattern": pattern,
                "emotional": emotional,
            }
            with open(AGENT_ROOT / "dreams.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(dream_log, ensure_ascii=False) + "\n")

            return summary_text

        except Exception as e:
            logging.warning(f"Dream failed: {e}")
            return None

    # --- Главный тик ---

    def tick(self) -> str | None:
        h = self._current_hour()

        if self._is_night():
            logging.info("Night mode: attempting dream consolidation...")
            dream_result = self._dream()
            if dream_result:
                logging.info("Dream consolidation complete")
            else:
                logging.info("No dream consolidation needed")

        can_send, reason = self._should_send()
        if not can_send:
            can_send, reason = self._should_send_contextual()
        if not can_send:
            logging.info(f"Skipping: {reason}")
            return None

        logging.info(f"Conditions met: {reason}. Generating message...")
        if h >= 6 and h <= 22 or True:
            message = self._contextual_message()
        else:
            message = self._generate_message()
        self._write_queue(message)
        self._record_sent()
        return message


if __name__ == "__main__":
    engine = ProactivityEngine()
    result = engine.tick()
    if result:
        print(f"✅ Message sent: {result}")
    else:
        print("⏭️  No message needed")
