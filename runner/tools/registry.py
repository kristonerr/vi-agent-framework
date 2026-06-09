import os
from pathlib import Path
from ..circuit_breaker import CircuitBreaker

ALLOWLIST_PATH = "tools/allowlist.txt"

_tools: dict[str, callable] = {}
_breakers: dict[str, CircuitBreaker] = {}

# Инструменты, которые ломкие — проходят через circuit breaker
_FRAGILE_TOOLS = {"web_search", "run_command", "mcp_"}


def _make_breaker(name: str) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name)
    return _breakers[name]


class _SessionAllowlist:
    def __init__(self):
        self._items: list[str] = []

    def get(self) -> list[str]:
        return list(self._items)

    def add(self, cmd: str):
        base = cmd.strip().split()[0] if cmd.strip() else ""
        if base and base not in self._items:
            self._items.append(base)

    def set(self, lst: list[str]):
        self._items = list(lst)

    def clear(self):
        self._items.clear()


_session_allowlist = _SessionAllowlist()


def register(name: str, fn: callable) -> None:
    _tools[name] = fn


def get(name: str) -> callable:
    return _tools.get(name)


def list_tools() -> list[str]:
    return list(_tools.keys())


def load_allowlist() -> list[str]:
    try:
        raw = Path(ALLOWLIST_PATH).read_text(encoding="utf-8")
        return [line.strip() for line in raw.splitlines() if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []


def is_command_allowed(command: str) -> bool:
    allowlist = load_allowlist() + _session_allowlist.get()
    if not allowlist:
        return False
    cmd_base = command.strip().split()[0] if command.strip() else ""
    return any(cmd_base == allowed for allowed in allowlist)


def call_with_resilience(name: str, args: dict) -> dict:
    """Call a tool through the circuit breaker.
    Fragile tools are protected; non-fragile tools pass through directly.
    """
    fn = _tools.get(name)
    if not fn:
        return {"error": f"unknown tool: {name}"}

    is_fragile = any(name.startswith(p) for p in _FRAGILE_TOOLS)
    if not is_fragile:
        try:
            result = fn(args)
            return result if isinstance(result, dict) else {"success": True, "data": result}
        except Exception as e:
            return {"error": str(e)}

    breaker = _make_breaker(name)
    return breaker.call(fn, args=[args])


def breaker_status() -> dict[str, dict]:
    return {n: b.status() for n, b in _breakers.items()}


def reset_breaker(name: str):
    _make_breaker(name).reset()
