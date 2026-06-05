import logging
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
CHECK_INTERVAL = 30
OLLAMA_URL = "http://localhost:11434"
MAX_CRASHES = 5
CRASH_WINDOW = 300


class Watchdog:
    def __init__(self, agent_args: list[str] | None = None):
        self.agent_args = agent_args or []
        self._process: subprocess.Popen | None = None
        self._crashes: list[float] = []
        self._ollama_down = False
        self._mode = "normal"

    def _ping_ollama(self) -> bool:
        try:
            import urllib.request

            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _start_agent(self) -> subprocess.Popen | None:
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "runner.main", *self.agent_args],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logging.info(f"Agent started (PID {proc.pid})")
            return proc
        except Exception as e:
            logging.error(f"Failed to start agent: {e}")
            return None

    def _should_restart(self) -> bool:
        now = time.time()
        self._crashes = [t for t in self._crashes if now - t < CRASH_WINDOW]
        return len(self._crashes) < MAX_CRASHES

    def _downgrade_mode(self):
        from . import health as h

        if self._mode == "normal":
            self._mode = "safe"
            h.change_mode("safe")
            logging.warning("Degraded to SAFE mode")
        elif self._mode == "safe":
            self._mode = "readonly"
            h.change_mode("readonly")
            logging.warning("Degraded to READONLY mode")

    def run(self):
        logging.info("Watchdog started")
        self._start_agent()

        while True:
            time.sleep(CHECK_INTERVAL)
            from . import health as h

            check = h.checkup()

            if not check["ok"]:
                logging.warning(f"Health check failed: {check}")
                self._downgrade_mode()

            if not self._ping_ollama():
                if not self._ollama_down:
                    logging.warning("Ollama is down, queueing messages")
                    self._ollama_down = True
                continue
            else:
                if self._ollama_down:
                    logging.info("Ollama is back up")
                    self._ollama_down = False

            if self._process:
                ret = self._process.poll()
                if ret is not None:
                    self._crashes.append(time.time())
                    logging.warning(f"Agent exited with code {ret}")
                    if self._should_restart():
                        logging.info("Restarting agent...")
                        self._process = self._start_agent()
                    else:
                        logging.error("Too many crashes, stopping watchdog")
                        self._downgrade_mode()
                        break

    def stop(self):
        if self._process:
            self._process.terminate()
            logging.info("Agent terminated")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(ROOT / "watchdog.log"), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    wd = Watchdog(sys.argv[1:] if len(sys.argv) > 1 else [])
    try:
        wd.run()
    except KeyboardInterrupt:
        wd.stop()


if __name__ == "__main__":
    main()
