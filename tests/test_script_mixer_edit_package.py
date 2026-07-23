from __future__ import annotations

import json
import subprocess
from pathlib import Path

from short_drama_controller.script_mixer.config import RuntimeConfig
from short_drama_controller.script_mixer.edit_package import (
    EditPackageExporter,
    calculate_edit_window,
)
from short_drama_controller.script_mixer.models import AudioPlan, Timeline, TimelineSegment
from short_drama_controller.script_mixer.review import save_timeline


def _runner(command, **_kwargs):
    executable = Path(command[0]).name.casefold()
    if "ffprobe" in executable:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"format": {"duration": "95.0"}}),
            stderr="",
        )
    output = Path(command[-1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"generated")
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _project(tmp_path: Path) -> tuple[RuntimeConfig, Path]:
    config = RuntimeConfig()
    config.output_root = str(tmp_path / "outputs")
    config.edit_package.create_jianying_draft = False
    config.edit_package.candidate_export_count = 1
    project = Path(config.output_root) / "edit_project"
    project.mkdir(parents=True)
    source = tmp_path / "media" / "source.mp4"
    candidate_source = tmp_path / "media" / "candidate.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"source")
    candidate_source.write_bytes(b"candidate")
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"voice")
    subtitle_dir = project / "subtitles"
    subtitle_dir.mkdir()
    srt = subtitle_dir / "captions.srt"
    ass = subtitle_dir / "captions.ass"
    srt.write_text("1\n00:00:00,000 --> 00:00:03,000\n测试字幕\n", encoding="utf-8")
    ass.write_text("ass", encoding="utf-8")
    timeline = Timeline(
        project_id="edit_project",
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
                source_path=str(source),
                source_start=5.0,
                source_end=8.0,
                match_score=0.9,
                speed=1.0,
                audio_enabled=True,
                clip_id="C1",
            )
        ],
        audio=AudioPlan(
            mode="mixed",
            narration_path=str(voice),
            narration_duration=3.0,
            subtitle_srt_path=str(srt),
            subtitle_ass_path=str(ass),
        ),
    )
    save_timeline(project, timeline)
    candidates = {
        "U001": [
            {
                "clip": {
                    "clip_id": "C1",
                    "source_id": "SRC1",
                    "source_path": str(source),
                    "source_start": 5.0,
                    "source_end": 8.0,
                    "duration": 3.0,
                    "description": "current",
                    "tags": [],
                    "emotions": [],
                    "usable": True,
                    "has_audio": True,
                },
                "score": 0.9,
                "reasons": ["current"],
            },
            {
                "clip": {
                    "clip_id": "C2",
                    "source_id": "SRC2",
                    "source_path": str(candidate_source),
                    "source_start": 38.0,
                    "source_end": 40.0,
                    "duration": 2.0,
                    "description": "备用画面",
                    "tags": ["备用"],
                    "emotions": [],
                    "usable": True,
                    "has_audio": False,
                },
                "score": 0.8,
                "reasons": ["alternative"],
            },
        ]
    }
    (project / "candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False),
        encoding="utf-8",
    )
    return config, project


def test_calculate_edit_window_keeps_handles_and_cap() -> None:
    normal = calculate_edit_window(5.0, 8.0, 95.0, 40.0, 1.0, 1.0)
    assert normal["media_start"] == 4.0
    assert normal["media_end"] == 9.0
    assert normal["selected_in"] == 1.0
    assert normal["handle_before"] == 1.0
    assert normal["handle_after"] == 1.0
    capped = calculate_edit_window(38.0, 40.0, 95.0, 40.0, 1.0, 1.0)
    assert capped["media_start"] == 37.0
    assert capped["media_end"] == 40.0
    assert capped["handle_after"] == 0.0


def test_export_edit_package_and_reuse_cache(tmp_path: Path) -> None:
    config, project = _project(tmp_path)
    exporter = EditPackageExporter(
        config,
        ffmpeg_path="ffmpeg",
        ffprobe_path="ffprobe",
        runner=_runner,
    )
    first = exporter.export(project, create_draft=False)
    package = Path(first["package_dir"])
    segment = first["segments"][0]
    assert Path(segment["proxy_video_path"]).is_file()
    assert Path(segment["source_audio_path"]).is_file()
    assert segment["media_start"] == 4.0
    assert segment["media_end"] == 9.0
    assert segment["selected_in"] == 1.0
    assert segment["selected_duration"] == 3.0
    assert Path(first["narration"]["output_path"]).is_file()
    assert Path(first["subtitles"]["srt"]).is_file()
    assert (package / "metadata" / "timeline.csv").is_file()
    assert (package / "剪映导入与修改说明.txt").is_file()
    candidate = first["candidates"]["S001"][0]
    assert Path(candidate["proxy_video_path"]).is_file()
    assert candidate["media_end"] == 40.0
    commands = json.loads(
        (package / "metadata" / "ffmpeg_commands.json").read_text(encoding="utf-8")
    )
    video_command = commands[0]
    assert "-fps_mode" in video_command
    assert "cfr" in video_command
    assert "fps=30" in video_command[video_command.index("-vf") + 1]

    second = exporter.export(project, create_draft=False)
    assert second["reused_asset_count"] >= 3
    assert second["segments"][0]["reused"] is True
    assert second["candidates"]["S001"][0]["reused"] is True
    assert second["narration"]["reused"] is True
