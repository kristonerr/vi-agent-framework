"""Semantic memory — associative recall using Ollama embeddings.
No external dependencies, no ChromaDB, no Docker.
Stores vectors in a local JSON file.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

STORE_PATH = "semantic_store.json"
EMBED_MODEL = "nomic-embed-text"
TOP_K_DEFAULT = 5
SIMILARITY_THRESHOLD = 0.5


class SemanticMemory:
    def __init__(self, ollama_client=None):
        self.ollama = ollama_client
        self.store = self._load_store()

    # --- Загрузка/сохранение хранилища ---

    def _load_store(self) -> dict:
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "entries" in data:
                    return data
                return {"version": 1, "entries": []}
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": 1, "entries": []}

    def _save_store(self):
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.store, f, ensure_ascii=False, indent=2)

    # --- Эмбеддинг ---

    def _get_embedding(self, text: str) -> Optional[list[float]]:
        if not self.ollama:
            return None
        try:
            response = self.ollama._request("POST", "/api/embed", {
                "model": EMBED_MODEL,
                "input": text,
            })
            data = response.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
            return None
        except Exception as e:
            logging.warning(f"Embedding failed: {e}")
            return None

    # --- Добавление записи ---

    def add(self, text: str, source: str = "conversation", importance: int = 5) -> bool:
        embedding = self._get_embedding(text)
        if not embedding:
            return False

        entry = {
            "id": len(self.store["entries"]) + 1,
            "text": text,
            "embedding": embedding,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "importance": importance,
        }
        self.store["entries"].append(entry)
        self._save_store()
        return True

    def add_batch(self, items: list[tuple[str, str, int]]) -> int:
        """Добавляет несколько записей: [(text, source, importance), ...]."""
        added = 0
        for text, source, importance in items:
            if self.add(text, source, importance):
                added += 1
        return added

    # --- Поиск ассоциаций ---

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: str, top_k: int = TOP_K_DEFAULT) -> list[dict]:
        """Ищет самые похожие записи по запросу."""
        query_emb = self._get_embedding(query)
        if not query_emb or not self.store["entries"]:
            return []

        scored = []
        for entry in self.store["entries"]:
            sim = self._cosine_similarity(query_emb, entry["embedding"])
            if sim >= SIMILARITY_THRESHOLD:
                scored.append((sim, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        return [
            {
                "text": entry["text"],
                "similarity": round(sim, 3),
                "source": entry["source"],
                "importance": entry.get("importance", 5),
            }
            for sim, entry in top
        ]

    def associate(self, text: str) -> str:
        """Возвращает строку ассоциаций для вставки в промпт."""
        results = self.search(text)
        if not results:
            return ""

        lines = ["--- ASSOCIATIONS ---"]
        for r in results:
            tag = "🔗" if r["similarity"] > 0.7 else "📎"
            lines.append(f"{tag} [{r['source']}] (match: {r['similarity']:.0%}) {r['text']}")
        return "\n".join(lines)

    # --- Обслуживание ---

    def count(self) -> int:
        return len(self.store["entries"])

    def clear(self):
        self.store = {"version": 1, "entries": []}
        self._save_store()

    def prune_low_importance(self, min_importance: int = 3):
        """Удаляет записи с низкой важностью."""
        before = len(self.store["entries"])
        self.store["entries"] = [
            e for e in self.store["entries"]
            if e.get("importance", 5) >= min_importance
        ]
        after = len(self.store["entries"])
        removed = before - after
        if removed:
            self._save_store()
            logging.info(f"Pruned {removed} low-importance entries from semantic store")
        return removed
