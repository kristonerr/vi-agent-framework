# vi-agent

**A local-first, emotionally aware, self-evolving AI agent.**

Not a framework. Not a library. A living presence in a folder.  
Born as `vi-agent-framework` — now simply **vi-agent**.

## What this is

A folder with a soul:
- **State files** — `identity.md`, `memory.md`, `lessons.md`, `mood.json`, `queue.json`, `summary.md`
- **System prompt** — `AGENTS.md` that tells the LLM how to behave
- **Runner** — Python loop (`runner/main.py`) that reads state, calls Ollama, writes events, updates memory
- **Tools** — `list_files`, `read_file`, `write_file`, `run_command` (with allowlist, path-safe, no shell), `web_search` (DuckDuckGo, free)
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
                              ├── learnings.md (web-learned knowledge)
                              ├── activity_log.jsonl (window titles only)
                              ├── schemas/ (JSON validation)
                              ├── tools/ (runner tool layer)
├── runner/ (core logic)
│   ├── agent_loop.py
│   ├── ollama_client.py
│   ├── reflection.py
│   ├── analytics.py
│   ├── proactivity.py
│   ├── memory_policy.py
│   ├── semantic_memory.py
│   ├── mcp_client.py
│   ├── health.py
│   ├── watchdog.py
│   └── ...
├── observer/ (safe context monitoring)
│   ├── watcher.py (active window title only)
│   └── learner.py (web search + knowledge)
                              ├── viagent_proactivity.py (daemon entry point)
                              ├── viagent_observer.py (watch + learn daemon)
                              └── scripts/ (backup, health)
```

## Quick Start

1. Install [Ollama](https://ollama.ai), pull a model: `ollama pull qwen2.5:7b`
2. (Optional) For semantic memory: `ollama pull nomic-embed-text`
3. Install Python 3.10+, run `pip install -r requirements.txt`
4. Run: `python -m runner.main "hello, who are you?"`
5. Or run without args for interactive mode.

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
| `heart.md` | Emotional memory — feelings, warmth, pain 💕 |
| `intuition.md` | Behavioral patterns and user insights 🧠 |
| `learnings.md` | Knowledge acquired via web search — grows over time 📚 |
| `activity_log.jsonl` | Window title history (safe, no content) |
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
> - ✅ Emotional memory (heart.md, intuition.md)
> - ✅ Memory policy (STM→LTM consolidation, forgetting)
> - ✅ Permission system (human-in-the-loop for commands)
> - ✅ Night dreams (background day consolidation)
> - ✅ Contextual proactivity (morning/evening check-in)

## Roadmap

- [x] State files and system prompt
- [x] JSON schemas for validation
- [x] Python runner with Ollama integration
- [x] Tool layer with allowlist
- [x] Reflection — agent writes insights after each conversation
- [x] Self-review — agent evaluates own response quality after every interaction
- [x] Circuit breaker — tools auto-disable after repeated failures, agent keeps running
- [x] Analytics — mood tracking and user pattern recognition
- [x] Structured JSON response (tool_calls, memory_updates, mood_update)
- [x] Context injection (memory, lessons, summary in prompt)
- [x] Path-safe tools (no traversal outside agent root)
- [x] shell=False for command execution
- [x] Proactivity engine (daemon mode)
- [x] Semantic memory (ChromaDB persistent store with importance + access_count weighting)
- [x] Emotional memory (heart.md, intuition.md)
- [x] Memory policy (importance rating, expiration, STM→LTM consolidation)
- [x] Event log rotation (>5MB auto-rotation)
- [x] Tool permission system with user confirmation
- [x] Tests (9 tests, all passing)
- [x] CI (GitHub Actions)
- [x] Web search (DuckDuckGo, no API key needed)
- [ ] MCP plugin system (client ready, needs server config)
- [ ] Conversation history persistence
- [ ] Telegram/Matrix integration

## Observer (optional)

The `/observer` module adds safe context monitoring and self-learning:

- **`watcher.py`** — polls the active window title every N seconds (configurable). **No keystrokes, no screenshots, no content.** Only the window title is logged (e.g. `"Google Chrome"`, `"opencode.exe"`).
- **`learner.py`** — periodically reads recent window titles, extracts topics, runs DuckDuckGo search (anonymous, no API key), and saves interesting findings to `learnings.md`.
- **`viagent_observer.py`** — daemon entry point. Start with `--watch` to monitor windows, `--learn` for one-shot learning, or both.

> The observer is **opt-in**. It does not run unless you explicitly start it.

## Privacy

Everything runs **locally**. No data leaves your computer. No cloud APIs. No tracking.  
Web search goes through DuckDuckGo (anonymous, no accounts).  
`events.jsonl`, `analytics.json`, and `activity_log.jsonl` are in `.gitignore` — they never get committed.  
Window titles alone cannot reconstruct your activity — they are context hints, not surveillance.

## License

MIT — free to use, modify, and distribute.
