from __future__ import annotations

import math
import re
import subprocess
from collections.abc import Callable
from pathlib import Path


class SceneDetectionError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]
_PTS_TIME = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


def _default_runner(*args, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def detect_scene_changes(
    path: str | Path,
    ffmpeg_path: str | None,
    threshold: float = 0.34,
    runner: Runner | None = None,
    timeout: float = 180.0,
) -> list[float]:
    if not ffmpeg_path:
        raise SceneDetectionError("ffmpeg is unavailable")
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Media file not found: {source}")
    threshold = max(0.01, min(0.99, threshold))
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-nostats",
        "-i",
        str(source),
        "-filter:v",
        f"select=gt(scene\\,{threshold:.4f}),showinfo",
        "-an",
        "-f",
        "null",
        "-",
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
        raise SceneDetectionError(f"Scene detection failed for {source}: {exc}") from exc
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "unknown ffmpeg error").strip()
        raise SceneDetectionError(f"Scene detection failed for {source}: {message[:500]}")
    text = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    values = sorted({round(float(match), 6) for match in _PTS_TIME.findall(text)})
    return [value for value in values if value > 0]


def fixed_windows(
    duration: float,
    window_seconds: float,
    minimum_seconds: float,
) -> list[tuple[float, float]]:
    if duration <= 0:
        return []
    window = max(window_seconds, minimum_seconds, 0.1)
    count = max(1, math.ceil(duration / window))
    ranges: list[tuple[float, float]] = []
    cursor = 0.0
    for index in range(count):
        end = duration if index == count - 1 else min(duration, cursor + window)
        if ranges and end - cursor < minimum_seconds:
            previous_start, _ = ranges[-1]
            ranges[-1] = (previous_start, round(end, 6))
        else:
            ranges.append((round(cursor, 6), round(end, 6)))
        cursor = end
    return ranges


def build_scene_ranges(
    duration: float,
    cut_points: list[float],
    minimum_seconds: float = 0.7,
    maximum_seconds: float = 6.0,
    fallback_window_seconds: float = 3.0,
) -> list[tuple[float, float]]:
    if duration <= 0:
        return []
    minimum = max(0.1, minimum_seconds)
    maximum = max(minimum, maximum_seconds)
    points = sorted({point for point in cut_points if minimum <= point <= duration - minimum})
    if not points:
        return fixed_windows(duration, min(maximum, fallback_window_seconds), minimum)

    boundaries = [0.0]
    for point in points:
        if point - boundaries[-1] >= minimum:
            boundaries.append(point)
    if duration - boundaries[-1] < minimum and len(boundaries) > 1:
        boundaries.pop()
    boundaries.append(duration)

    ranges: list[tuple[float, float]] = []
    for start, end in zip(boundaries, boundaries[1:], strict=True):
        length = end - start
        if length <= maximum:
            ranges.append((round(start, 6), round(end, 6)))
            continue
        pieces = fixed_windows(length, maximum, minimum)
        ranges.extend((round(start + left, 6), round(start + right, 6)) for left, right in pieces)
    return ranges
