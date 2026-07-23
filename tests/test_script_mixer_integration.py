from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from short_drama_controller.script_mixer.catalog import MediaCatalog
from short_drama_controller.script_mixer.config import RuntimeConfig
from short_drama_controller.script_mixer.integration import IntegrationChecker
from short_drama_controller.script_mixer.models import (
    DiscoveryReport,
    MediaClip,
    MediaScanSummary,
    MediaSource,
    Timeline,
    TimelineSegment,
    ToolLocation,
)


class FakePipeline:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.catalog = MediaCatalog(config.database_path)
        self.catalog.initialize()
        self.plan_calls = 0
        self.render_calls = 0
        self.violate_window = False

    def doctor(self) -> DiscoveryReport:
        tools = {
            name: ToolLocation(
                name=name,
                executable=name,
                source="test",
                version=f"{name} test version",
            )
            for name in ("ffmpeg", "ffprobe", "ollama", "python", "git", "nvidia_smi", "whisper")
        }
        return DiscoveryReport(
            platform="Test OS",
            generated_at="2026-07-23T00:00:00+00:00",
            tools=tools,
            models={},
        )

    def model_status(self) -> dict:
        return {
            "available": True,
            "selected": {
                "text_model": "text-test",
                "vision_model": "vision-test",
                "embedding_model": "embedding-test",
                "speech_model": "whisper-test.pt",
            },
            "whisper": {"available": True, "selected_model": "whisper-test.pt"},
            "installed_models": [],
            "embedding_cache": {},
            "errors": [],
        }

    def scan_media(self, root, fast=False, force=False, prune_missing=False) -> MediaScanSummary:
        base = Path(root)
        definitions = [
            ("horizontal_audio.mp4", 9.0, 1920, 1080, True),
            ("vertical_silent.mp4", 12.0, 1080, 1920, False),
            ("long_audio.mp4", 95.0, 1920, 1080, True),
        ]
        clips_written = 0
        for index, (name, duration, width, height, has_audio) in enumerate(definitions, start=1):
            path = base / name
            path.write_bytes(name.encode("utf-8"))
            source_id = f"SRC{index:03d}"
            indexed = min(duration, self.config.media_scan.maximum_source_process_seconds)
            source = MediaSource(
                source_id=source_id,
                source_path=str(path.resolve()),
                filename=name,
                extension=".mp4",
                file_size=path.stat().st_size,
                modified_ns=path.stat().st_mtime_ns,
                fingerprint=f"fingerprint-{index}",
                duration=duration,
                width=width,
                height=height,
                fps=30.0,
                has_audio=has_audio,
                indexed_duration=indexed,
                ignored_tail_seconds=max(0.0, duration - indexed),
            )
            source_end = 41.0 if self.violate_window and index == 3 else indexed
            clip = MediaClip(
                clip_id=f"CLP{index:03d}",
                source_id=source_id,
                source_path=source.source_path,
                source_start=0.0,
                source_end=source_end,
                duration=source_end,
                description=name,
                width=width,
                height=height,
                has_audio=has_audio,
            )
            self.catalog.replace_source_clips(source, [clip])
            clips_written += 1
        return MediaScanSummary(
            root=str(base.resolve()),
            discovered_files=3,
            new_files=3,
            sources_written=3,
            clips_written=clips_written,
            capped_files=1,
            indexed_duration_seconds=61.0,
            ignored_tail_seconds=55.0,
        )

    def plan(self, **kwargs):
        self.plan_calls += 1
        project_id = kwargs["project_id"]
        project_dir = Path(self.config.output_root) / project_id
        subtitle_dir = project_dir / "subtitles"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        subtitle = subtitle_dir / "captions.ass"
        subtitle.write_text("subtitle", encoding="utf-8")
        source = self.catalog.list_sources()[0]
        timeline = Timeline(
            project_id=project_id,
            width=1080,
            height=1920,
            fps=30,
            duration=30.0,
            segments=[
                TimelineSegment(
                    segment_id="SEG001",
                    unit_id="U001",
                    timeline_start=0.0,
                    timeline_end=30.0,
                    source_id=source.source_id,
                    source_path=source.source_path,
                    source_start=0.0,
                    source_end=40.0,
                    match_score=0.9,
                    audio_enabled=True,
                )
            ],
        )
        timeline.audio.mode = "source"
        timeline.audio.subtitle_ass_path = str(subtitle)
        return timeline, project_dir

    def render(self, timeline, project_dir, burn_subtitles=False, dry_run=False):
        self.render_calls += 1
        output = Path(project_dir) / "exports" / "final.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"rendered-video")
        return output


def _fake_runner(command, **_kwargs):
    executable = Path(command[0]).name.casefold()
    if executable == "ffmpeg" and "-filters" in command:
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="subtitles scale crop concat loudnorm sidechaincompress",
            stderr="",
        )
    if executable == "ffmpeg" and "-encoders" in command:
        return subprocess.CompletedProcess(command, 0, stdout="libx264 aac", stderr="")
    if executable == "nvidia_smi" or executable == "nvidia-smi":
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="RTX 4060, 555.10, 8192, 1024, 7168\n",
            stderr="",
        )
    if executable == "ffprobe":
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "format": {"duration": "1.5"},
                    "streams": [
                        {"codec_type": "video", "codec_name": "h264", "width": 640, "height": 360},
                        {"codec_type": "audio", "codec_name": "aac"},
                    ],
                }
            ),
            stderr="",
        )
    if executable == "ffmpeg":
        output = Path(command[-1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"synthetic-video")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")


def _config(tmp_path: Path) -> RuntimeConfig:
    config = RuntimeConfig()
    config.database_path = str(tmp_path / "runtime" / "media.db")
    config.output_root = str(tmp_path / "outputs")
    config.discovery_report_path = str(tmp_path / "runtime" / "discovery.json")
    config.integration.report_path = str(tmp_path / "runtime" / "integration_report.json")
    config.integration.work_root = str(tmp_path / "runtime" / "integration")
    config.integration.minimum_free_space_bytes = 1
    config.subtitles.font_name = "Microsoft YaHei"
    return config


def _patch_fonts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "short_drama_controller.script_mixer.integration._discover_fonts",
        lambda configured_name: {
            "configured_font": configured_name,
            "configured_matches": ["C:/Windows/Fonts/msyh.ttc"],
            "cjk_font_matches": ["C:/Windows/Fonts/msyh.ttc"],
            "font_roots": ["C:/Windows/Fonts"],
            "files_scanned": 1,
        },
    )


def test_integration_check_writes_incremental_environment_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fonts(monkeypatch)
    config = _config(tmp_path)
    pipeline = FakePipeline(config)
    report = IntegrationChecker(pipeline, runner=_fake_runner).run()
    assert report.environment_ready is True
    assert report.ready_for_real_trial is False
    assert report.trial_completed is False
    assert report.resume_supported is True
    statuses = {item.check_id: item.status for item in report.checks}
    assert statuses["synthetic_render"] == "pass"
    assert statuses["media_library"] == "skip"
    stored = json.loads(Path(config.integration.report_path).read_text(encoding="utf-8"))
    assert stored["environment_ready"] is True
    assert stored["checks"][-1]["check_id"] == "real_trial"


def test_integration_check_scans_real_fixture_and_runs_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fonts(monkeypatch)
    config = _config(tmp_path)
    pipeline = FakePipeline(config)
    media_root = tmp_path / "media"
    media_root.mkdir()
    script = tmp_path / "script.txt"
    script.write_text("这是用于真实电脑集成试剪的测试文案。", encoding="utf-8")
    report = IntegrationChecker(pipeline, runner=_fake_runner).run(
        media_root=media_root,
        script_path=script,
        run_trial=True,
        transcribe_trial=False,
    )
    assert report.environment_ready is True
    assert report.ready_for_real_trial is True
    assert report.trial_completed is True
    assert pipeline.plan_calls == 1
    assert pipeline.render_calls == 1
    media_check = next(item for item in report.checks if item.check_id == "media_library")
    assert media_check.status == "pass"
    assert media_check.details["categories"]["longer_than_processing_window"] == 1
    trial = next(item for item in report.checks if item.check_id == "real_trial")
    assert trial.details["source_window_verified"] is True
    assert Path(trial.details["output"]).is_file()


def test_integration_check_blocks_clip_after_40_seconds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fonts(monkeypatch)
    config = _config(tmp_path)
    pipeline = FakePipeline(config)
    pipeline.violate_window = True
    media_root = tmp_path / "media"
    media_root.mkdir()
    script = tmp_path / "script.txt"
    script.write_text("边界测试。", encoding="utf-8")
    report = IntegrationChecker(pipeline, runner=_fake_runner).run(
        media_root=media_root,
        script_path=script,
    )
    media_check = next(item for item in report.checks if item.check_id == "media_library")
    assert media_check.status == "fail"
    assert media_check.blocker is True
    assert media_check.details["violations"][0]["source_end"] == 41.0
    assert report.ready_for_real_trial is False
