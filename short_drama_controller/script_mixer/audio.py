from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .config import AudioConfig
from .models import AudioPlan, TimelineSegment


VALID_AUDIO_MODES = {"auto", "narration", "source", "mixed", "mute"}


class AudioProbeError(RuntimeError):
    pass


@dataclass(slots=True)
class AudioProbe:
    path: str
    duration: float
    has_audio: bool
    codec: str = ""
    sample_rate: int = 0
    channels: int = 0


def resolve_audio_mode(requested: str, narration_path: str | Path | None) -> str:
    mode = (requested or "auto").strip().casefold()
    if mode not in VALID_AUDIO_MODES:
        raise ValueError(
            f"Unsupported audio mode: {requested}. Expected one of: "
            + ", ".join(sorted(VALID_AUDIO_MODES))
        )
    has_narration = bool(narration_path)
    if mode == "auto":
        return "narration" if has_narration else "source"
    if mode in {"narration", "mixed"} and not has_narration:
        raise ValueError(f"Audio mode {mode} requires a narration file")
    return mode


def _positive_float(value: object) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if parsed > 0 else 0.0


def parse_audio_probe_payload(payload: dict, path: str | Path) -> AudioProbe:
    streams = payload.get("streams") or []
    audio_streams = [
        item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"
    ]
    format_data = payload.get("format") or {}
    duration = _positive_float(format_data.get("duration"))
    if duration <= 0:
        duration = max((_positive_float(item.get("duration")) for item in streams if isinstance(item, dict)), default=0.0)
    first_audio = audio_streams[0] if audio_streams else {}
    return AudioProbe(
        path=str(Path(path).expanduser().resolve()),
        duration=round(duration, 6),
        has_audio=bool(audio_streams),
        codec=str(first_audio.get("codec_name") or ""),
        sample_rate=int(_positive_float(first_audio.get("sample_rate"))),
        channels=int(_positive_float(first_audio.get("channels"))),
    )


def probe_audio(path: str | Path, ffprobe_path: str | None) -> AudioProbe:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Audio file not found: {source}")
    if not ffprobe_path:
        raise AudioProbeError("ffprobe is required to read the narration duration")
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,duration,sample_rate,channels",
        "-of",
        "json",
        str(source),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AudioProbeError(f"Unable to run ffprobe for narration: {exc}") from exc
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout).strip()
        raise AudioProbeError(f"ffprobe failed for narration: {error[:800]}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AudioProbeError("ffprobe returned invalid JSON for narration") from exc
    if not isinstance(payload, dict):
        raise AudioProbeError("ffprobe narration response root must be an object")
    result = parse_audio_probe_payload(payload, source)
    if not result.has_audio:
        raise AudioProbeError(f"Narration file contains no audio stream: {source}")
    if result.duration <= 0:
        raise AudioProbeError(f"Narration duration is unavailable: {source}")
    return result


def build_audio_plan(
    segments: list[TimelineSegment],
    duration: float,
    config: AudioConfig,
    requested_mode: str = "auto",
    narration_path: str | Path | None = None,
    narration_duration: float | None = None,
) -> AudioPlan:
    mode = resolve_audio_mode(requested_mode, narration_path)
    resolved_narration = ""
    if narration_path:
        resolved_narration = str(Path(narration_path).expanduser().resolve())
    source_seconds = sum(segment.duration for segment in segments if segment.audio_enabled)
    source_coverage = source_seconds / duration if duration > 0 else 0.0
    warnings: list[str] = []
    if mode in {"source", "mixed"} and source_coverage <= 0:
        warnings.append("Selected timeline has no usable original source audio")
    elif mode in {"source", "mixed"} and source_coverage < 0.5:
        warnings.append(f"Original source audio covers only {source_coverage:.1%} of the timeline")
    narration_seconds = max(0.0, float(narration_duration or 0.0))
    if mode in {"narration", "mixed"} and narration_seconds <= 0:
        warnings.append("Narration duration was not measured")
    return AudioPlan(
        mode=mode,
        narration_path=resolved_narration,
        narration_duration=round(narration_seconds, 6),
        sample_rate=config.sample_rate,
        channels=config.channels,
        source_volume=(
            config.mixed_source_volume if mode == "mixed" else config.source_volume
        ),
        narration_volume=config.narration_volume,
        normalize_source=config.normalize_source,
        normalize_narration=config.normalize_narration,
        narration_target_lufs=config.narration_target_lufs,
        source_target_lufs=config.source_target_lufs,
        true_peak=config.true_peak,
        loudness_range=config.loudness_range,
        ducking_threshold=config.ducking_threshold,
        ducking_ratio=config.ducking_ratio,
        ducking_attack_ms=config.ducking_attack_ms,
        ducking_release_ms=config.ducking_release_ms,
        source_audio_segments=sum(segment.audio_enabled for segment in segments),
        source_audio_coverage=round(source_coverage, 6),
        warnings=warnings,
    )
