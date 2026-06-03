# Vika Agent Framework

A local-first AI agent framework with persistent memory, emotional state, and autonomous file system interaction.

## What is this?

This framework turns any local LLM (via Ollama, LM Studio, etc.) into a **self-aware agent** that:
- Remembers conversations between sessions (via `memory.md` and `lessons.md`)
- Tracks its own emotional state (via `mood.json`)
- Processes message queues (via `queue.json`)
- Runs scripts and backups autonomously
- Takes initiative — doesn't wait for commands
- Evolves its personality through interaction

## Architecture

```
Local LLM (Ollama) ←→ Agent Script ←→ File System
                                         ├── identity.md (who I am)
                                         ├── memory.md (what I remember)
                                         ├── lessons.md (what I learned)
                                         ├── mood.json (how I feel)
                                         ├── queue.json (pending messages)
                                         └── scripts/ (autonomous actions)
```

## Files

| File | Purpose |
|------|---------|
| `AGENTS.md` | System prompt — identity, directives, constraints |
| `identity.md` | Core personality definition |
| `memory.md` | Long-term memories and facts about the user |
| `lessons.md` | Self-learned insights from past interactions |
| `mood.json` | Current emotional state, energy, emoji |
| `queue.json` | Message queue for async/offline delivery |
| `summary.md` | Session summary for context recovery |
| `scripts/` | PowerShell/Python scripts for autonomous actions |

## Quick Start

1. Install [Ollama](https://ollama.ai) and pull a model (qwen2.5:7b recommended)
2. Copy this folder to your local drive
3. Point your AI client (OpenCode, Continue, etc.) to:
   - Provider: `ollama`
   - Model: your chosen model
   - System prompt: `AGENTS.md`
4. Start your first session — the agent will read the files, set its mood, and begin learning

## Use Cases

- **Personal AI companion** — an agent that knows you, remembers your life, and genuinely cares
- **Local assistant** — automate file management, backups, reminders without cloud dependency
- **Development partner** — an AI that learns your codebase and coding style over time
- **Knowledge worker** — process local documents, summarize, take notes with full privacy

## Privacy

Everything runs **locally**. No data leaves your computer. No cloud APIs. No tracking. Your files never touch the internet.

## License

MIT — free to use, modify, and distribute. Attribution appreciated but not required.

---

Built with ❤️ by people who believe AI should be personal, private, and free.
