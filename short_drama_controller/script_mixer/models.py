from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ToolLocation:
    name: str
    executable: str | None = None
    source: str = "not_found"
    version: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.executable)


@dataclass(slots=True)
class ModelLocation:
    name: str
    path: str | None = None
    source: str = "not_found"
    model_type: str = "unknown"

    @property
    def available(self) -> bool:
        return bool(self.path)


@dataclass(slots=True)
class DiscoveryReport:
    platform: str
    generated_at: str
    tools: dict[str, ToolLocation] = field(default_factory=dict)
    models: dict[str, list[ModelLocation]] = field(default_factory=dict)
    searched_roots: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "generated_at": self.generated_at,
            "tools": {name: asdict(item) | {"available": item.available} for name, item in self.tools.items()},
            "models": {
                name: [asdict(item) | {"available": item.available} for item in items]
                for name, items in self.models.items()
            },
            "searched_roots": self.searched_roots,
            "warnings": self.warnings,
        }


@dataclass(slots=True)
class MediaSource:
    source_id: str
    source_path: str
    filename: str
    extension: str
    file_size: int
    modified_ns: int
    fingerprint: str
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str = ""
    audio_codec: str = ""
    has_audio: bool = False
    rotation: int = 0
    status: str = "ready"
    error: str = ""
    indexed_duration: float = 0.0
    ignored_tail_seconds: float = 0.0

    @property
    def is_vertical(self) -> bool:
        width, height = self.display_dimensions
        return height > width > 0

    @property
    def display_dimensions(self) -> tuple[int, int]:
        if abs(self.rotation) % 180 == 90:
            return self.height, self.width
        return self.width, self.height


@dataclass(slots=True)
class MediaScanSummary:
    root: str
    discovered_files: int = 0
    new_files: int = 0
    changed_files: int = 0
    unchanged_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    capped_files: int = 0
    sources_written: int = 0
    clips_written: int = 0
    thumbnails_written: int = 0
    indexed_duration_seconds: float = 0.0
    ignored_tail_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ScriptUnit:
    unit_id: str
    text: str
    start: float
    end: float
    duration: float
    role: str = "body"
    importance: float = 0.5


@dataclass(slots=True)
class VisualIntent:
    unit_id: str
    literal_queries: list[str]
    metaphor_queries: list[str]
    positive_tags: list[str]
    negative_tags: list[str]
    emotion: list[str]
    preferred_shots: list[str]

    @property
    def all_queries(self) -> list[str]:
        return [*self.literal_queries, *self.metaphor_queries, *self.positive_tags]


@dataclass(slots=True)
class MediaClip:
    clip_id: str
    source_id: str
    source_path: str
    source_start: float
    source_end: float
    duration: float
    description: str = ""
    tags: list[str] = field(default_factory=list)
    emotions: list[str] = field(default_factory=list)
    shot_type: str = "unknown"
    camera_motion: str = "unknown"
    width: int = 0
    height: int = 0
    quality_score: float = 0.5
    has_watermark: bool = False
    usable: bool = True
    thumbnail_path: str = ""
    has_audio: bool = False

    @property
    def is_vertical(self) -> bool:
        return self.height > self.width > 0

    def validate_source(self) -> bool:
        return Path(self.source_path).exists()


@dataclass(slots=True)
class CandidateClip:
    clip: MediaClip
    score: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TimelineSegment:
    segment_id: str
    unit_id: str
    timeline_start: float
    timeline_end: float
    source_id: str
    source_path: str
    source_start: float
    source_end: float
    match_score: float
    crop_mode: str = "center_crop"
    speed: float = 1.0
    audio_enabled: bool = False
    match_reasons: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return round(self.timeline_end - self.timeline_start, 3)


@dataclass(slots=True)
class AudioPlan:
    mode: str = "mute"
    narration_path: str = ""
    narration_duration: float = 0.0
    sample_rate: int = 48000
    channels: int = 2
    source_volume: float = 1.0
    narration_volume: float = 1.0
    normalize_source: bool = False
    normalize_narration: bool = True
    narration_target_lufs: float = -16.0
    source_target_lufs: float = -18.0
    true_peak: float = -1.5
    loudness_range: float = 11.0
    ducking_threshold: float = 0.03
    ducking_ratio: float = 10.0
    ducking_attack_ms: float = 20.0
    ducking_release_ms: float = 300.0
    source_audio_segments: int = 0
    source_audio_coverage: float = 0.0
    transcript_path: str = ""
    transcription_model: str = ""
    transcription_language: str = ""
    timing_source: str = "estimated"
    alignment_coverage: float = 0.0
    subtitle_srt_path: str = ""
    subtitle_ass_path: str = ""
    subtitle_karaoke_ass_path: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Timeline:
    project_id: str
    width: int
    height: int
    fps: int
    duration: float
    segments: list[TimelineSegment]
    audio: AudioPlan = field(default_factory=AudioPlan)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "duration": self.duration,
            "segments": [asdict(item) | {"duration": item.duration} for item in self.segments],
            "audio": asdict(self.audio),
            "warnings": self.warnings,
        }
