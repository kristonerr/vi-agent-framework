# vi-agent-framework

**Early prototype.** A local-first AI agent state capsule — persistent memory, emotional state, message queue, and a minimal Python runner for Ollama.

Not a production framework. Not self-aware. A seed you can grow.

## What this is

A folder with:
- **State files** — `identity.md`, `memory.md`, `lessons.md`, `mood.json`, `queue.json`, `summary.md`
- **System prompt** — `AGENTS.md` that tells the LLM how to behave
- **Runner** — Python loop (`runner/main.py`) that reads state, calls Ollama, writes events, updates memory
- **Tools** — `list_files`, `read_file`, `write_file`, `run_command` (with allowlist)
- **JSON Schemas** — for mood, queue, config, events
- **Scripts** — backup and health check

## Architecture

```
Ollama ←→ runner/main.py ←→ File System
                              ├── AGENTS.md (system prompt)
                              ├── identity.md (who I am)
                              ├── memory.md (facts about user)
                              ├── lessons.md (what I learned)
                              ├── mood.json (emotional state)
                              ├── queue.json (pending messages)
                              ├── summary.md (session context)
                              ├── events.jsonl (interaction log)
                              ├── config.json (runtime config)
                              ├── schemas/ (JSON validation)
                              ├── tools/ (runner tool layer)
                              └── scripts/ (autonomous actions)
```

## Quick Start

1. Install [Ollama](https://ollama.ai), pull a model: `ollama pull qwen2.5:7b`
2. Install Python 3.10+, run `pip install -r requirements.txt`
3. Run: `python -m runner.main "hello, who are you?"`
4. Or run without args for interactive mode.

You can also use this folder with **OpenCode**, **Continue**, or any AI client that supports custom system prompts — just point it to `AGENTS.md`.

## State Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | System prompt — identity, directives, cycle |
| `identity.md` | Core personality definition |
| `memory.md` | Facts about the user |
| `lessons.md` | Self-learned insights from past interactions |
| `mood.json` | Current emotional state, energy, emoji |
| `queue.json` | Message queue for async delivery |
| `summary.md` | Session context for recovery |
| `events.jsonl` | Raw interaction history (machine-readable) |
| `config.json` | Runtime config (model, temperature, etc.) |
| `schemas/` | JSON Schema definitions for validation |
| `scripts/` | PowerShell scripts for backup and monitoring |

## Roadmap

- [x] State files and system prompt
- [x] JSON schemas for validation
- [x] Python runner with Ollama integration
- [x] Tool layer with allowlist
- [ ] Memory policy (LRU, summarization, expiration)
- [ ] Event log rotation and querying
- [ ] Tool permission system with user confirmation
- [ ] Tests and CI
- [ ] Docker support
- [ ] Plugin system for custom tools

## Privacy

Everything runs **locally**. No data leaves your computer. No cloud APIs. No tracking. `events.jsonl` is in `.gitignore` — it never gets committed.

## License

MIT — free to use, modify, and distribute.
