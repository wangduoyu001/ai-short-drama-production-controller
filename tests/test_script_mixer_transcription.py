from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from short_drama_controller.script_mixer.config import RuntimeConfig, SubtitleConfig, TranscriptionConfig
from short_drama_controller.script_mixer.models import MediaClip, ModelLocation
from short_drama_controller.script_mixer.pipeline import ScriptMixerPipeline
from short_drama_controller.script_mixer.render import build_ffmpeg_command
from short_drama_controller.script_mixer.subtitles import build_subtitle_cues, write_subtitles
from short_drama_controller.script_mixer.transcription import (
    align_script_to_transcription,
    build_whisper_command,
    parse_whisper_payload,
    resolve_whisper_model,
    run_whisper_cli,
)


def _payload() -> dict:
    return {
        "text": "第一句 第二句",
        "language": "zh",
        "segments": [
            {
                "id": 0,
                "start": 0.5,
                "end": 1.5,
                "text": "第一句",
                "words": [
                    {"word": "第一句", "start": 0.5, "end": 1.5, "probability": 0.98}
                ],
            },
            {
                "id": 1,
                "start": 3.0,
                "end": 4.0,
                "text": "第二句",
                "words": [
                    {"word": "第二句", "start": 3.0, "end": 4.0, "probability": 0.97}
                ],
            },
        ],
    }


def test_parse_and_align_whisper_timestamps() -> None:
    result = parse_whisper_payload(
        _payload(),
        audio_path="voice.wav",
        model="medium.pt",
        duration_override=5.0,
    )
    alignment = align_script_to_transcription("第一句。第二句。", result)
    assert alignment.timing_source == "whisper_alignment"
    assert alignment.coverage == 1.0
    assert len(alignment.units) == 2
    assert alignment.units[0].start == 0.0
    assert 2.0 <= alignment.units[0].end <= 2.5
    assert alignment.units[1].start == alignment.units[0].end
    assert alignment.units[-1].end == 5.0
    assert alignment.tokens
    assert "".join(token.text for token in alignment.tokens) == "第一句。第二句。"
    assert alignment.tokens[0].start == 0.5
    assert alignment.tokens[-1].end == 4.0


def test_low_alignment_coverage_falls_back() -> None:
    result = parse_whisper_payload(
        {
            "text": "完全无关",
            "language": "zh",
            "segments": [{"id": 0, "start": 0.0, "end": 3.0, "text": "完全无关"}],
        },
        audio_path="voice.wav",
        model="small.pt",
        duration_override=3.0,
    )
    alignment = align_script_to_transcription(
        "今天讲的是本地混剪系统。",
        result,
        minimum_coverage=0.8,
    )
    assert alignment.timing_source == "proportional_fallback"
    assert alignment.coverage < 0.8
    assert alignment.units[-1].end == 3.0
    assert alignment.tokens == []
    assert alignment.warnings


def test_resolve_whisper_model_prefers_local_turbo(tmp_path: Path) -> None:
    model_dir = tmp_path / "whisper"
    model_dir.mkdir()
    (model_dir / "small.pt").write_bytes(b"small")
    turbo = model_dir / "turbo.pt"
    turbo.write_bytes(b"turbo")
    selected = resolve_whisper_model(
        "",
        [ModelLocation(name="whisper", path=str(model_dir), model_type="whisper_cache")],
        allow_download=False,
    )
    assert selected == str(turbo.resolve())
    assert resolve_whisper_model("medium", [], allow_download=False) is None
    assert resolve_whisper_model("medium", [], allow_download=True) == "medium"


def test_whisper_command_uses_json_and_word_timestamps(tmp_path: Path) -> None:
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"audio")
    output = tmp_path / "out"
    command = build_whisper_command(
        whisper_path="whisper",
        audio_path=audio,
        model="D:/models/medium.pt",
        output_dir=output,
        config=TranscriptionConfig(language="Chinese", word_timestamps=True, fp16=False),
        initial_prompt="这是原始文案",
    )
    joined = " ".join(command)
    assert "--output_format json" in joined
    assert "--word_timestamps True" in joined
    assert "--fp16 False" in joined
    assert "--initial_prompt 这是原始文案" in joined


def test_run_whisper_cli_reads_generated_json(tmp_path: Path) -> None:
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"audio")
    model = tmp_path / "small.pt"
    model.write_bytes(b"model")

    def runner(command, **_kwargs):
        output_dir = Path(command[command.index("--output_dir") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "voice.json").write_text(
            json.dumps(_payload(), ensure_ascii=False),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = run_whisper_cli(
        whisper_path="whisper",
        audio_path=audio,
        model=str(model),
        output_dir=tmp_path / "out",
        config=TranscriptionConfig(),
        duration_override=5.0,
        runner=runner,
    )
    assert result.duration == 5.0
    assert result.language == "zh"
    assert len(result.segments) == 2
    assert result.command


def test_subtitle_files_use_script_text(tmp_path: Path) -> None:
    result = parse_whisper_payload(
        _payload(),
        audio_path="voice.wav",
        model="medium.pt",
        duration_override=5.0,
    )
    alignment = align_script_to_transcription("第一句。第二句。", result)
    config = SubtitleConfig(max_chars_per_line=4, max_lines=2)
    cues = build_subtitle_cues(alignment.units, config)
    assert cues[0].text == "第一句。"
    paths = write_subtitles(
        alignment.units,
        project_dir=tmp_path,
        config=config,
        width=1080,
        height=1920,
        aligned_tokens=alignment.tokens,
    )
    srt = Path(paths["srt"]).read_text(encoding="utf-8-sig")
    ass = Path(paths["ass"]).read_text(encoding="utf-8-sig")
    karaoke = Path(paths["karaoke_ass"]).read_text(encoding="utf-8-sig")
    karaoke_dialogue = "".join(
        line.rsplit(",", 1)[-1]
        for line in karaoke.splitlines()
        if line.startswith("Dialogue:")
    )
    karaoke_plain = re.sub(r"\{\\k\d+\}", "", karaoke_dialogue)
    assert "00:00:00,000" in srt
    assert "第一句。" in srt
    assert "PlayResX: 1080" in ass
    assert "Dialogue:" in ass
    assert r"{\k" in karaoke
    assert "Dialogue: 0,0:00:00.50" in karaoke
    assert "0:00:04.00" in karaoke
    assert karaoke_plain == "第一句。第二句。"


def test_pipeline_uses_existing_whisper_json_and_creates_subtitles(tmp_path: Path) -> None:
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
                source_end=8.0,
                duration=8.0,
                description="人物在办公室工作",
                tags=["办公室", "工作"],
                quality_score=0.9,
                has_audio=True,
            )
        )
    voice = tmp_path / "voice.wav"
    voice.write_bytes(b"audio")
    transcript = tmp_path / "voice.json"
    transcript.write_text(json.dumps(_payload(), ensure_ascii=False), encoding="utf-8")
    timeline, project_dir = pipeline.plan(
        script_text="第一句。第二句。",
        narration_path=voice,
        narration_duration=5.0,
        audio_mode="narration",
        transcript_json_path=transcript,
        project_id="whisper_json_test",
    )
    assert timeline.duration == 5.0
    assert timeline.audio.timing_source == "whisper_alignment"
    assert timeline.audio.alignment_coverage == 1.0
    assert Path(timeline.audio.transcript_path).is_file()
    assert Path(timeline.audio.subtitle_srt_path).is_file()
    assert Path(timeline.audio.subtitle_ass_path).is_file()
    assert Path(timeline.audio.subtitle_karaoke_ass_path).is_file()
    assert (project_dir / "alignment.json").is_file()
    alignment_payload = json.loads((project_dir / "alignment.json").read_text(encoding="utf-8"))
    assert "".join(token["text"] for token in alignment_payload["tokens"]) == "第一句。第二句。"


def test_ffmpeg_can_burn_generated_subtitle(tmp_path: Path) -> None:
    config = RuntimeConfig()
    config.database_path = str(tmp_path / "media.db")
    config.output_root = str(tmp_path / "outputs")
    config.local_models.auto_select_ollama_models = False
    config.mixing.minimum_source_count = 1
    config.mixing.max_single_source_ratio = 1.0
    config.mixing.max_single_source_seconds = 30.0
    config.mixing.source_reuse_gap = 0
    pipeline = ScriptMixerPipeline(config=config)
    for index in range(1, 3):
        pipeline.catalog.upsert_clip(
            MediaClip(
                clip_id=f"C{index:03d}",
                source_id=f"SRC{index:03d}",
                source_path=f"D:/media/{index}.mp4",
                source_start=0.0,
                source_end=5.0,
                duration=5.0,
                description="第一句 第二句",
                tags=["第一句", "第二句"],
                quality_score=0.9,
            )
        )
    timeline, project_dir = pipeline.plan(
        script_text="第一句。第二句。",
        target_duration=4.0,
        audio_mode="mute",
        project_id="subtitle_burn_test",
    )
    command = build_ffmpeg_command(
        timeline,
        "ffmpeg",
        "output.mp4",
        subtitle_path=project_dir / "subtitles" / "captions.ass",
    )
    graph = command[command.index("-filter_complex") + 1]
    assert "subtitles=filename=" in graph
    assert "[outv_base]" in graph
