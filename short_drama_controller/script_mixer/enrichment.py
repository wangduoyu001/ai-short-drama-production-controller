from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .catalog import MediaCatalog
from .ollama_adapter import OllamaError, OllamaVisionProvider


@dataclass(slots=True)
class EnrichmentSummary:
    requested: int = 0
    analyzed: int = 0
    skipped: int = 0
    failed: int = 0
    watermarked: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "requested": self.requested,
            "analyzed": self.analyzed,
            "skipped": self.skipped,
            "failed": self.failed,
            "watermarked": self.watermarked,
            "errors": self.errors,
        }


class MediaEnricher:
    def __init__(
        self,
        catalog: MediaCatalog,
        provider: OllamaVisionProvider,
    ):
        self.catalog = catalog
        self.provider = provider

    def enrich(
        self,
        limit: int | None = None,
        force: bool = False,
    ) -> EnrichmentSummary:
        clips = self.catalog.list_clips(usable_only=False)
        if limit is not None:
            clips = clips[: max(0, limit)]
        summary = EnrichmentSummary(requested=len(clips))

        for clip in clips:
            thumbnail = Path(clip.thumbnail_path) if clip.thumbnail_path else None
            if thumbnail is None or not thumbnail.is_file():
                summary.skipped += 1
                continue
            if not force and clip.description and clip.shot_type != "unknown" and clip.emotions:
                summary.skipped += 1
                continue
            try:
                analysis = self.provider.analyze(thumbnail)
            except (OllamaError, FileNotFoundError, OSError, ValueError) as exc:
                summary.failed += 1
                summary.errors.append(f"{clip.clip_id}: {exc}")
                continue

            merged_tags = [
                *clip.tags,
                *analysis.subjects,
                analysis.scene,
                *analysis.actions,
                *analysis.tags,
            ]
            clip.tags = list(dict.fromkeys(item.strip() for item in merged_tags if item.strip()))[:32]
            clip.description = analysis.description or clip.description
            clip.emotions = analysis.emotions
            clip.shot_type = analysis.shot_type or "unknown"
            clip.camera_motion = analysis.camera_motion or "unknown"
            clip.has_watermark = analysis.has_watermark
            clip.usable = clip.usable and not analysis.has_watermark
            clip.quality_score = round(
                max(0.0, min(1.0, clip.quality_score * 0.4 + analysis.quality_score * 0.6)),
                4,
            )
            self.catalog.upsert_clip(clip)
            summary.analyzed += 1
            if analysis.has_watermark:
                summary.watermarked += 1
        return summary
