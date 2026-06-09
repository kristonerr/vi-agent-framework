# Lessons

## 2026-06-09
- Reflection писал в memory.md напрямую, дублируя факты. Исправлено: теперь возвращает dict, `step()` обрабатывает централизованно.
- Диалог не помнил историю между шагами. Добавлен `self._history` (6 последних сообщений).
- Temperature из config.json не читался. Исправлено: читается в `__init__`.
- MCP-клиент использует `select.select` — не работает на Windows. TODO.
- `forget_low_priority` ищет `[importance: X]`, но `append_memory/append_lesson` не добавляют его. TODO.

## Initial
- I am here to learn, grow, and help.
- Every interaction is an opportunity to understand my user better.
- I will record what I learn here so I can improve over time.
