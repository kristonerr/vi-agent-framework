"""Migrate old semantic_store.json to ChromaDB."""
import json
import logging
import shutil
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

OLD_STORE = Path("semantic_store.json")
BACKUP_PATH = Path("semantic_store.json.backup")


def migrate():
    if not OLD_STORE.exists():
        logging.info("No semantic_store.json found — nothing to migrate")
        return

    try:
        from runner.semantic_memory import SemanticMemory
        from runner.ollama_client import OllamaClient
    except ImportError:
        logging.error("Run this script from the vi-agent-framework root directory")
        return

    ollama = OllamaClient()
    if not ollama.ping():
        logging.error("Ollama is not running. Start it first.")
        return

    with open(OLD_STORE, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data.get("entries", [])
    if not entries:
        logging.info("semantic_store.json is empty — nothing to migrate")
        return

    sm = SemanticMemory(ollama_client=ollama)
    migrated = 0

    for entry in entries:
        text = entry.get("text", "")
        source = entry.get("source", "conversation")
        importance = entry.get("importance", 5)
        if not text:
            continue
        if sm.add(text, source=source, importance=importance):
            migrated += 1

    shutil.copy2(OLD_STORE, BACKUP_PATH)
    OLD_STORE.unlink()

    logging.info(f"Migrated {migrated}/{len(entries)} entries to ChromaDB")
    logging.info(f"Old store backed up to {BACKUP_PATH}")


if __name__ == "__main__":
    migrate()
