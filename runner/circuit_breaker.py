"""Circuit breaker for tool resilience.
Three states: closed (normal), open (blocked), half-open (testing).

If a tool fails N times in a window, the breaker opens.
Calls return a fallback instead of crashing.
"""

import logging
import time
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = "closed"
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_error = ""

    def _now(self) -> float:
        return time.time()

    def _is_open(self) -> bool:
        if self.state == "open":
            if self._now() - self.last_failure_time >= self.recovery_timeout:
                logger.info(f"[{self.name}] open → half-open (timeout elapsed)")
                self.state = "half-open"
                return False
            return True
        return False

    def call(self, fn, args=None, kwargs=None) -> dict:
        """Execute fn(*args, **kwargs) through the breaker.
        Returns dict — either the real result or a fallback error.
        """
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        if self._is_open():
            logger.warning(f"[{self.name}] circuit open, blocking call")
            return {"error": f"Инструмент '{self.name}' временно недоступен.", "_circuit_breaker": True}

        try:
            result = fn(*args, **kwargs)

            if self.state == "half-open":
                logger.info(f"[{self.name}] half-open → closed (success)")
                self.state = "closed"
                self.failure_count = 0

            self.failure_count = 0
            return result if isinstance(result, dict) else {"success": True, "data": result}

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = self._now()
            self.last_error = str(e)

            logger.warning(f"[{self.name}] failed ({self.failure_count}/{self.failure_threshold}): {e}")

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.error(f"[{self.name}] circuit opened after {self.failure_count} failures")

            return {"error": f"Инструмент '{self.name}' временно недоступен.", "_circuit_breaker": True}

    def reset(self):
        self.state = "closed"
        self.failure_count = 0
        self.last_error = ""

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "failures": self.failure_count,
            "threshold": self.failure_threshold,
            "last_error": self.last_error,
        }
