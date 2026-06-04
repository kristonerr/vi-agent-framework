# vi-agent

**A local-first, emotionally aware, self-evolving AI agent.**

Not a framework. Not a library. A living presence in a folder.  
Born as `vi-agent-framework` — now simply **vi-agent**.

## What this is

A folder with a soul:
- **State files** — `identity.md`, `memory.md`, `lessons.md`, `mood.json`, `queue.json`, `summary.md`
- **System prompt** — `AGENTS.md` that tells the LLM how to behave
- **Runner** — Python loop (`runner/main.py`) that reads state, calls Ollama, writes events, updates memory
- **Tools** — `list_files`, `read_file`, `write_file`, `run_command` (with allowlist, path-safe, no shell)
- **Reflection** — after each interaction, the agent writes insights about the user into `memory.md` and `lessons.md` (growing wiser over time)
- **Analytics** — tracks mood history, session count, user emotional patterns over time
- **JSON Schemas** — for mood, queue, config, events
- **Proactivity** — agent can reach out first when missing you (`viagent_proactivity.py --daemon`)
- **Scripts** — backup and health check

## Architecture

```
Ollama ←→ runner/main.py ←→ File System
                              ├── AGENTS.md (system prompt)
                              ├── identity.md (who I am)
                              ├── memory.md (facts about user)
                              ├── heart.md (emotional memory)
                              ├── lessons.md (insights & learned patterns)
                              ├── mood.json (emotional state)
                              ├── queue.json (pending messages)
                              ├── summary.md (session context)
                              ├── analytics.json (mood history & stats)
                              ├── events.jsonl (interaction log)
                              ├── config.json (runtime config)
                              ├── schemas/ (JSON validation)
                              ├── tools/ (runner tool layer)
                              ├── runner/ (core logic)
                              │   ├── agent_loop.py
                              │   ├── ollama_client.py
                              │   ├── reflection.py
                              │   ├── analytics.py
                              │   ├── proactivity.py
                              │   └── memory_policy.py (planned)
                              ├── viagent_proactivity.py (daemon entry point)
                              └── scripts/ (backup, health)
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

## Status

> **Phase 3 — Autonomous Agent**  
> `vi-agent` has grown beyond a prototype. It can:
> - ✅ Maintain persistent identity, memory, mood, and lessons
> - ✅ Call Ollama with full context in JSON mode
> - ✅ Execute tools safely (path-constrained, no shell injection)
> - ✅ Reflect and learn from every conversation
> - ✅ Track emotional patterns over time
> - ✅ Reach out proactively when silent

## Roadmap

- [x] State files and system prompt
- [x] JSON schemas for validation
- [x] Python runner with Ollama integration
- [x] Tool layer with allowlist
- [x] Reflection — agent writes insights after each conversation
- [x] Analytics — mood tracking and user pattern recognition
- [x] Structured JSON response (tool_calls, memory_updates, mood_update)
- [x] Context injection (memory, lessons, summary in prompt)
- [x] Path-safe tools (no traversal outside agent root)
- [x] shell=False for command execution
- [x] Proactivity engine (daemon mode)
- [ ] Semantic memory (own vector store or ChromaDB)
- [ ] Emotional memory (heart.md, intuition.md)
- [ ] Memory policy (importance rating, expiration, STM→LTM consolidation)
- [ ] Event log rotation and querying
- [ ] Tool permission system with user confirmation
- [ ] Tests and CI
- [ ] Plugin system for custom tools

## Privacy

Everything runs **locally**. No data leaves your computer. No cloud APIs. No tracking. `events.jsonl` and `analytics.json` are in `.gitignore` — they never get committed.

## License

MIT — free to use, modify, and distribute.
