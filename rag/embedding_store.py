"""
EmbeddingStore — File-based RAG vector store.

Day 4 concept: Retrieval Augmented Generation (RAG).
Connect agents to a curated knowledge base via semantic search,
so responses cite relevant educational content instead of hallucinating.

Zero infra design:
  - Embeddings stored as a flat JSON file (no Pinecone, no ChromaDB, no Redis)
  - Cosine similarity in pure Python math (no numpy)
  - Embedding model: text-embedding-004 via Gemini REST API (free tier)
  - Knowledge base: pre-seeded educational content chunks (see knowledge_base.py)

Usage:
    store = EmbeddingStore(api_key)
    await store.build()          # embed all chunks once, saves to embeddings.json
    results = await store.retrieve("photosynthesis", top_k=3)
    # Returns list of {"chunk_id", "text", "subject", "score"}
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import httpx

EMBEDDINGS_PATH = Path(__file__).parent / "embeddings.json"
EMBEDDING_MODEL = "text-embedding-004"
GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{EMBEDDING_MODEL}:embedContent"
)


# ---------------------------------------------------------------------------
# Knowledge chunk schema
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeChunk:
    chunk_id: str
    subject: str
    grade_range: str       # e.g. "5-8"
    topic: str
    text: str
    source: str            # e.g. "Khan Academy", "curated"


@dataclass
class EmbeddedChunk:
    chunk_id: str
    subject: str
    grade_range: str
    topic: str
    text: str
    source: str
    embedding: list[float]


@dataclass
class RetrievalResult:
    chunk_id: str
    subject: str
    topic: str
    text: str
    source: str
    score: float           # cosine similarity [0, 1]


# ---------------------------------------------------------------------------
# Pure-Python cosine similarity (no numpy)
# ---------------------------------------------------------------------------

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    na, nb = _norm(a), _norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return _dot(a, b) / (na * nb)


# ---------------------------------------------------------------------------
# EmbeddingStore
# ---------------------------------------------------------------------------

class EmbeddingStore:
    """
    File-based embedding store.

    Build once (embed all chunks → save to embeddings.json).
    Retrieve anytime (load embeddings.json → cosine similarity search).
    """

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._chunks: list[EmbeddedChunk] = []
        self._built = False

    async def _embed(self, text: str) -> list[float]:
        """Call Gemini text-embedding-004 to embed a single string."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_EMBED_URL}?key={self._api_key}",
                json={
                    "model": f"models/{EMBEDDING_MODEL}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]

    async def _embed_query(self, text: str) -> list[float]:
        """Embed a query string (task type differs for retrieval quality)."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{GEMINI_EMBED_URL}?key={self._api_key}",
                json={
                    "model": f"models/{EMBEDDING_MODEL}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": "RETRIEVAL_QUERY",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]

    async def build(self, chunks: list[KnowledgeChunk], force: bool = False) -> None:
        """
        Embed all knowledge chunks and save to embeddings.json.
        Skip if embeddings.json already exists (idempotent).
        """
        if EMBEDDINGS_PATH.exists() and not force:
            self._load()
            return

        embedded: list[EmbeddedChunk] = []
        for i, chunk in enumerate(chunks):
            print(f"[EmbeddingStore] Embedding {i+1}/{len(chunks)}: {chunk.chunk_id}")
            try:
                vec = await self._embed(chunk.text)
                embedded.append(
                    EmbeddedChunk(
                        chunk_id=chunk.chunk_id,
                        subject=chunk.subject,
                        grade_range=chunk.grade_range,
                        topic=chunk.topic,
                        text=chunk.text,
                        source=chunk.source,
                        embedding=vec,
                    )
                )
                time.sleep(0.1)  # avoid rate limiting
            except Exception as e:
                print(f"[EmbeddingStore] Failed to embed {chunk.chunk_id}: {e}")

        EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        EMBEDDINGS_PATH.write_text(
            json.dumps([asdict(c) for c in embedded], indent=2)
        )
        self._chunks = embedded
        self._built = True
        print(f"[EmbeddingStore] Saved {len(embedded)} embeddings → {EMBEDDINGS_PATH}")

    def _load(self) -> None:
        """Load pre-built embeddings from disk."""
        raw = json.loads(EMBEDDINGS_PATH.read_text())
        self._chunks = [EmbeddedChunk(**r) for r in raw]
        self._built = True

    def load_if_exists(self) -> bool:
        """Load embeddings if the file exists. Returns True if loaded."""
        if EMBEDDINGS_PATH.exists():
            self._load()
            return True
        return False

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        subject_filter: str | None = None,
        grade_level: int | None = None,
    ) -> list[RetrievalResult]:
        """
        Semantic search over the knowledge base.

        1. Embed the query
        2. Cosine similarity against all chunks
        3. Optional subject + grade filter
        4. Return top_k results
        """
        if not self._built:
            if not self.load_if_exists():
                return []

        query_vec = await self._embed_query(query)

        scored: list[tuple[float, EmbeddedChunk]] = []
        for chunk in self._chunks:
            # Subject filter
            if subject_filter and chunk.subject.lower() != subject_filter.lower():
                if chunk.subject.lower() != "general":
                    continue
            # Grade filter: parse grade_range "5-8" and check overlap
            if grade_level is not None:
                try:
                    lo, hi = (int(x) for x in chunk.grade_range.split("-"))
                    if not (lo <= grade_level <= hi):
                        continue
                except ValueError:
                    pass

            score = cosine_similarity(query_vec, chunk.embedding)
            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            RetrievalResult(
                chunk_id=c.chunk_id,
                subject=c.subject,
                topic=c.topic,
                text=c.text,
                source=c.source,
                score=round(s, 4),
            )
            for s, c in scored[:top_k]
        ]

    def format_context(self, results: list[RetrievalResult]) -> str:
        """Format retrieved chunks for injection into agent prompt context."""
        if not results:
            return ""
        lines = ["\n\n## Retrieved Knowledge (RAG)\n"]
        for r in results:
            lines.append(
                f"**{r.topic}** ({r.source}, score={r.score:.2f})\n{r.text}\n"
            )
        return "\n".join(lines)


# Singleton store (initialized lazily per request in serverless context)
_store: EmbeddingStore | None = None


def get_store(api_key: str) -> EmbeddingStore:
    global _store
    if _store is None:
        _store = EmbeddingStore(api_key)
        _store.load_if_exists()
    return _store
