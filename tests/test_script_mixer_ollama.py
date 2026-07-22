from __future__ import annotations

from pathlib import Path

from short_drama_controller.script_mixer.catalog import MediaCatalog
from short_drama_controller.script_mixer.enrichment import MediaEnricher
from short_drama_controller.script_mixer.models import MediaClip, ScriptUnit
from short_drama_controller.script_mixer.ollama_adapter import (
    OllamaClient,
    OllamaIntentProvider,
    OllamaModel,
    OllamaVisionProvider,
    VisionClipAnalysis,
)


class FakeModelClient(OllamaClient):
    def __init__(self) -> None:
        super().__init__(base_url="http://invalid")
        self.models = {
            "qwen3:8b": OllamaModel(
                name="qwen3:8b",
                capabilities=["completion"],
                family="qwen3",
            ),
            "qwen3-vl:8b": OllamaModel(
                name="qwen3-vl:8b",
                capabilities=["completion", "vision"],
                family="qwen3vl",
            ),
            "qwen3-embedding:0.6b": OllamaModel(
                name="qwen3-embedding:0.6b",
                capabilities=["embedding"],
                family="qwen3embedding",
            ),
        }

    def list_model_names(self) -> list[str]:
        return list(self.models)

    def show_model(self, name: str) -> OllamaModel:
        return self.models[name]


class FakeGenerateClient(FakeModelClient):
    def generate(self, model, prompt, schema=None, images=None, system="", timeout=None):
        if images:
            return {
                "description": "年轻人在夜间办公室使用电脑工作",
                "subjects": ["年轻人", "电脑"],
                "scene": "夜间办公室",
                "actions": ["敲键盘"],
                "emotions": ["专注", "疲惫"],
                "tags": ["工作", "自媒体"],
                "shot_type": "中近景",
                "camera_motion": "静止",
                "has_watermark": False,
                "quality_score": 0.9,
            }
        return {
            "literal_queries": ["人物深夜工作", "电脑操作"],
            "metaphor_queries": ["重复循环的工作"],
            "positive_tags": ["办公室", "努力"],
            "negative_tags": ["庆祝"],
            "emotion": ["疲惫"],
            "preferred_shots": ["中近景", "手部特写"],
        }


def test_model_selection_uses_capabilities() -> None:
    client = FakeModelClient()
    text = client.select_model("completion")
    vision = client.select_model("vision")
    embedding = client.select_model("embedding")
    assert text is not None
    assert vision is not None
    assert embedding is not None
    assert text.name == "qwen3:8b"
    assert vision.name == "qwen3-vl:8b"
    assert embedding.name == "qwen3-embedding:0.6b"


def test_ollama_intent_provider_returns_visual_intent() -> None:
    provider = OllamaIntentProvider(FakeGenerateClient(), "qwen3:8b")
    unit = ScriptUnit(
        unit_id="U001",
        text="努力不等于有效增长",
        start=0.0,
        end=2.0,
        duration=2.0,
        role="hook",
    )
    intent = provider.generate(unit)
    assert intent.unit_id == "U001"
    assert "人物深夜工作" in intent.literal_queries
    assert "庆祝" in intent.negative_tags


def test_ollama_vision_provider_reads_thumbnail(tmp_path: Path) -> None:
    image = tmp_path / "frame.jpg"
    image.write_bytes(b"fake-jpeg")
    provider = OllamaVisionProvider(FakeGenerateClient(), "qwen3-vl:8b")
    result = provider.analyze(image)
    assert result.scene == "夜间办公室"
    assert result.has_watermark is False
    assert result.quality_score == 0.9


class FakeVisionProvider:
    def analyze(self, image_path: str | Path) -> VisionClipAnalysis:
        return VisionClipAnalysis(
            description="城市夜景中一名人物快速行走",
            subjects=["人物"],
            scene="城市夜景",
            actions=["行走"],
            emotions=["焦虑"],
            tags=["城市", "夜晚"],
            shot_type="全景",
            camera_motion="跟拍",
            has_watermark=False,
            quality_score=0.8,
        )


def test_media_enricher_updates_catalog(tmp_path: Path) -> None:
    thumbnail = tmp_path / "thumb.jpg"
    thumbnail.write_bytes(b"image")
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    catalog.upsert_clip(
        MediaClip(
            clip_id="C001",
            source_id="SRC001",
            source_path="D:/media/source.mp4",
            source_start=0.0,
            source_end=2.0,
            duration=2.0,
            description="",
            tags=["原标签"],
            thumbnail_path=str(thumbnail),
        )
    )
    summary = MediaEnricher(catalog, FakeVisionProvider()).enrich()
    assert summary.analyzed == 1
    updated = catalog.list_clips(usable_only=False)[0]
    assert updated.description == "城市夜景中一名人物快速行走"
    assert "城市夜景" in updated.tags
    assert updated.shot_type == "全景"
