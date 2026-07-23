from __future__ import annotations

import json
from pathlib import Path

from short_drama_controller.script_mixer.config import RuntimeConfig
from short_drama_controller.script_mixer.models import ScriptUnit, Timeline, TimelineSegment, VisualIntent
from short_drama_controller.script_mixer.replan import ProjectReplanner
from short_drama_controller.script_mixer.review import TimelineReviewService, load_timeline, save_timeline


def _clip(clip_id: str, source_id: str, path: Path, score_text: str) -> dict:
    return {
        "clip_id": clip_id,
        "source_id": source_id,
        "source_path": str(path),
        "source_start": 0.0,
        "source_end": 5.0,
        "duration": 5.0,
        "description": score_text,
        "tags": [score_text],
        "emotions": [],
        "shot_type": "中景",
        "camera_motion": "固定",
        "width": 1080,
        "height": 1920,
        "quality_score": 0.9,
        "has_watermark": False,
        "usable": True,
        "thumbnail_path": "",
        "has_audio": True,
    }


def _setup(tmp_path: Path) -> tuple[RuntimeConfig, Path]:
    config = RuntimeConfig()
    config.output_root = str(tmp_path / "outputs")
    config.mixing.minimum_source_count = 1
    config.mixing.max_single_source_seconds = 30.0
    config.mixing.max_single_source_ratio = 1.0
    config.mixing.source_reuse_gap = 0
    project = Path(config.output_root) / "replan_project"
    project.mkdir(parents=True)

    paths: dict[str, Path] = {}
    for name in ("A", "B", "C", "D", "E"):
        path = tmp_path / "media" / f"{name}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode("utf-8"))
        paths[name] = path

    units = [
        ScriptUnit("U001", "第一句", 0.0, 3.0, 3.0, "hook", 0.9),
        ScriptUnit("U002", "第二句", 3.0, 6.0, 3.0, "body", 0.6),
        ScriptUnit("U003", "第三句", 6.0, 9.0, 3.0, "conclusion", 0.9),
    ]
    intents = [
        VisualIntent(item.unit_id, [item.text], [], [item.text], [], [], ["中景"])
        for item in units
    ]
    (project / "script_units.json").write_text(
        json.dumps([item.__dict__ if hasattr(item, "__dict__") else {
            "unit_id": item.unit_id,
            "text": item.text,
            "start": item.start,
            "end": item.end,
            "duration": item.duration,
            "role": item.role,
            "importance": item.importance,
        } for item in units], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (project / "visual_intents.json").write_text(
        json.dumps([
            {
                "unit_id": item.unit_id,
                "literal_queries": item.literal_queries,
                "metaphor_queries": item.metaphor_queries,
                "positive_tags": item.positive_tags,
                "negative_tags": item.negative_tags,
                "emotion": item.emotion,
                "preferred_shots": item.preferred_shots,
            }
            for item in intents
        ], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    candidates = {
        "U001": [
            {"clip": _clip("C1", "SRC_A", paths["A"], "旧开场"), "score": 0.4, "reasons": ["old"]},
            {"clip": _clip("C4", "SRC_D", paths["D"], "新开场"), "score": 0.95, "reasons": ["better"]},
        ],
        "U002": [
            {"clip": _clip("C2", "SRC_B", paths["B"], "锁定镜头"), "score": 0.3, "reasons": ["locked"]},
            {"clip": _clip("C5", "SRC_E", paths["E"], "更高分镜头"), "score": 0.99, "reasons": ["better"]},
        ],
        "U003": [
            {"clip": _clip("C3", "SRC_C", paths["C"], "结尾"), "score": 0.8, "reasons": ["end"]}
        ],
    }
    (project / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    timeline = Timeline(
        project_id="replan_project",
        width=1080,
        height=1920,
        fps=30,
        duration=9.0,
        segments=[
            TimelineSegment("S001", "U001", 0.0, 3.0, "SRC_A", str(paths["A"]), 0.0, 3.0, 0.4, clip_id="C1"),
            TimelineSegment("S002", "U002", 3.0, 6.0, "SRC_B", str(paths["B"]), 0.0, 3.0, 0.3, clip_id="C2"),
            TimelineSegment("S003", "U003", 6.0, 9.0, "SRC_C", str(paths["C"]), 0.0, 3.0, 0.8, clip_id="C3"),
        ],
    )
    save_timeline(project, timeline)
    return config, project


def test_replan_changes_unlocked_and_preserves_locked(tmp_path: Path) -> None:
    config, project = _setup(tmp_path)
    review = TimelineReviewService(config)
    review.lock(project, "S002")
    result = ProjectReplanner(config).replan(project)
    timeline = load_timeline(project)
    assert timeline.segments[0].clip_id == "C4"
    assert timeline.segments[1].clip_id == "C2"
    assert timeline.segments[1].locked is True
    assert timeline.segments[1].review_status == "approved"
    assert timeline.segments[2].clip_id == "C3"
    assert "S001" in result["replan"]["changed_segments"]
    assert result["replan"]["locked_segments_preserved"] == ["S002"]
    revision_log = json.loads((project / "revision_log.json").read_text(encoding="utf-8"))
    assert revision_log["revisions"][-1]["action"] == "replan"
