from __future__ import annotations

import json
from pathlib import Path

from short_drama_controller.script_mixer.cli import main
from short_drama_controller.script_mixer.config import RuntimeConfig
from short_drama_controller.script_mixer.models import Timeline, TimelineSegment
from short_drama_controller.script_mixer.review import load_timeline, save_timeline


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    config = RuntimeConfig()
    config.database_path = str(tmp_path / "runtime" / "media.db")
    config.output_root = str(tmp_path / "outputs")
    config.mixing.minimum_source_count = 1
    config.mixing.max_single_source_seconds = 30.0
    config.mixing.max_single_source_ratio = 1.0
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config.to_dict(), ensure_ascii=False), encoding="utf-8")

    project = Path(config.output_root) / "cli_review"
    project.mkdir(parents=True)
    source1 = tmp_path / "media" / "source1.mp4"
    source2 = tmp_path / "media" / "source2.mp4"
    source1.parent.mkdir(parents=True)
    source1.write_bytes(b"one")
    source2.write_bytes(b"two")
    timeline = Timeline(
        project_id="cli_review",
        width=1080,
        height=1920,
        fps=30,
        duration=3.0,
        segments=[
            TimelineSegment(
                segment_id="S001",
                unit_id="U001",
                timeline_start=0.0,
                timeline_end=3.0,
                source_id="SRC1",
                source_path=str(source1),
                source_start=0.0,
                source_end=3.0,
                match_score=0.6,
                clip_id="C1",
            )
        ],
    )
    save_timeline(project, timeline)
    candidates = {
        "U001": [
            {
                "clip": {
                    "clip_id": "C1",
                    "source_id": "SRC1",
                    "source_path": str(source1),
                    "source_start": 0.0,
                    "source_end": 3.0,
                    "duration": 3.0,
                    "description": "旧镜头",
                    "tags": ["旧镜头"],
                    "usable": True,
                },
                "score": 0.6,
                "reasons": ["current"],
            },
            {
                "clip": {
                    "clip_id": "C2",
                    "source_id": "SRC2",
                    "source_path": str(source2),
                    "source_start": 0.0,
                    "source_end": 4.0,
                    "duration": 4.0,
                    "description": "手机 创作",
                    "tags": ["手机", "创作"],
                    "usable": True,
                },
                "score": 0.9,
                "reasons": ["keyword"],
            },
        ]
    }
    (project / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False),
        encoding="utf-8",
    )
    return config_path, project


def test_review_lock_unlock_cli(tmp_path: Path, capsys) -> None:
    config_path, project = _setup(tmp_path)
    assert main(["--config", str(config_path), "review-project", "--project", str(project)]) == 0
    capsys.readouterr()
    assert main(
        [
            "--config",
            str(config_path),
            "lock-segment",
            "--project",
            str(project),
            "--segment",
            "S001",
        ]
    ) == 0
    capsys.readouterr()
    assert load_timeline(project).segments[0].locked is True
    assert main(
        [
            "--config",
            str(config_path),
            "unlock-segment",
            "--project",
            str(project),
            "--segment",
            "S001",
        ]
    ) == 0
    capsys.readouterr()
    assert load_timeline(project).segments[0].locked is False


def test_replace_and_rollback_cli(tmp_path: Path, capsys) -> None:
    config_path, project = _setup(tmp_path)
    assert main(
        [
            "--config",
            str(config_path),
            "replace-segment",
            "--project",
            str(project),
            "--segment",
            "S001",
            "--keyword",
            "手机 创作",
            "--reason",
            "CLI replacement",
        ]
    ) == 0
    capsys.readouterr()
    assert load_timeline(project).segments[0].clip_id == "C2"
    assert main(
        [
            "--config",
            str(config_path),
            "rollback-project",
            "--project",
            str(project),
        ]
    ) == 0
    capsys.readouterr()
    assert load_timeline(project).segments[0].clip_id == "C1"
