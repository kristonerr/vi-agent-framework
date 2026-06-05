# Setup Guide — vi-agent

Пошаговая инструкция по развёртыванию vi-agent с нуля.

---

## 1. Установи Python

**Требование:** Python 3.10 или выше.

- Скачай с [python.org](https://www.python.org/downloads/)
- При установке отметь "Add Python to PATH"
- Проверь в терминале: `python --version`

## 2. Установи Git

- Скачай с [git-scm.com](https://git-scm.com/downloads)
- Проверь: `git --version`

## 3. Скачай vi-agent

```bash
git clone https://github.com/kristonerr/vi-agent-framework.git
cd vi-agent-framework
```

## 4. Установи зависимости

```bash
pip install -r requirements.txt
```

Сейчас там только `requests`, но если нужна семантическая память — ChromaDB установится автоматически при первом запуске. Можно установить заранее:

```bash
pip install chromadb
```

## 5. Установи и запусти Ollama

- Скачай с [ollama.ai](https://ollama.ai/download)
- Установи и запусти
- Проверь: `ollama --version`

Скачай модель для агента:

```bash
ollama pull qwen2.5:7b
```

Скачай модель для эмбеддингов (нужна для семантической памяти):

```bash
ollama pull nomic-embed-text
```

## 6. Настрой конфиг

Открой `config.json` и убедись что параметры подходят:

- `model` — модель для агента (по умолчанию `qwen2.5:7b`)
- `base_url` — адрес Ollama (по умолчанию `http://localhost:11434`)
- `temperature` — креативность ответов (0.0-1.0, по умолчанию 0.7)

Если Ollama работает на другом порту или удалённо — укажи свой URL.

## 7. Проверь allowlist (безопасность)

Файл `tools/allowlist.txt` содержит команды, которые агент может выполнять без спроса. По умолчанию там только безопасные команды. Можешь добавить свои, но будь осторожен.

## 8. Веб-поиск

Агент умеет искать в интернете через DuckDuckGo — без API-ключей, бесплатно.
Просто скажи в диалоге: *"найди в интернете последние новости"* — агент сам вызовет `web_search`.

## 9. MCP-совместимость

MCP (Model Context Protocol) — открытый стандарт для подключения внешних инструментов.
Чтобы подключить MCP-сервер, добавь его в `config.json`:

```json
{
  "mcp_servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    }
  ]
}
```

Агент сам обнаружит инструменты сервера и добавит их с префиксом `mcp_`. Пример:
- `mcp_read_file` — прочитать файл через MCP
- `mcp_write_file` — записать файл через MCP
- `mcp_list_directory` — список директории

## 8. Запусти агента

### Однократный запрос:

```bash
python -m runner.main "Привет, кто ты?"
```

### Интерактивный режим:

```bash
python -m runner.main
```

Появится приглашение `>`. Пиши сообщения, агент отвечает. Для выхода — `exit` или `Ctrl+C`.

## 9. Проактивность (опционально)

Чтобы агент сам писал тебе, когда долго молчит:

```bash
python viagent_proactivity.py --daemon
```

Остановка: `Ctrl+C`.

## 11. Что дальше?

- Персонализируй `AGENTS.md` — это системный промпт агента, его личность
- Напиши в `identity.md` кто ты (пользователь), чтобы агент знал
- Со временем агент сам будет наполнять `memory.md`, `lessons.md` и `heart.md`

## Быстрый чек-лист

- [ ] Python 3.10+
- [ ] Git
- [ ] `pip install -r requirements.txt`
- [ ] Ollama запущен
- [ ] `ollama pull qwen2.5:7b`
- [ ] `ollama pull nomic-embed-text`
- [ ] `python -m runner.main "привет"`

## Устранение проблем

**Ошибка "Ollama is not running"** — запусти Ollama сначала.

**Ошибка "module not found"** — проверь что ты в корне `vi-agent-framework`, выполни `pip install -r requirements.txt`.

**Русские символы в консоли Windows** — если кракозябры, выполни перед запуском:

```bash
$env:PYTHONIOENCODING='utf-8'
```
