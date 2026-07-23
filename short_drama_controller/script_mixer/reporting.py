from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .models import Timeline


def build_timeline_report(
    timeline: Timeline,
    config: RuntimeConfig,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_seconds: dict[str, float] = defaultdict(float)
    source_counts: Counter[str] = Counter()
    low_match_segments: list[str] = []
    missing_media_segments: list[str] = []
    source_window_violations: list[str] = []
    adjacent_same_source: list[tuple[str, str]] = []
    cap = config.media_scan.maximum_source_process_seconds

    for index, segment in enumerate(timeline.segments):
        source_seconds[segment.source_id] += segment.duration
        source_counts[segment.source_id] += 1
        if segment.match_score < config.mixing.low_match_threshold:
            low_match_segments.append(segment.segment_id)
        if not Path(segment.source_path).is_file():
            missing_media_segments.append(segment.segment_id)
        if cap > 0 and segment.source_end > cap + 0.001:
            source_window_violations.append(segment.segment_id)
        if index > 0 and timeline.segments[index - 1].source_id == segment.source_id:
            adjacent_same_source.append((timeline.segments[index - 1].segment_id, segment.segment_id))

    highest_source_ratio = (
        max(source_seconds.values()) / timeline.duration
        if source_seconds and timeline.duration > 0
        else 0.0
    )
    blocking_warnings: list[str] = []
    if len(source_seconds) < config.mixing.minimum_source_count:
        blocking_warnings.append(
            f"unique source count {len(source_seconds)} is below required "
            f"{config.mixing.minimum_source_count}"
        )
    for source_id, seconds in sorted(source_seconds.items()):
        if seconds > config.mixing.max_single_source_seconds + 0.001:
            blocking_warnings.append(
                f"source {source_id} uses {seconds:.3f}s, above "
                f"{config.mixing.max_single_source_seconds:.3f}s"
            )
        ratio = seconds / timeline.duration if timeline.duration else 0.0
        if ratio > config.mixing.max_single_source_ratio + 0.001:
            blocking_warnings.append(
                f"source {source_id} ratio {ratio:.1%} exceeds "
                f"{config.mixing.max_single_source_ratio:.1%}"
            )
    if adjacent_same_source:
        blocking_warnings.append(
            "adjacent same-source segments: "
            + ", ".join(f"{left}/{right}" for left, right in adjacent_same_source)
        )
    if missing_media_segments:
        blocking_warnings.append(
            f"missing source files for segments: {', '.join(missing_media_segments)}"
        )
    if source_window_violations:
        blocking_warnings.append(
            f"segments exceed the source-processing window: "
            f"{', '.join(source_window_violations)}"
        )

    audio_blockers: list[str] = []
    if timeline.audio.mode == "source" and timeline.audio.source_audio_coverage < 0.5:
        audio_blockers.append(
            f"source audio coverage {timeline.audio.source_audio_coverage:.1%} is below 50%"
        )
    if timeline.audio.mode in {"narration", "mixed"} and timeline.audio.narration_duration <= 0:
        audio_blockers.append("narration duration is unavailable")

    review_payload = review or {}
    review_payload.setdefault("locked_segment_count", sum(item.locked for item in timeline.segments))
    review_payload.setdefault(
        "review_status_counts",
        dict(Counter(item.review_status for item in timeline.segments)),
    )
    review_payload.setdefault(
        "replaced_segment_count",
        sum(item.review_status == "replaced" for item in timeline.segments),
    )

    subtitle_review_required = bool(
        timeline.audio.mode in {"narration", "mixed"}
        and timeline.audio.timing_source != "whisper_alignment"
    )
    warnings = list(
        dict.fromkeys(
            [
                *timeline.warnings,
                *blocking_warnings,
                *timeline.audio.warnings,
            ]
        )
    )
    return {
        "project_id": timeline.project_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "duration": timeline.duration,
        "segment_count": len(timeline.segments),
        "unique_source_count": len(source_seconds),
        "required_source_count": config.mixing.minimum_source_count,
        "highest_single_source_ratio": round(highest_source_ratio, 4),
        "source_seconds": {key: round(value, 3) for key, value in source_seconds.items()},
        "source_clip_counts": dict(source_counts),
        "low_match_segments": low_match_segments,
        "missing_media_segments": missing_media_segments,
        "source_window_violations": source_window_violations,
        "adjacent_same_source": [list(item) for item in adjacent_same_source],
        "audio": asdict(timeline.audio),
        "audio_blockers": audio_blockers,
        "subtitle_review_required": subtitle_review_required,
        "review": review_payload,
        "warnings": warnings,
        "allow_final_export": not (
            blocking_warnings
            or low_match_segments
            or audio_blockers
            or missing_media_segments
            or source_window_violations
        ),
    }
