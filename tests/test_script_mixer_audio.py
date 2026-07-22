from __future__ import annotations

from pathlib import Path

import pytest

from short_drama_controller.script_mixer.audio import (
    build_audio_plan,
    parse_audio_probe_payload,
    resolve_audio_mode,
)
from short_drama_controller.script_mixer.config import AudioConfig, RuntimeConfig
from short_drama_controller.script_mixer.models import AudioPlan, MediaClip, Timeline, TimelineSegment
from short_drama_controller.script_mixer.pipeline import ScriptMixerPipeline
from short_drama_controller.script_mixer.render import build_ffmpeg_command


def _timeline(mode: str = "mute", narration_path: str = "") -> Timeline:
    segments = [
        TimelineSegment(
            segment_id="S001",
            unit_id="U001",
            timeline_start=0.0,
            timeline_end=2.0,
            source_id="SRC001",
            source_path="D:/media/with_audio.mp4",
            source_start=1.0,
            source_end=3.0,
            match_score=0.9,
            speed=1.0,
            audio_enabled=True,
        ),
        TimelineSegment(
            segment_id="S002",
            unit_id="U002",
            timeline_start=2.0,
            timeline_end=4.0,
            source_id="SRC002",
            source_path="D:/media/silent.mp4",
            source_start=4.0,
            source_end=5.0,
            match_score=0.8,
            speed=0.5,
            audio_enabled=False,
        ),
    ]
    return Timeline(
        project_id="audio_test",
        width=1080,
        height=1920,
        fps=30,
        duration=4.0,
        segments=segments,
        audio=AudioPlan(
            mode=mode,
            narration_path=narration_path,
            narration_duration=4.0 if narration_path else 0.0,
            source_audio_segments=1,
            source_audio_coverage=0.5,
        ),
    )


def test_audio_mode_resolution() -> None:
    assert resolve_audio_mode("auto", "voice.wav") == "narration"
    assert resolve_audio_mode("auto", None) == "source"
    assert resolve_audio_mode("source", "voice.wav") == "source"
    assert resolve_audio_mode("mute", None) == "mute"
    with pytest.raises(ValueError):
        resolve_audio_mode("mixed", None)
    with pytest.raises(ValueError):
        resolve_audio_mode("impossible", None)


def test_parse_audio_probe_payload() -> None:
    result = parse_audio_probe_payload(
        {
            "format": {"duration": "12.345"},
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": "48000",
                    "channels": 2,
                }
            ],
        },
        "voice.wav",
    )
    assert result.has_audio is True
    assert result.duration == 12.345
    assert result.codec == "aac"
    assert result.sample_rate == 48000
    assert result.channels == 2


def test_audio_plan_reports_source_coverage() -> None:
    timeline = _timeline("source")
    plan = build_audio_plan(
        segments=timeline.segments,
        duration=timeline.duration,
        config=AudioConfig(),
        requested_mode="source",
    )
    assert plan.mode == "source"
    assert plan.source_audio_segments == 1
    assert plan.source_audio_coverage == 0.5


def test_source_audio_ffmpeg_graph_fills_silence() -> None:
    command = build_ffmpeg_command(_timeline("source"), "ffmpeg", "output.mp4")
    graph = command[command.index("-filter_complex") + 1]
    assert "[0:a]atrim=start=1.000:end=3.000" in graph
    assert "atempo=1.000000" in graph
    assert "anullsrc=r=48000:cl=stereo" in graph
    assert "concat=n=2:v=0:a=1[source_concat]" in graph
    assert "[outa]" in command


def test_narration_audio_ffmpeg_graph() -> None:
    command = build_ffmpeg_command(
        _timeline("narration", "voice.wav"),
        "ffmpeg",
        "output.mp4",
    )
    graph = command[command.index("-filter_complex") + 1]
    assert command.count("-i") == 3
    assert "[2:a]atrim=start=0:end=4.000" in graph
    assert "loudnorm=I=-16.0" in graph
    assert "sidechaincompress" not in graph


def test_mixed_audio_ffmpeg_graph_ducks_source() -> None:
    timeline = _timeline("mixed", "voice.wav")
    timeline.audio.source_volume = 0.22
    command = build_ffmpeg_command(timeline, "ffmpeg", "output.mp4")
    graph = command[command.index("-filter_complex") + 1]
    assert "sidechaincompress=" in graph
    assert "asplit=2" in graph
    assert "amix=inputs=2" in graph
    assert "volume=0.220000" in graph


def test_mute_audio_ffmpeg_graph() -> None:
    command = build_ffmpeg_command(_timeline("mute"), "ffmpeg", "output.mp4")
    assert "-an" in command
    assert "-c:a" not in command


def test_real_narration_duration_drives_timeline(tmp_path: Path) -> None:
    config = RuntimeConfig()
    config.database_path = str(tmp_path / "media.db")
    config.output_root = str(tmp_path / "outputs")
    config.local_models.auto_select_ollama_models = False
    config.mixing.minimum_source_count = 1
    config.mixing.max_single_source_ratio = 1.0
    config.mixing.max_single_source_seconds = 30.0
    config.mixing.source_reuse_gap = 0
    pipeline = ScriptMixerPipeline(config=config)
    for index in range(1, 5):
        pipeline.catalog.upsert_clip(
            MediaClip(
                clip_id=f"C{index:03d}",
                source_id=f"SRC{index:03d}",
                source_path=f"D:/media/{index}.mp4",
                source_start=0.0,
                source_end=10.0,
                duration=10.0,
                description="人物在办公室使用电脑工作",
                tags=["办公室", "电脑", "工作"],
                quality_score=0.9,
                has_audio=True,
            )
        )
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"placeholder")
    timeline, _project = pipeline.plan(
        script_text="很多人每天都在努力。但是低效率的重复并不会带来增长。真正需要的是一套可复用的系统。",
        target_duration=30.0,
        narration_path=voice,
        narration_duration=7.5,
        audio_mode="narration",
        project_id="voice_duration_test",
    )
    assert timeline.duration == 7.5
    assert timeline.audio.mode == "narration"
    assert timeline.audio.narration_duration == 7.5
    assert any("overridden by narration duration" in item for item in timeline.audio.warnings)
