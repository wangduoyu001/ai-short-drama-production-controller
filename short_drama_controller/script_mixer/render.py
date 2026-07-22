from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .models import Timeline


class RenderUnavailableError(RuntimeError):
    pass


def build_ffmpeg_command(
    timeline: Timeline,
    ffmpeg_path: str,
    output_path: str | Path,
    voice_path: str | Path | None = None,
) -> list[str]:
    if not timeline.segments:
        raise ValueError("Timeline contains no segments")
    output = Path(output_path)
    command = [ffmpeg_path, "-hide_banner", "-y"]
    for segment in timeline.segments:
        command.extend(["-i", segment.source_path])

    voice_input_index: int | None = None
    if voice_path is not None:
        voice_input_index = len(timeline.segments)
        command.extend(["-i", str(voice_path)])

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

    command.extend(["-filter_complex", ";".join(filters), "-map", "[outv]"])
    if voice_input_index is not None:
        command.extend(["-map", f"{voice_input_index}:a:0", "-c:a", "aac", "-b:a", "192k", "-shortest"])
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
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def save_render_plan(command: list[str], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"command": command}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def render_timeline(
    timeline: Timeline,
    ffmpeg_path: str | None,
    output_path: str | Path,
    voice_path: str | Path | None = None,
    dry_run: bool = False,
) -> list[str]:
    if not ffmpeg_path:
        raise RenderUnavailableError("ffmpeg was not discovered and no override was configured")
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = build_ffmpeg_command(timeline, ffmpeg_path, output, voice_path=voice_path)
    if dry_run:
        return command
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with exit code {completed.returncode}")
    return command
