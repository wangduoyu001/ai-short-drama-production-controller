from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path


class ThumbnailError(RuntimeError):
    pass


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _default_runner(*args, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(*args, **kwargs)


def extract_thumbnail(
    source_path: str | Path,
    timestamp: float,
    output_path: str | Path,
    ffmpeg_path: str | None,
    width: int = 360,
    runner: Runner | None = None,
    timeout: float = 45.0,
) -> Path:
    if not ffmpeg_path:
        raise ThumbnailError("ffmpeg is unavailable")
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"Media file not found: {source}")
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{max(0.0, timestamp):.3f}",
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        f"scale={max(64, width)}:-2",
        "-q:v",
        "3",
        str(target),
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
        raise ThumbnailError(f"Thumbnail extraction failed for {source}: {exc}") from exc
    if completed.returncode != 0 or not target.exists():
        message = (completed.stderr or completed.stdout or "thumbnail was not created").strip()
        raise ThumbnailError(f"Thumbnail extraction failed for {source}: {message[:500]}")
    return target
