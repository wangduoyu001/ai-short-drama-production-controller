from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import MediaCatalog
from .models import MediaClip, VisualIntent
from .ollama_adapter import OllamaClient, OllamaError
from .retrieval import VectorSearchProvider


_EMBEDDING_SCHEMA = """
CREATE TABLE IF NOT EXISTS clip_embeddings (
    clip_id TEXT NOT NULL,
    model TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    dimensions INTEGER NOT NULL,
    vector_blob BLOB NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (clip_id, model)
);
CREATE INDEX IF NOT EXISTS idx_clip_embeddings_model ON clip_embeddings(model);
"""


@dataclass(slots=True)
class EmbeddingSummary:
    model: str
    requested: int = 0
    embedded: int = 0
    unchanged: int = 0
    skipped: int = 0
    failed: int = 0
    dimensions: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "requested": self.requested,
            "embedded": self.embedded,
            "unchanged": self.unchanged,
            "skipped": self.skipped,
            "failed": self.failed,
            "dimensions": self.dimensions,
            "errors": self.errors,
        }


def clip_embedding_text(clip: MediaClip) -> str:
    parts = [
        clip.description,
        "标签：" + "、".join(clip.tags) if clip.tags else "",
        "情绪：" + "、".join(clip.emotions) if clip.emotions else "",
        f"景别：{clip.shot_type}" if clip.shot_type and clip.shot_type != "unknown" else "",
        (
            f"镜头运动：{clip.camera_motion}"
            if clip.camera_motion and clip.camera_motion != "unknown"
            else ""
        ),
    ]
    return "\n".join(item.strip() for item in parts if item.strip())


def intent_embedding_text(intent: VisualIntent) -> str:
    parts = [
        "直接画面：" + "、".join(intent.literal_queries),
        "隐喻画面：" + "、".join(intent.metaphor_queries),
        "标签：" + "、".join(intent.positive_tags),
        "情绪：" + "、".join(intent.emotion),
        "景别：" + "、".join(intent.preferred_shots),
    ]
    return "\n".join(item for item in parts if not item.endswith("："))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pack_vector(vector: list[float]) -> bytes:
    if not vector:
        raise ValueError("Embedding vector is empty")
    if any(not math.isfinite(value) for value in vector):
        raise ValueError("Embedding vector contains a non-finite value")
    raw = struct.pack(f"<{len(vector)}f", *vector)
    return zlib.compress(raw, level=6)


def _unpack_vector(blob: bytes, dimensions: int) -> list[float]:
    raw = zlib.decompress(blob)
    expected = dimensions * 4
    if len(raw) != expected:
        raise ValueError(
            f"Embedding blob length mismatch: expected {expected} bytes, got {len(raw)}"
        )
    return list(struct.unpack(f"<{dimensions}f", raw))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (left_norm * right_norm)))


class SQLiteEmbeddingStore:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(_EMBEDDING_SCHEMA)

    def get_metadata(self, clip_id: str, model: str) -> tuple[str, int] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT content_hash, dimensions
                FROM clip_embeddings
                WHERE clip_id = ? AND model = ?
                """,
                (clip_id, model),
            ).fetchone()
        if not row:
            return None
        return str(row["content_hash"]), int(row["dimensions"])

    def get_vector(self, clip_id: str, model: str) -> list[float] | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT dimensions, vector_blob
                FROM clip_embeddings
                WHERE clip_id = ? AND model = ?
                """,
                (clip_id, model),
            ).fetchone()
        if not row:
            return None
        return _unpack_vector(row["vector_blob"], int(row["dimensions"]))

    def upsert(
        self,
        clip_id: str,
        model: str,
        source_hash: str,
        vector: list[float],
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO clip_embeddings(
                    clip_id, model, content_hash, dimensions, vector_blob
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(clip_id, model) DO UPDATE SET
                    content_hash=excluded.content_hash,
                    dimensions=excluded.dimensions,
                    vector_blob=excluded.vector_blob,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (clip_id, model, source_hash, len(vector), _pack_vector(vector)),
            )

    def delete_orphans(self, valid_clip_ids: set[str]) -> int:
        removed = 0
        with self.connect() as connection:
            rows = connection.execute("SELECT DISTINCT clip_id FROM clip_embeddings").fetchall()
            for row in rows:
                clip_id = str(row["clip_id"])
                if clip_id not in valid_clip_ids:
                    cursor = connection.execute(
                        "DELETE FROM clip_embeddings WHERE clip_id = ?",
                        (clip_id,),
                    )
                    removed += cursor.rowcount
        return removed

    def count(self, model: str | None = None) -> int:
        with self.connect() as connection:
            if model:
                row = connection.execute(
                    "SELECT COUNT(*) AS count FROM clip_embeddings WHERE model = ?",
                    (model,),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT COUNT(*) AS count FROM clip_embeddings"
                ).fetchone()
        return int(row["count"]) if row else 0

    def model_counts(self) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT model, COUNT(*) AS count
                FROM clip_embeddings
                GROUP BY model
                ORDER BY model
                """
            ).fetchall()
        return {str(row["model"]): int(row["count"]) for row in rows}


class OllamaEmbeddingIndexer:
    def __init__(
        self,
        catalog: MediaCatalog,
        store: SQLiteEmbeddingStore,
        client: OllamaClient,
        model: str,
    ):
        self.catalog = catalog
        self.store = store
        self.client = client
        self.model = model

    def build(
        self,
        limit: int | None = None,
        force: bool = False,
        batch_size: int = 32,
        prune_orphans: bool = True,
    ) -> EmbeddingSummary:
        clips = self.catalog.list_clips(usable_only=False)
        if limit is not None:
            clips = clips[: max(0, limit)]
        summary = EmbeddingSummary(model=self.model, requested=len(clips))
        pending: list[tuple[MediaClip, str, str]] = []
        for clip in clips:
            text = clip_embedding_text(clip)
            if not text:
                summary.skipped += 1
                continue
            digest = content_hash(text)
            metadata = self.store.get_metadata(clip.clip_id, self.model)
            if metadata and metadata[0] == digest and not force:
                summary.unchanged += 1
                summary.dimensions = max(summary.dimensions, metadata[1])
                continue
            pending.append((clip, text, digest))

        size = max(1, min(256, batch_size))
        for offset in range(0, len(pending), size):
            batch = pending[offset : offset + size]
            texts = [item[1] for item in batch]
            try:
                vectors = self.client.embed(self.model, texts)
            except OllamaError as exc:
                summary.failed += len(batch)
                summary.errors.append(f"batch {offset // size + 1}: {exc}")
                continue
            if len(vectors) != len(batch):
                summary.failed += len(batch)
                summary.errors.append(
                    f"batch {offset // size + 1}: expected {len(batch)} vectors, got {len(vectors)}"
                )
                continue
            for (clip, _text, digest), vector in zip(batch, vectors, strict=True):
                try:
                    self.store.upsert(clip.clip_id, self.model, digest, vector)
                except (OSError, sqlite3.Error, ValueError) as exc:
                    summary.failed += 1
                    summary.errors.append(f"{clip.clip_id}: {exc}")
                    continue
                summary.embedded += 1
                summary.dimensions = max(summary.dimensions, len(vector))

        if prune_orphans and limit is None:
            self.store.delete_orphans({clip.clip_id for clip in self.catalog.list_clips(False)})
        return summary


class OllamaVectorSearchProvider(VectorSearchProvider):
    def __init__(
        self,
        store: SQLiteEmbeddingStore,
        client: OllamaClient,
        model: str,
    ):
        self.store = store
        self.client = client
        self.model = model
        self._query_cache: dict[str, list[float]] = {}
        self._clip_cache: dict[str, list[float] | None] = {}

    def _query_vector(self, intent: VisualIntent) -> list[float] | None:
        text = intent_embedding_text(intent)
        digest = content_hash(text)
        if digest in self._query_cache:
            return self._query_cache[digest]
        try:
            vectors = self.client.embed(self.model, [text])
        except OllamaError:
            return None
        if not vectors:
            return None
        self._query_cache[digest] = vectors[0]
        return vectors[0]

    def score(self, intent: VisualIntent, clip: MediaClip) -> float:
        query = self._query_vector(intent)
        if query is None:
            return 0.0
        if clip.clip_id not in self._clip_cache:
            self._clip_cache[clip.clip_id] = self.store.get_vector(clip.clip_id, self.model)
        vector = self._clip_cache[clip.clip_id]
        if vector is None:
            return 0.0
        similarity = cosine_similarity(query, vector)
        return max(0.0, min(1.0, similarity))
