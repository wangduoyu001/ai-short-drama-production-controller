from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from .models import AudioPlan, Timeline


class RenderUnavailableError(RuntimeError):
    pass


def _channel_layout(channels: int) -> str:
    return "mono" if channels == 1 else "stereo"


def _audio_format_filter(sample_rate: int, channels: int) -> str:
    layout = _channel_layout(channels)
    return (
        f"aresample={sample_rate},"
        f"aformat=sample_fmts=fltp:sample_rates={sample_rate}:channel_layouts={layout}"
    )


def _loudnorm_filter(target_lufs: float, true_peak: float, loudness_range: float) -> str:
    return f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={loudness_range}"


def _resolve_render_audio(
    timeline: Timeline,
    voice_path: str | Path | None,
    audio_mode: str | None,
) -> tuple[str, str]:
    mode = (audio_mode or timeline.audio.mode or "mute").casefold()
    narration = str(voice_path or timeline.audio.narration_path or "")
    if mode == "auto":
        mode = "narration" if narration else "source"
    if mode not in {"narration", "source", "mixed", "mute"}:
        raise ValueError(f"Unsupported render audio mode: {mode}")
    if mode in {"narration", "mixed"} and not narration:
        raise ValueError(f"Audio mode {mode} requires a narration file")
    return mode, narration


def _build_source_audio_filters(timeline: Timeline, filters: list[str]) -> str:
    plan = timeline.audio
    sample_rate = max(8000, int(plan.sample_rate))
    channels = 1 if plan.channels == 1 else 2
    audio_labels: list[str] = []
    for index, segment in enumerate(timeline.segments):
        label = f"sa{index}"
        duration = max(0.001, segment.duration)
        if segment.audio_enabled:
            filters.append(
                f"[{index}:a]"
                f"atrim=start={segment.source_start:.3f}:end={segment.source_end:.3f},"
                f"asetpts=PTS-STARTPTS,"
                f"atempo={max(0.5, min(2.0, segment.speed)):.6f},"
                f"{_audio_format_filter(sample_rate, channels)},"
                f"apad=pad_dur={duration:.3f},atrim=duration={duration:.3f}"
                f"[{label}]"
            )
        else:
            layout = _channel_layout(channels)
            filters.append(
                f"anullsrc=r={sample_rate}:cl={layout},"
                f"atrim=duration={duration:.3f}"
                f"[{label}]"
            )
        audio_labels.append(f"[{label}]")

    filters.append(
        f"{''.join(audio_labels)}concat=n={len(audio_labels)}:v=0:a=1[source_concat]"
    )
    chain = "[source_concat]"
    operations: list[str] = []
    if plan.normalize_source:
        operations.append(
            _loudnorm_filter(plan.source_target_lufs, plan.true_peak, plan.loudness_range)
        )
    operations.append(f"volume={max(0.0, plan.source_volume):.6f}")
    operations.append(f"atrim=duration={timeline.duration:.3f}")
    filters.append(f"{chain}{','.join(operations)}[source_audio]")
    return "source_audio"


def _build_narration_filters(
    timeline: Timeline,
    filters: list[str],
    voice_input_index: int,
) -> str:
    plan = timeline.audio
    sample_rate = max(8000, int(plan.sample_rate))
    channels = 1 if plan.channels == 1 else 2
    operations = [
        f"atrim=start=0:end={timeline.duration:.3f}",
        "asetpts=PTS-STARTPTS",
        _audio_format_filter(sample_rate, channels),
        f"apad=pad_dur={timeline.duration:.3f}",
        f"atrim=duration={timeline.duration:.3f}",
    ]
    if plan.normalize_narration:
        operations.append(
            _loudnorm_filter(plan.narration_target_lufs, plan.true_peak, plan.loudness_range)
        )
    operations.append(f"volume={max(0.0, plan.narration_volume):.6f}")
    filters.append(f"[{voice_input_index}:a]{','.join(operations)}[narration_audio]")
    return "narration_audio"


def _build_final_audio_filters(
    timeline: Timeline,
    filters: list[str],
    mode: str,
    voice_input_index: int | None,
) -> str | None:
    if mode == "mute":
        return None
    source_label: str | None = None
    narration_label: str | None = None
    if mode in {"source", "mixed"}:
        source_label = _build_source_audio_filters(timeline, filters)
    if mode in {"narration", "mixed"}:
        if voice_input_index is None:
            raise ValueError(f"Audio mode {mode} requires a narration input")
        narration_label = _build_narration_filters(timeline, filters, voice_input_index)

    if mode == "source" and source_label:
        filters.append(f"[{source_label}]alimiter=limit=0.95[outa]")
        return "outa"
    if mode == "narration" and narration_label:
        filters.append(f"[{narration_label}]alimiter=limit=0.95[outa]")
        return "outa"
    if mode == "mixed" and source_label and narration_label:
        plan = timeline.audio
        filters.append(f"[{narration_label}]asplit=2[narration_side][narration_mix]")
        filters.append(
            f"[{source_label}][narration_side]"
            f"sidechaincompress=threshold={plan.ducking_threshold}:"
            f"ratio={plan.ducking_ratio}:"
            f"attack={plan.ducking_attack_ms}:"
            f"release={plan.ducking_release_ms}"
            f"[source_ducked]"
        )
        filters.append(
            "[source_ducked][narration_mix]"
            "amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[outa]"
        )
        return "outa"
    raise ValueError(f"Unable to construct audio graph for mode: {mode}")


def build_ffmpeg_command(
    timeline: Timeline,
    ffmpeg_path: str,
    output_path: str | Path,
    voice_path: str | Path | None = None,
    audio_mode: str | None = None,
) -> list[str]:
    if not timeline.segments:
        raise ValueError("Timeline contains no segments")
    output = Path(output_path)
    mode, narration = _resolve_render_audio(timeline, voice_path, audio_mode)
    command = [ffmpeg_path, "-hide_banner", "-y"]
    for segment in timeline.segments:
        command.extend(["-i", segment.source_path])

    voice_input_index: int | None = None
    if narration:
        voice_input_index = len(timeline.segments)
        command.extend(["-i", narration])

    filters: list[str] = []
    video_labels: list[str] = []
    for index, segment in enumerate(timeline.segments):
        label = f"v{index}"
        source_duration = max(0.001, segment.source_end - segment.source_start)
        target_duration = max(0.001, segment.timeline_end - segment.timeline_start)
        speed = source_duration / target_duration
        filters.append(
            f"[{index}:v]"
            f"trim=start={segment.source_start:.3f}:end={segment.source_end:.3f},"
            f"setpts=(PTS-STARTPTS)/{speed:.6f},"
            f"scale={timeline.width}:{timeline.height}:force_original_aspect_ratio=increase,"
            f"crop={timeline.width}:{timeline.height},"
            f"fps={timeline.fps},setsar=1,format=yuv420p"
            f"[{label}]"
        )
        video_labels.append(f"[{label}]")
    filters.append(
        f"{''.join(video_labels)}concat=n={len(video_labels)}:v=1:a=0[outv]"
    )
    audio_label = _build_final_audio_filters(timeline, filters, mode, voice_input_index)

    command.extend(["-filter_complex", ";".join(filters), "-map", "[outv]"])
    if audio_label:
        command.extend(["-map", f"[{audio_label}]", "-c:a", "aac", "-b:a", "192k"])
    else:
        command.extend(["-an"])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-t",
            f"{timeline.duration:.3f}",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def save_render_plan(
    command: list[str],
    path: str | Path,
    audio_plan: AudioPlan | None = None,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {"command": command}
    if audio_plan is not None:
        payload["audio"] = asdict(audio_plan)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def render_timeline(
    timeline: Timeline,
    ffmpeg_path: str | None,
    output_path: str | Path,
    voice_path: str | Path | None = None,
    audio_mode: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    if not ffmpeg_path:
        raise RenderUnavailableError("ffmpeg was not discovered and no override was configured")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(
        timeline,
        ffmpeg_path,
        output,
        voice_path=voice_path,
        audio_mode=audio_mode,
    )
    if dry_run:
        return command
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {completed.returncode}")
    return command
