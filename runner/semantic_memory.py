import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings

DB_PATH = str(Path(__file__).parent.parent / "chroma_db")
COLLECTION_NAME = "vika_memories"
EMBED_MODEL = "nomic-embed-text"
TOP_K_DEFAULT = 5
SIMILARITY_THRESHOLD = 0.5


class SemanticMemory:
    def __init__(self, ollama_client=None):
        self.ollama = ollama_client
        self.client = chromadb.PersistentClient(path=DB_PATH, settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logging.info(f"ChromaDB loaded: {self.collection.count()} vectors")

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

    def add(self, text: str, source: str = "conversation", importance: int = 5) -> bool:
        embedding = self._get_embedding(text)
        if not embedding:
            return False

        entry_id = str(self.collection.count() + 1)
        timestamp = datetime.now(timezone.utc).isoformat()

        self.collection.add(
            ids=[entry_id],
            embeddings=[embedding],
            metadatas=[{
                "text": text,
                "source": source,
                "importance": importance,
                "timestamp": timestamp,
                "access_count": 0,
            }],
        )
        return True

    def add_batch(self, items: list[tuple[str, str, int]]) -> int:
        added = 0
        for text, source, importance in items:
            if self.add(text, source, importance):
                added += 1
        return added

    def search(self, query: str, top_k: int = TOP_K_DEFAULT) -> list[dict]:
        query_emb = self._get_embedding(query)
        if not query_emb:
            return []

        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=top_k,
            include=["metadatas", "distances"],
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        entries = []
        for i in range(len(results["ids"][0])):
            dist = results["distances"][0][i]
            similarity = 1.0 - dist
            if similarity < SIMILARITY_THRESHOLD:
                continue

            meta = results["metadatas"][0][i]
            entries.append({
                "text": meta["text"],
                "similarity": round(similarity, 3),
                "source": meta.get("source", ""),
                "importance": meta.get("importance", 5),
                "access_count": meta.get("access_count", 0),
                "id": results["ids"][0][i],
            })

            self._increment_access(results["ids"][0][i])

        entries.sort(key=self._score_entry, reverse=True)
        return entries

    @staticmethod
    def _score_entry(e: dict) -> float:
        sim = e.get("similarity", 0)
        imp = e.get("importance", 5) / 10.0
        access = math.log1p(e.get("access_count", 0)) * 0.05
        return sim * 0.6 + imp * 0.3 + access * 0.1

    def _increment_access(self, entry_id: str):
        try:
            result = self.collection.get(ids=[entry_id], include=["metadatas"])
            if result["metadatas"]:
                meta = dict(result["metadatas"][0])
                meta["access_count"] = meta.get("access_count", 0) + 1
                self.collection.update(ids=[entry_id], metadatas=[meta])
        except Exception as e:
            logging.warning(f"Failed to increment access_count: {e}")

    def associate(self, text: str) -> str:
        results = self.search(text)
        if not results:
            return ""

        lines = ["--- ASSOCIATIONS ---"]
        for r in results:
            tag = "🔗" if r["similarity"] > 0.7 else "📎"
            lines.append(f"{tag} [{r['source']}] (match: {r['similarity']:.0%}, imp:{r['importance']}) {r['text']}")
        return "\n".join(lines)

    def count(self) -> int:
        return self.collection.count()

    def clear(self):
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def prune_low_importance(self, min_importance: int = 3, max_age_days: int = 30) -> int:
        all_data = self.collection.get(include=["metadatas"])
        if not all_data["ids"]:
            return 0

        now = datetime.now(timezone.utc)
        to_delete = []
        for i in range(len(all_data["ids"])):
            meta = all_data["metadatas"][i]
            imp = meta.get("importance", 5)
            access = meta.get("access_count", 0)
            ts_str = meta.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str) if ts_str else datetime.min.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = datetime.min.replace(tzinfo=timezone.utc)

            age_days = (now - ts).days
            if age_days > max_age_days and imp < min_importance and access == 0:
                to_delete.append(all_data["ids"][i])

        if to_delete:
            self.collection.delete(ids=to_delete)
            logging.info(f"Pruned {len(to_delete)} low-importance entries from semantic store")
        return len(to_delete)
