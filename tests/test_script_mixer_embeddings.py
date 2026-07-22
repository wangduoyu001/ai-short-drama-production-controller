from __future__ import annotations

from pathlib import Path

from short_drama_controller.script_mixer.catalog import MediaCatalog
from short_drama_controller.script_mixer.embeddings import (
    OllamaEmbeddingIndexer,
    OllamaVectorSearchProvider,
    SQLiteEmbeddingStore,
    cosine_similarity,
)
from short_drama_controller.script_mixer.models import MediaClip, VisualIntent
from short_drama_controller.script_mixer.ollama_adapter import OllamaClient
from short_drama_controller.script_mixer.retrieval import HybridRetriever


class FakeEmbeddingClient(OllamaClient):
    def __init__(self) -> None:
        super().__init__(base_url="http://invalid")
        self.calls = 0

    def embed(self, model, inputs, truncate=True, dimensions=None, timeout=None):
        self.calls += 1
        rows = [inputs] if isinstance(inputs, str) else inputs
        vectors = []
        for text in rows:
            lowered = text.casefold()
            vector = [
                1.0 if "办公室" in lowered or "电脑" in lowered else 0.0,
                1.0 if "城市" in lowered or "街道" in lowered else 0.0,
                1.0 if "疲惫" in lowered or "工作" in lowered else 0.0,
                1.0 if "庆祝" in lowered or "胜利" in lowered else 0.0,
            ]
            norm = sum(value * value for value in vector) ** 0.5 or 1.0
            vectors.append([value / norm for value in vector])
        return vectors


def _clip(clip_id: str, description: str, tags: list[str]) -> MediaClip:
    return MediaClip(
        clip_id=clip_id,
        source_id=f"SRC_{clip_id}",
        source_path=f"D:/media/{clip_id}.mp4",
        source_start=0.0,
        source_end=2.0,
        duration=2.0,
        description=description,
        tags=tags,
        quality_score=0.8,
    )


def _intent() -> VisualIntent:
    return VisualIntent(
        unit_id="U001",
        literal_queries=["人物深夜使用电脑工作"],
        metaphor_queries=["持续努力但十分疲惫"],
        positive_tags=["办公室"],
        negative_tags=["庆祝"],
        emotion=["疲惫"],
        preferred_shots=["中近景"],
    )


def test_cosine_similarity() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([], []) == 0.0


def test_embedding_store_roundtrip(tmp_path: Path) -> None:
    store = SQLiteEmbeddingStore(tmp_path / "media.db")
    store.upsert("C001", "embed-model", "hash", [0.1, 0.2, 0.3])
    vector = store.get_vector("C001", "embed-model")
    assert vector is not None
    assert len(vector) == 3
    assert abs(vector[1] - 0.2) < 1e-6
    assert store.model_counts() == {"embed-model": 1}


def test_embedding_indexer_is_incremental(tmp_path: Path) -> None:
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    catalog.upsert_many(
        [
            _clip("C001", "夜间办公室人物敲电脑", ["办公室", "工作"]),
            _clip("C002", "城市街道车辆行驶", ["城市", "街道"]),
        ]
    )
    store = SQLiteEmbeddingStore(tmp_path / "media.db")
    client = FakeEmbeddingClient()
    indexer = OllamaEmbeddingIndexer(catalog, store, client, "embed-model")

    first = indexer.build(batch_size=2)
    assert first.embedded == 2
    assert first.unchanged == 0
    assert first.dimensions == 4
    assert client.calls == 1

    second = indexer.build(batch_size=2)
    assert second.embedded == 0
    assert second.unchanged == 2
    assert client.calls == 1

    changed = catalog.list_clips(usable_only=False)[0]
    changed.description = "庆祝胜利的人群"
    catalog.upsert_clip(changed)
    third = indexer.build(batch_size=2)
    assert third.embedded == 1
    assert third.unchanged == 1
    assert client.calls == 2


def test_vector_provider_changes_hybrid_ranking(tmp_path: Path) -> None:
    office = _clip("C001", "人物在房间里", ["普通画面"])
    city = _clip("C002", "城市街道", ["城市"])
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    catalog.upsert_many([office, city])
    store = SQLiteEmbeddingStore(tmp_path / "media.db")
    client = FakeEmbeddingClient()
    indexer = OllamaEmbeddingIndexer(catalog, store, client, "embed-model")
    indexer.build()

    provider = OllamaVectorSearchProvider(store, client, "embed-model")
    retriever = HybridRetriever(vector_provider=provider)
    results = retriever.retrieve(_intent(), [office, city])
    assert results[0].clip.clip_id == "C001"
    assert any(reason.startswith("vector=") for reason in results[0].reasons)
