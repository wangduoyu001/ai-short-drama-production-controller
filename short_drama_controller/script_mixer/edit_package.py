from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import RuntimeConfig
from .models import CandidateClip, MediaClip, TimelineSegment
from .review import load_candidates, load_timeline, resolve_project_dir


Runner = Callable[..., subprocess.CompletedProcess[str]]


class EditPackageError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _safe_name(value: str, maximum: int = 80) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|\s]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_.")
    return (cleaned or "item")[:maximum]


def _file_signature(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def _content_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _channel_layout(channels: int) -> str:
    return "mono" if channels == 1 else "stereo"


def _run_command(runner: Runner, command: list[str], timeout: float = 1800.0) -> None:
    completed = runner(command, check=False, capture_output=True, text=True, timeout=timeout)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "unknown ffmpeg error").strip()
        raise EditPackageError(f"Command failed ({completed.returncode}): {message[-2000:]}")


def probe_media_duration(
    path: str | Path,
    ffprobe_path: str | None,
    runner: Runner = subprocess.run,
) -> float:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Media file not found: {source}")
    if not ffprobe_path:
        return 0.0
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(source),
    ]
    completed = runner(command, check=False, capture_output=True, text=True, timeout=60.0)
    if completed.returncode != 0:
        return 0.0
    try:
        payload = json.loads(completed.stdout or "{}")
        return max(0.0, float(payload.get("format", {}).get("duration", 0.0)))
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0.0


def calculate_edit_window(
    source_start: float,
    source_end: float,
    source_duration: float,
    process_cap: float,
    handle_before: float,
    handle_after: float,
) -> dict[str, float]:
    upper = source_duration if source_duration > 0 else source_end + max(0.0, handle_after)
    if process_cap > 0:
        upper = min(upper, process_cap)
    media_start = max(0.0, source_start - max(0.0, handle_before))
    media_end = min(upper, source_end + max(0.0, handle_after))
    if media_end < source_end - 0.001:
        raise EditPackageError(
            f"Selected source range {source_start:.3f}-{source_end:.3f}s exceeds usable source window"
        )
    if media_end <= media_start:
        raise EditPackageError("Edit window has no positive duration")
    selected_in = max(0.0, source_start - media_start)
    selected_duration = max(0.001, source_end - source_start)
    return {
        "media_start": round(media_start, 6),
        "media_end": round(media_end, 6),
        "media_duration": round(media_end - media_start, 6),
        "selected_in": round(selected_in, 6),
        "selected_out": round(selected_in + selected_duration, 6),
        "selected_duration": round(selected_duration, 6),
        "handle_before": round(selected_in, 6),
        "handle_after": round(max(0.0, media_end - source_end), 6),
    }


def build_proxy_video_command(
    ffmpeg_path: str,
    source_path: str | Path,
    output_path: str | Path,
    window: dict[str, float],
    width: int,
    height: int,
    fps: int,
    codec: str,
    preset: str,
    crf: int,
) -> list[str]:
    video_filter = (
        f"trim=start={window['media_start']:.6f}:end={window['media_end']:.6f},"
        "setpts=PTS-STARTPTS,"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},setsar=1,format=yuv420p"
    )
    return [
        ffmpeg_path,
        "-hide_banner",
        "-y",
        "-i",
        str(Path(source_path).resolve()),
        "-map",
        "0:v:0",
        "-vf",
        video_filter,
        "-an",
        "-c:v",
        codec,
        "-preset",
        preset,
        "-crf",
        str(crf),
        "-fps_mode",
        "cfr",
        "-movflags",
        "+faststart",
        str(Path(output_path).resolve()),
    ]


def build_audio_stem_command(
    ffmpeg_path: str,
    source_path: str | Path,
    output_path: str | Path,
    window: dict[str, float],
    sample_rate: int,
    channels: int,
    codec: str,
) -> list[str]:
    layout = _channel_layout(channels)
    audio_filter = (
        f"atrim=start={window['media_start']:.6f}:end={window['media_end']:.6f},"
        "asetpts=PTS-STARTPTS,"
        f"aresample={sample_rate},"
        f"aformat=sample_rates={sample_rate}:channel_layouts={layout}"
    )
    return [
        ffmpeg_path,
        "-hide_banner",
        "-y",
        "-i",
        str(Path(source_path).resolve()),
        "-map",
        "0:a:0",
        "-af",
        audio_filter,
        "-c:a",
        codec,
        str(Path(output_path).resolve()),
    ]


def build_narration_wav_command(
    ffmpeg_path: str,
    source_path: str | Path,
    output_path: str | Path,
    duration: float,
    sample_rate: int,
    channels: int,
    codec: str,
) -> list[str]:
    layout = _channel_layout(channels)
    return [
        ffmpeg_path,
        "-hide_banner",
        "-y",
        "-i",
        str(Path(source_path).resolve()),
        "-vn",
        "-af",
        (
            f"atrim=start=0:end={duration:.6f},asetpts=PTS-STARTPTS,"
            f"aresample={sample_rate},"
            f"aformat=sample_rates={sample_rate}:channel_layouts={layout},"
            f"apad=pad_dur={duration:.6f},atrim=duration={duration:.6f}"
        ),
        "-c:a",
        codec,
        str(Path(output_path).resolve()),
    ]


def _previous_assets(manifest_path: Path) -> dict[str, dict[str, Any]]:
    if not manifest_path.is_file():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    assets: dict[str, dict[str, Any]] = {}
    for row in payload.get("segments", []):
        if isinstance(row, dict) and row.get("asset_key"):
            assets[str(row["asset_key"])] = row
    for rows in payload.get("candidates", {}).values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("asset_key"):
                assets[str(row["asset_key"])] = row
    narration = payload.get("narration")
    if isinstance(narration, dict) and narration.get("asset_key"):
        assets[str(narration["asset_key"])] = narration
    return assets


def _can_reuse(previous: dict[str, Any] | None, digest: str, required: list[Path]) -> bool:
    return bool(
        previous
        and previous.get("content_hash") == digest
        and all(path.is_file() and path.stat().st_size > 0 for path in required)
    )


def _copy_subtitle(source: str, target: Path, dry_run: bool) -> str:
    if not source:
        return ""
    path = Path(source)
    if not path.is_file():
        return ""
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return str(target.resolve())


def _segment_filename(segment: TimelineSegment) -> str:
    source = _safe_name(segment.source_id or Path(segment.source_path).stem, 32)
    return (
        f"{_safe_name(segment.segment_id, 16)}_{source}_"
        f"{segment.source_start:.3f}-{segment.source_end:.3f}.mp4"
    )


def _candidate_filename(rank: int, clip: MediaClip) -> str:
    source = _safe_name(clip.source_id or Path(clip.source_path).stem, 28)
    return f"C{rank:02d}_{source}_{clip.source_start:.3f}-{clip.source_end:.3f}.mp4"


class EditPackageExporter:
    def __init__(
        self,
        config: RuntimeConfig,
        ffmpeg_path: str | None,
        ffprobe_path: str | None,
        runner: Runner = subprocess.run,
    ):
        self.config = config
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.runner = runner
        self._duration_cache: dict[str, float] = {}

    def export(
        self,
        project: str | Path,
        draft_root: str | Path | None = None,
        draft_name: str | None = None,
        create_draft: bool | None = None,
        require_draft: bool | None = None,
        candidate_count: int | None = None,
        handle_before: float | None = None,
        handle_after: float | None = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if not self.ffmpeg_path:
            raise EditPackageError("FFmpeg is required to export the Jianying edit package")
        project_dir = resolve_project_dir(project, self.config.output_root)
        timeline = load_timeline(project_dir)
        package_dir = project_dir / "exports" / self.config.edit_package.output_dir_name
        video_dir = package_dir / "video"
        audio_dir = package_dir / "audio"
        subtitle_dir = package_dir / "subtitles"
        candidate_root = package_dir / "candidates"
        metadata_dir = package_dir / "metadata"
        for path in (video_dir, audio_dir, subtitle_dir, candidate_root, metadata_dir):
            path.mkdir(parents=True, exist_ok=True)

        manifest_path = metadata_dir / "package_manifest.json"
        previous = _previous_assets(manifest_path)
        before = self.config.edit_package.handle_before_seconds if handle_before is None else handle_before
        after = self.config.edit_package.handle_after_seconds if handle_after is None else handle_after
        wanted_candidates = (
            self.config.edit_package.candidate_export_count
            if candidate_count is None
            else max(0, candidate_count)
        )
        commands: list[list[str]] = []
        warnings: list[str] = []
        failures: list[str] = []
        reused_count = 0
        rendered_count = 0
        segment_rows: list[dict[str, Any]] = []

        for segment in timeline.segments:
            try:
                row, reused, rendered, row_commands = self._export_segment(
                    segment=segment,
                    timeline_width=timeline.width,
                    timeline_height=timeline.height,
                    timeline_fps=timeline.fps,
                    video_dir=video_dir,
                    audio_dir=audio_dir,
                    previous=previous,
                    handle_before=before,
                    handle_after=after,
                    force=force,
                    dry_run=dry_run,
                )
                segment_rows.append(row)
                commands.extend(row_commands)
                reused_count += int(reused)
                rendered_count += int(rendered)
            except (EditPackageError, FileNotFoundError, OSError, ValueError) as exc:
                failures.append(f"{segment.segment_id}: {exc}")

        if failures:
            raise EditPackageError(
                "Current timeline segments could not be exported: " + " | ".join(failures)
            )

        candidates_payload: dict[str, list[dict[str, Any]]] = {}
        if wanted_candidates > 0:
            try:
                candidates_by_unit = load_candidates(project_dir)
            except Exception as exc:
                candidates_by_unit = {}
                warnings.append(f"Candidate export skipped: {exc}")
            for segment, segment_row in zip(timeline.segments, segment_rows):
                rows: list[dict[str, Any]] = []
                exported = 0
                for original_rank, candidate in enumerate(
                    candidates_by_unit.get(segment.unit_id, []), start=1
                ):
                    if exported >= wanted_candidates:
                        break
                    clip = candidate.clip
                    if clip.clip_id == segment.clip_id:
                        continue
                    try:
                        row, reused, rendered, row_commands = self._export_candidate(
                            segment=segment,
                            candidate=candidate,
                            original_rank=original_rank,
                            candidate_rank=exported + 1,
                            target_dir=candidate_root / segment.segment_id,
                            timeline_width=timeline.width,
                            timeline_height=timeline.height,
                            timeline_fps=timeline.fps,
                            previous=previous,
                            handle_before=before,
                            handle_after=after,
                            force=force,
                            dry_run=dry_run,
                        )
                    except (EditPackageError, FileNotFoundError, OSError, ValueError) as exc:
                        warnings.append(
                            f"{segment.segment_id} candidate {original_rank} skipped: {exc}"
                        )
                        continue
                    rows.append(row)
                    commands.extend(row_commands)
                    reused_count += int(reused)
                    rendered_count += int(rendered)
                    exported += 1
                candidates_payload[segment.segment_id] = rows
                segment_row["candidate_directory"] = str(
                    (candidate_root / segment.segment_id).resolve()
                )
                segment_row["candidate_count"] = len(rows)

        narration_row: dict[str, Any] = {}
        narration_source = Path(timeline.audio.narration_path) if timeline.audio.narration_path else None
        if (
            self.config.edit_package.export_narration_wav
            and narration_source
            and narration_source.is_file()
        ):
            narration_target = audio_dir / "narration.wav"
            digest = _content_hash(
                {
                    "kind": "narration",
                    "source": _file_signature(narration_source),
                    "duration": timeline.duration,
                    "sample_rate": self.config.edit_package.sample_rate,
                    "channels": self.config.edit_package.channels,
                    "codec": self.config.edit_package.audio_codec,
                }
            )
            asset_key = "narration"
            reused = not force and _can_reuse(
                previous.get(asset_key), digest, [narration_target]
            )
            command = build_narration_wav_command(
                self.ffmpeg_path,
                narration_source,
                narration_target,
                timeline.duration,
                self.config.edit_package.sample_rate,
                self.config.edit_package.channels,
                self.config.edit_package.audio_codec,
            )
            commands.append(command)
            if not reused and not dry_run:
                narration_target.parent.mkdir(parents=True, exist_ok=True)
                _run_command(self.runner, command)
                rendered_count += 1
            elif reused:
                reused_count += 1
            narration_row = {
                "asset_key": asset_key,
                "content_hash": digest,
                "source_path": str(narration_source.resolve()),
                "output_path": str(narration_target.resolve()),
                "timeline_start": 0.0,
                "timeline_duration": timeline.duration,
                "reused": reused,
            }

        subtitle_paths: dict[str, str] = {}
        if self.config.edit_package.export_subtitles:
            subtitle_paths = {
                "srt": _copy_subtitle(
                    timeline.audio.subtitle_srt_path,
                    subtitle_dir / "captions.srt",
                    dry_run,
                ),
                "ass": _copy_subtitle(
                    timeline.audio.subtitle_ass_path,
                    subtitle_dir / "captions.ass",
                    dry_run,
                ),
                "karaoke_ass": _copy_subtitle(
                    timeline.audio.subtitle_karaoke_ass_path,
                    subtitle_dir / "captions.karaoke.ass",
                    dry_run,
                ),
            }

        manifest: dict[str, Any] = {
            "schema_version": 1,
            "project_id": timeline.project_id,
            "generated_at": _utc_now(),
            "project_dir": str(project_dir.resolve()),
            "package_dir": str(package_dir.resolve()),
            "timeline": {
                "width": timeline.width,
                "height": timeline.height,
                "fps": timeline.fps,
                "duration": timeline.duration,
            },
            "settings": asdict(self.config.edit_package),
            "segments": segment_rows,
            "candidates": candidates_payload,
            "narration": narration_row,
            "subtitles": subtitle_paths,
            "audio_mode": timeline.audio.mode,
            "commands_path": str((metadata_dir / "ffmpeg_commands.json").resolve()),
            "reused_asset_count": reused_count,
            "rendered_asset_count": rendered_count,
            "warnings": warnings,
            "failures": failures,
            "dry_run": dry_run,
            "jianying_draft": {},
        }
        self._write_tables(package_dir, manifest, dry_run)
        _atomic_write_json(metadata_dir / "ffmpeg_commands.json", commands)
        _atomic_write_json(manifest_path, manifest)

        should_create_draft = (
            self.config.edit_package.create_jianying_draft
            if create_draft is None
            else create_draft
        )
        must_create_draft = (
            self.config.edit_package.require_jianying_draft
            if require_draft is None
            else require_draft
        )
        if should_create_draft and not dry_run:
            try:
                from .jianying_draft import create_jianying_draft

                draft_result = create_jianying_draft(
                    manifest=manifest,
                    config=self.config,
                    draft_root=draft_root,
                    draft_name=draft_name,
                )
                manifest["jianying_draft"] = draft_result
            except Exception as exc:
                manifest["jianying_draft"] = {
                    "created": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                manifest["warnings"].append(
                    "Jianying draft was not created; the standard edit package remains usable"
                )
                if must_create_draft:
                    _atomic_write_json(manifest_path, manifest)
                    raise EditPackageError(str(exc)) from exc
            _atomic_write_json(manifest_path, manifest)

        return manifest

    def _duration(self, path: Path) -> float:
        key = str(path.resolve())
        if key not in self._duration_cache:
            self._duration_cache[key] = probe_media_duration(
                path, self.ffprobe_path, runner=self.runner
            )
        return self._duration_cache[key]

    def _export_segment(
        self,
        segment: TimelineSegment,
        timeline_width: int,
        timeline_height: int,
        timeline_fps: int,
        video_dir: Path,
        audio_dir: Path,
        previous: dict[str, dict[str, Any]],
        handle_before: float,
        handle_after: float,
        force: bool,
        dry_run: bool,
    ) -> tuple[dict[str, Any], bool, bool, list[list[str]]]:
        source = Path(segment.source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Source media is missing: {source}")
        duration = self._duration(source)
        window = calculate_edit_window(
            segment.source_start,
            segment.source_end,
            duration,
            self.config.media_scan.maximum_source_process_seconds,
            handle_before,
            handle_after,
        )
        target = video_dir / _segment_filename(segment)
        audio_target = audio_dir / f"{_safe_name(segment.segment_id)}_source.wav"
        payload = {
            "kind": "timeline_segment",
            "segment": {
                "segment_id": segment.segment_id,
                "clip_id": segment.clip_id,
                "source_start": segment.source_start,
                "source_end": segment.source_end,
                "speed": segment.speed,
                "audio_enabled": segment.audio_enabled,
            },
            "source": _file_signature(source),
            "window": window,
            "video": {
                "width": timeline_width,
                "height": timeline_height,
                "fps": timeline_fps,
                "codec": self.config.edit_package.video_codec,
                "preset": self.config.edit_package.video_preset,
                "crf": self.config.edit_package.video_crf,
            },
            "audio": {
                "enabled": self.config.edit_package.export_source_audio_stems
                and segment.audio_enabled,
                "sample_rate": self.config.edit_package.sample_rate,
                "channels": self.config.edit_package.channels,
                "codec": self.config.edit_package.audio_codec,
            },
        }
        digest = _content_hash(payload)
        asset_key = f"segment:{segment.segment_id}"
        required = [target]
        export_audio = self.config.edit_package.export_source_audio_stems and segment.audio_enabled
        if export_audio:
            required.append(audio_target)
        reused = not force and _can_reuse(previous.get(asset_key), digest, required)
        commands = [
            build_proxy_video_command(
                self.ffmpeg_path or "ffmpeg",
                source,
                target,
                window,
                timeline_width,
                timeline_height,
                timeline_fps,
                self.config.edit_package.video_codec,
                self.config.edit_package.video_preset,
                self.config.edit_package.video_crf,
            )
        ]
        if export_audio:
            commands.append(
                build_audio_stem_command(
                    self.ffmpeg_path or "ffmpeg",
                    source,
                    audio_target,
                    window,
                    self.config.edit_package.sample_rate,
                    self.config.edit_package.channels,
                    self.config.edit_package.audio_codec,
                )
            )
        if not reused and not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            _run_command(self.runner, commands[0])
            if export_audio:
                audio_target.parent.mkdir(parents=True, exist_ok=True)
                _run_command(self.runner, commands[1])
        row = {
            "asset_key": asset_key,
            "content_hash": digest,
            "segment_id": segment.segment_id,
            "unit_id": segment.unit_id,
            "clip_id": segment.clip_id,
            "source_id": segment.source_id,
            "source_path": str(source.resolve()),
            "source_duration": duration,
            "timeline_start": segment.timeline_start,
            "timeline_end": segment.timeline_end,
            "timeline_duration": segment.duration,
            "source_start": segment.source_start,
            "source_end": segment.source_end,
            "speed": segment.speed,
            "match_score": segment.match_score,
            "locked": segment.locked,
            "review_status": segment.review_status,
            "proxy_video_path": str(target.resolve()),
            "source_audio_path": str(audio_target.resolve()) if export_audio else "",
            **window,
            "reused": reused,
        }
        return row, reused, not reused and not dry_run, commands

    def _export_candidate(
        self,
        segment: TimelineSegment,
        candidate: CandidateClip,
        original_rank: int,
        candidate_rank: int,
        target_dir: Path,
        timeline_width: int,
        timeline_height: int,
        timeline_fps: int,
        previous: dict[str, dict[str, Any]],
        handle_before: float,
        handle_after: float,
        force: bool,
        dry_run: bool,
    ) -> tuple[dict[str, Any], bool, bool, list[list[str]]]:
        clip = candidate.clip
        source = Path(clip.source_path)
        if not source.is_file():
            raise FileNotFoundError(f"Candidate source media is missing: {source}")
        duration = self._duration(source)
        window = calculate_edit_window(
            clip.source_start,
            clip.source_end,
            duration,
            self.config.media_scan.maximum_source_process_seconds,
            handle_before,
            handle_after,
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / _candidate_filename(candidate_rank, clip)
        payload = {
            "kind": "candidate",
            "segment_id": segment.segment_id,
            "clip": asdict(clip),
            "source": _file_signature(source),
            "window": window,
            "width": timeline_width,
            "height": timeline_height,
            "fps": timeline_fps,
            "codec": self.config.edit_package.video_codec,
            "preset": self.config.edit_package.video_preset,
            "crf": self.config.edit_package.video_crf,
        }
        digest = _content_hash(payload)
        asset_key = f"candidate:{segment.segment_id}:{clip.clip_id}"
        reused = not force and _can_reuse(previous.get(asset_key), digest, [target])
        command = build_proxy_video_command(
            self.ffmpeg_path or "ffmpeg",
            source,
            target,
            window,
            timeline_width,
            timeline_height,
            timeline_fps,
            self.config.edit_package.video_codec,
            self.config.edit_package.video_preset,
            self.config.edit_package.video_crf,
        )
        if not reused and not dry_run:
            _run_command(self.runner, command)
        row = {
            "asset_key": asset_key,
            "content_hash": digest,
            "segment_id": segment.segment_id,
            "unit_id": segment.unit_id,
            "candidate_rank": candidate_rank,
            "original_candidate_rank": original_rank,
            "clip_id": clip.clip_id,
            "source_id": clip.source_id,
            "source_path": str(source.resolve()),
            "source_duration": duration,
            "source_start": clip.source_start,
            "source_end": clip.source_end,
            "description": clip.description,
            "tags": clip.tags,
            "emotions": clip.emotions,
            "shot_type": clip.shot_type,
            "has_audio": clip.has_audio,
            "score": candidate.score,
            "reasons": candidate.reasons,
            "proxy_video_path": str(target.resolve()),
            **window,
            "reused": reused,
        }
        return row, reused, not reused and not dry_run, [command]

    @staticmethod
    def _write_tables(package_dir: Path, manifest: dict[str, Any], dry_run: bool) -> None:
        metadata_dir = package_dir / "metadata"
        if not dry_run:
            with (metadata_dir / "timeline.csv").open("w", encoding="utf-8-sig", newline="") as handle:
                fieldnames = [
                    "segment_id",
                    "timeline_start",
                    "timeline_end",
                    "timeline_duration",
                    "source_id",
                    "source_start",
                    "source_end",
                    "media_start",
                    "media_end",
                    "handle_before",
                    "handle_after",
                    "selected_in",
                    "selected_out",
                    "speed",
                    "proxy_video_path",
                    "source_audio_path",
                    "locked",
                    "review_status",
                ]
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(manifest["segments"])
            guide = """剪映人工修改说明

1. 优先打开自动生成的剪映草稿；草稿不可用时，导入 video 文件夹中的镜头。
2. 每个镜头已经统一为固定帧率、统一画幅和H.264代理，减少卡帧、黑帧和时间戳问题。
3. 镜头文件包含前后余量。timeline.csv中的 selected_in/selected_out 是系统原始选择区间；可在剪映中向前或向后拖动。
4. audio 文件夹包含原声分段和完整配音；subtitles 文件夹包含SRT/ASS字幕。
5. candidates/Sxxx 中是该片段的备用画面，可直接拖入剪映替换。
6. 剪映修改完成后，以剪映工程为最终人工版本；不要反向覆盖原始素材。
7. 系统仍只允许使用每个原视频前40秒。
"""
            (package_dir / "剪映导入与修改说明.txt").write_text(guide, encoding="utf-8")
