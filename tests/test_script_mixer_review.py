from __future__ import annotations

import json
from pathlib import Path

import pytest

from short_drama_controller.script_mixer.config import RuntimeConfig
from short_drama_controller.script_mixer.models import AudioPlan, Timeline, TimelineSegment
from short_drama_controller.script_mixer.review import (
    SegmentLockedError,
    TimelineReviewService,
    load_timeline,
    save_timeline,
)


def _clip_payload(
    clip_id: str,
    source_id: str,
    source_path: Path,
    start: float,
    end: float,
    description: str,
    has_audio: bool = True,
    shot_type: str = "中景",
) -> dict:
    return {
        "clip_id": clip_id,
        "source_id": source_id,
        "source_path": str(source_path),
        "source_start": start,
        "source_end": end,
        "duration": end - start,
        "description": description,
        "tags": description.split(),
        "emotions": ["专注"],
        "shot_type": shot_type,
        "camera_motion": "固定",
        "width": 1080,
        "height": 1920,
        "quality_score": 0.9,
        "has_watermark": False,
        "usable": True,
        "thumbnail_path": "",
        "has_audio": has_audio,
    }


def _project(tmp_path: Path) -> tuple[RuntimeConfig, Path]:
    config = RuntimeConfig()
    config.output_root = str(tmp_path / "outputs")
    config.mixing.minimum_source_count = 1
    config.mixing.max_single_source_seconds = 30.0
    config.mixing.max_single_source_ratio = 1.0
    project = Path(config.output_root) / "review_project"
    project.mkdir(parents=True)

    source_paths = {}
    for index in range(1, 6):
        path = tmp_path / "media" / f"source_{index}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"video-{index}".encode("utf-8"))
        source_paths[index] = path

    timeline = Timeline(
        project_id="review_project",
        width=1080,
        height=1920,
        fps=30,
        duration=9.0,
        segments=[
            TimelineSegment(
                segment_id="S001",
                unit_id="U001",
                timeline_start=0.0,
                timeline_end=3.0,
                source_id="SRC1",
                source_path=str(source_paths[1]),
                source_start=0.0,
                source_end=3.0,
                match_score=0.9,
                clip_id="C1",
                audio_enabled=True,
            ),
            TimelineSegment(
                segment_id="S002",
                unit_id="U002",
                timeline_start=3.0,
                timeline_end=6.0,
                source_id="SRC2",
                source_path=str(source_paths[2]),
                source_start=0.0,
                source_end=3.0,
                match_score=0.5,
                clip_id="C2",
                audio_enabled=True,
            ),
            TimelineSegment(
                segment_id="S003",
                unit_id="U003",
                timeline_start=6.0,
                timeline_end=9.0,
                source_id="SRC3",
                source_path=str(source_paths[3]),
                source_start=0.0,
                source_end=3.0,
                match_score=0.9,
                clip_id="C3",
                audio_enabled=True,
            ),
        ],
        audio=AudioPlan(mode="mute"),
    )
    save_timeline(project, timeline)
    candidates = {
        "U001": [
            {
                "clip": _clip_payload("C1", "SRC1", source_paths[1], 0.0, 5.0, "开场 办公室"),
                "score": 0.9,
                "reasons": ["current"],
            }
        ],
        "U002": [
            {
                "clip": _clip_payload("C2", "SRC2", source_paths[2], 0.0, 5.0, "旧镜头 办公室"),
                "score": 0.5,
                "reasons": ["current"],
            },
            {
                "clip": _clip_payload("C4", "SRC4", source_paths[4], 1.0, 6.0, "手机 创作 工作"),
                "score": 0.93,
                "reasons": ["关键词匹配", "来源多样性"],
            },
            {
                "clip": _clip_payload("C5", "SRC5", source_paths[5], 39.0, 45.0, "手机 创作 工作"),
                "score": 0.95,
                "reasons": ["超过40秒"],
            },
        ],
        "U003": [
            {
                "clip": _clip_payload("C3", "SRC3", source_paths[3], 0.0, 5.0, "结尾 城市"),
                "score": 0.9,
                "reasons": ["current"],
            }
        ],
    }
    (project / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config, project


def test_review_lock_and_unlock_are_persistent(tmp_path: Path) -> None:
    config, project = _project(tmp_path)
    service = TimelineReviewService(config)
    locked = service.lock(project, "S002")
    timeline = load_timeline(project)
    assert timeline.segments[1].locked is True
    assert timeline.segments[1].review_status == "approved"
    assert locked["review"]["locked_segment_count"] == 1
    unlocked = service.unlock(project, "S002")
    timeline = load_timeline(project)
    assert timeline.segments[1].locked is False
    assert timeline.segments[1].review_status == "unreviewed"
    assert unlocked["review"]["locked_segment_count"] == 0
    revision_log = json.loads((project / "revision_log.json").read_text(encoding="utf-8"))
    assert [item["action"] for item in revision_log["revisions"]] == ["lock", "unlock"]


def test_locked_segment_cannot_be_replaced(tmp_path: Path) -> None:
    config, project = _project(tmp_path)
    service = TimelineReviewService(config)
    service.lock(project, "S002")
    with pytest.raises(SegmentLockedError):
        service.replace(project, "S002", keyword="手机")


def test_replace_preserves_timeline_and_updates_report(tmp_path: Path) -> None:
    config, project = _project(tmp_path)
    service = TimelineReviewService(config)
    result = service.replace(
        project,
        "S002",
        keyword="手机 创作",
        reason="旧画面与文案不匹配",
    )
    timeline = load_timeline(project)
    segment = timeline.segments[1]
    assert segment.timeline_start == 3.0
    assert segment.timeline_end == 6.0
    assert segment.duration == 3.0
    assert segment.clip_id == "C4"
    assert segment.source_id == "SRC4"
    assert segment.source_start == 1.0
    assert segment.source_end == 4.0
    assert segment.match_score == 0.93
    assert segment.review_status == "replaced"
    assert segment.replacement_reason == "旧画面与文案不匹配"
    assert segment.candidate_rank == 2
    assert result["replacement"]["clip_id"] == "C4"
    report = json.loads((project / "report.json").read_text(encoding="utf-8"))
    assert report["review"]["replaced_segment_count"] == 1
    assert report["source_window_violations"] == []
    assert (project / "review.json").is_file()


def test_rollback_restores_previous_timeline(tmp_path: Path) -> None:
    config, project = _project(tmp_path)
    service = TimelineReviewService(config)
    service.replace(project, "S002", keyword="手机 创作", reason="replace")
    assert load_timeline(project).segments[1].clip_id == "C4"
    result = service.rollback(project)
    restored = load_timeline(project)
    assert restored.segments[1].clip_id == "C2"
    assert restored.segments[1].source_id == "SRC2"
    assert result["rolled_back_revision"]["action"] == "replace"
    rollback_log = json.loads((project / "rollback_log.json").read_text(encoding="utf-8"))
    assert rollback_log["rollbacks"][-1]["revision"]["segment_id"] == "S002"
