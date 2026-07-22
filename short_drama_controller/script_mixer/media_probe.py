from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import MediaSource


class MediaProbeError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _default_runner(*args, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_fraction(value: str | None) -> float:
    if not value or value in {"0/0", "N/A"}:
        return 0.0
    if "/" not in value:
        return _float(value)
    numerator, denominator = value.split("/", 1)
    denominator_value = _float(denominator)
    if denominator_value == 0:
        return 0.0
    return _float(numerator) / denominator_value


def _rotation(video_stream: dict[str, Any]) -> int:
    tags = video_stream.get("tags") or {}
    if "rotate" in tags:
        return _int(tags.get("rotate")) % 360
    for item in video_stream.get("side_data_list") or []:
        if "rotation" in item:
            return _int(item.get("rotation")) % 360
    return 0


def parse_ffprobe_payload(
    payload: dict[str, Any],
    path: Path,
    source_id: str,
    fingerprint: str,
    file_size: int,
    modified_ns: int,
) -> MediaSource:
    streams = payload.get("streams") or []
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    if not video_stream:
        raise MediaProbeError(f"No video stream found: {path}")
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    format_data = payload.get("format") or {}

    duration = _float(format_data.get("duration"))
    if duration <= 0:
        duration = _float(video_stream.get("duration"))
    if duration <= 0:
        duration_ts = _float(video_stream.get("duration_ts"))
        time_base = parse_fraction(video_stream.get("time_base"))
        duration = duration_ts * time_base
    if duration <= 0:
        raise MediaProbeError(f"Unable to determine media duration: {path}")

    fps = parse_fraction(video_stream.get("avg_frame_rate"))
    if fps <= 0:
        fps = parse_fraction(video_stream.get("r_frame_rate"))

    return MediaSource(
        source_id=source_id,
        source_path=str(path.resolve()),
        filename=path.name,
        extension=path.suffix.casefold(),
        file_size=file_size,
        modified_ns=modified_ns,
        fingerprint=fingerprint,
        duration=round(duration, 6),
        width=_int(video_stream.get("width")),
        height=_int(video_stream.get("height")),
        fps=round(fps, 6),
        video_codec=str(video_stream.get("codec_name") or ""),
        audio_codec=str((audio_stream or {}).get("codec_name") or ""),
        has_audio=audio_stream is not None,
        rotation=_rotation(video_stream),
    )


def probe_media(
    path: str | Path,
    ffprobe_path: str | None,
    source_id: str,
    fingerprint: str,
    runner: Runner | None = None,
    timeout: float = 30.0,
) -> MediaSource:
    if not ffprobe_path:
        raise MediaProbeError("ffprobe is unavailable; run doctor or configure discovery.tool_overrides.ffprobe")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Media file not found: {source}")
    stat = source.stat()
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source),
    ]
    execute = runner or _default_runner
    try:
        completed = execute(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise MediaProbeError(f"ffprobe execution failed for {source}: {exc}") from exc
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "unknown ffprobe error").strip()
        raise MediaProbeError(f"ffprobe failed for {source}: {message[:500]}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise MediaProbeError(f"ffprobe returned invalid JSON for {source}") from exc
    if not isinstance(payload, dict):
        raise MediaProbeError(f"ffprobe root payload must be an object: {source}")
    return parse_ffprobe_payload(
        payload=payload,
        path=source,
        source_id=source_id,
        fingerprint=fingerprint,
        file_size=stat.st_size,
        modified_ns=stat.st_mtime_ns,
    )
