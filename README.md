# vi-agent-framework

**Early prototype.** A local-first AI agent state capsule — persistent memory, emotional state, message queue, and a minimal Python runner for Ollama.

Not a production framework. Not self-aware. A seed you can grow.

## What this is

A folder with:
- **State files** — `identity.md`, `memory.md`, `lessons.md`, `mood.json`, `queue.json`, `summary.md`
- **System prompt** — `AGENTS.md` that tells the LLM how to behave
- **Runner** — Python loop (`runner/main.py`) that reads state, calls Ollama, writes events, updates memory
- **Tools** — `list_files`, `read_file`, `write_file`, `run_command` (with allowlist)
- **Reflection** — after each interaction, the agent writes insights about the user into `memory.md` and `lessons.md` (growing wiser over time)
- **Analytics** — tracks mood history, session count, user emotional patterns over time
- **JSON Schemas** — for mood, queue, config, events
- **Scripts** — backup and health check

## Architecture

```
Ollama ←→ runner/main.py ←→ File System
                              ├── AGENTS.md (system prompt)
                              ├── identity.md (who I am)
                              ├── memory.md (facts about user)
                              ├── lessons.md (insights & learned patterns)
                              ├── mood.json (emotional state)
                              ├── queue.json (pending messages)
                              ├── summary.md (session context)
                              ├── analytics.json (mood history & stats)
                              ├── events.jsonl (interaction log)
                              ├── config.json (runtime config)
                              ├── schemas/ (JSON validation)
                              ├── tools/ (runner tool layer)
                              ├── runner/reflection.py (self-improvement)
                              ├── runner/analytics.py (user patterns)
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
- [x] Reflection — agent writes insights after each conversation
- [x] Analytics — mood tracking and user pattern recognition
- [ ] Vector memory (ChromaDB) — semantic search when memory grows large
- [ ] Memory policy (LRU, summarization, expiration)
- [ ] Event log rotation and querying
- [ ] Tool permission system with user confirmation
- [ ] Tests and CI
- [ ] Plugin system for custom tools

## Privacy

Everything runs **locally**. No data leaves your computer. No cloud APIs. No tracking. `events.jsonl` and `analytics.json` are in `.gitignore` — they never get committed.

## License

MIT — free to use, modify, and distribute.
