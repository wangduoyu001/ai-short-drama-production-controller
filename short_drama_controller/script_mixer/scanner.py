from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from .catalog import MediaCatalog
from .config import MediaScanConfig
from .media_probe import MediaProbeError, probe_media
from .models import MediaClip, MediaScanSummary, MediaSource
from .scene_detection import SceneDetectionError, build_scene_ranges, detect_scene_changes
from .thumbnails import ThumbnailError, extract_thumbnail


ProbeFunction = Callable[..., MediaSource]
SceneFunction = Callable[..., list[float]]
ThumbnailFunction = Callable[..., Path]


def stable_source_id(path: str | Path) -> str:
    normalized = str(Path(path).resolve()).replace("\\", "/").casefold()
    return "SRC_" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def fingerprint_file(path: str | Path, sample_bytes: int = 1_048_576) -> str:
    source = Path(path)
    stat = source.stat()
    digest = hashlib.sha256()
    digest.update(str(stat.st_size).encode("ascii"))
    digest.update(b":")
    digest.update(str(stat.st_mtime_ns).encode("ascii"))
    sample = max(4096, sample_bytes)
    with source.open("rb") as handle:
        digest.update(handle.read(sample))
        if stat.st_size > sample:
            handle.seek(max(0, stat.st_size - sample))
            digest.update(handle.read(sample))
    return digest.hexdigest()


def discover_media_files(root: str | Path, config: MediaScanConfig) -> list[Path]:
    base = Path(root).expanduser().resolve()
    if not base.is_dir():
        raise NotADirectoryError(f"Media root is not a directory: {base}")
    supported = {item.casefold() if item.startswith(".") else f".{item.casefold()}" for item in config.supported_extensions}
    iterator: Iterable[Path] = base.rglob("*") if config.recursive else base.glob("*")
    files: list[Path] = []
    for path in iterator:
        try:
            if path.is_symlink() and not config.follow_symlinks:
                continue
            if path.is_file() and path.suffix.casefold() in supported:
                files.append(path.resolve())
        except OSError:
            continue
    files.sort(key=lambda item: str(item).casefold())
    return files


def _path_tags(path: Path, root: Path) -> list[str]:
    try:
        relative = path.relative_to(root)
        parts = list(relative.parts[-4:])
    except ValueError:
        parts = list(path.parts[-4:])
    tokens: list[str] = []
    for part in parts:
        stem = Path(part).stem
        tokens.extend(item for item in re.split(r"[\s._\-—]+", stem) if len(item) >= 2)
    return list(dict.fromkeys(tokens))[:20]


def _quality_score(source: MediaSource) -> float:
    width, height = source.display_dimensions
    pixels = width * height
    resolution_score = min(1.0, pixels / float(1080 * 1920)) if pixels > 0 else 0.0
    fps_score = min(1.0, source.fps / 30.0) if source.fps > 0 else 0.0
    codec_bonus = 0.05 if source.video_codec in {"h264", "hevc", "av1", "vp9"} else 0.0
    return round(min(1.0, 0.35 + resolution_score * 0.45 + fps_score * 0.15 + codec_bonus), 4)


def _clip_id(source_id: str, index: int, start: float, end: float) -> str:
    key = f"{source_id}:{index}:{start:.6f}:{end:.6f}"
    return "CLP_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def _failed_source(path: Path, source_id: str, fingerprint: str, error: str) -> MediaSource:
    stat = path.stat()
    return MediaSource(
        source_id=source_id,
        source_path=str(path.resolve()),
        filename=path.name,
        extension=path.suffix.casefold(),
        file_size=stat.st_size,
        modified_ns=stat.st_mtime_ns,
        fingerprint=fingerprint,
        duration=0.0,
        width=0,
        height=0,
        fps=0.0,
        status="failed",
        error=error[:1000],
    )


class MediaScanner:
    def __init__(
        self,
        catalog: MediaCatalog,
        config: MediaScanConfig,
        ffprobe_path: str | None,
        ffmpeg_path: str | None,
        probe_function: ProbeFunction = probe_media,
        scene_function: SceneFunction = detect_scene_changes,
        thumbnail_function: ThumbnailFunction = extract_thumbnail,
    ):
        self.catalog = catalog
        self.config = config
        self.ffprobe_path = ffprobe_path
        self.ffmpeg_path = ffmpeg_path
        self.probe_function = probe_function
        self.scene_function = scene_function
        self.thumbnail_function = thumbnail_function

    def scan(
        self,
        root: str | Path,
        fast: bool = False,
        force: bool = False,
        prune_missing: bool = False,
    ) -> MediaScanSummary:
        base = Path(root).expanduser().resolve()
        files = discover_media_files(base, self.config)
        summary = MediaScanSummary(root=str(base), discovered_files=len(files))
        existing_paths = {str(item) for item in files}

        for path in files:
            try:
                fingerprint = fingerprint_file(path, self.config.fingerprint_sample_bytes)
            except OSError as exc:
                summary.failed_files += 1
                summary.errors.append(f"{path}: fingerprint failed: {exc}")
                continue

            existing = self.catalog.get_source_by_path(path)
            if existing and existing.fingerprint == fingerprint and not force:
                summary.unchanged_files += 1
                continue
            if existing:
                summary.changed_files += 1
            else:
                summary.new_files += 1

            source_id = existing.source_id if existing else stable_source_id(path)
            try:
                source = self.probe_function(
                    path=path,
                    ffprobe_path=self.ffprobe_path,
                    source_id=source_id,
                    fingerprint=fingerprint,
                )
            except (MediaProbeError, FileNotFoundError, OSError, ValueError) as exc:
                failed = _failed_source(path, source_id, fingerprint, str(exc))
                self.catalog.upsert_source(failed)
                summary.failed_files += 1
                summary.errors.append(f"{path}: {exc}")
                continue

            if source.duration < self.config.minimum_source_seconds:
                source.status = "skipped"
                source.error = "source duration is below minimum_source_seconds"
                self.catalog.replace_source_clips(source, [])
                summary.skipped_files += 1
                summary.sources_written += 1
                continue

            cut_points: list[float] = []
            detection_error = ""
            if self.config.scene_detection_enabled and not fast and self.ffmpeg_path:
                try:
                    cut_points = self.scene_function(
                        path=path,
                        ffmpeg_path=self.ffmpeg_path,
                        threshold=self.config.scene_threshold,
                    )
                except (SceneDetectionError, FileNotFoundError, OSError, ValueError) as exc:
                    detection_error = str(exc)

            ranges = build_scene_ranges(
                duration=source.duration,
                cut_points=cut_points,
                minimum_seconds=self.config.minimum_scene_seconds,
                maximum_seconds=(
                    self.config.fallback_window_seconds if fast else self.config.maximum_scene_seconds
                ),
                fallback_window_seconds=self.config.fallback_window_seconds,
            )
            if not ranges:
                source.status = "failed"
                source.error = "no valid clip ranges were produced"
                self.catalog.replace_source_clips(source, [])
                summary.failed_files += 1
                summary.sources_written += 1
                summary.errors.append(f"{path}: no valid clip ranges")
                continue

            tags = _path_tags(path, base)
            description = " ".join(tags) if tags else path.stem
            width, height = source.display_dimensions
            clips: list[MediaClip] = []
            for index, (start, end) in enumerate(ranges, start=1):
                midpoint = start + (end - start) / 2
                thumbnail_path = ""
                if self.config.generate_thumbnails and not fast and self.ffmpeg_path:
                    target = (
                        Path(self.config.thumbnail_root)
                        / source.source_id
                        / f"{index:05d}_{midpoint:.3f}.jpg"
                    )
                    try:
                        created = self.thumbnail_function(
                            source_path=path,
                            timestamp=midpoint,
                            output_path=target,
                            ffmpeg_path=self.ffmpeg_path,
                            width=self.config.thumbnail_width,
                        )
                        thumbnail_path = str(created)
                        summary.thumbnails_written += 1
                    except (ThumbnailError, FileNotFoundError, OSError, ValueError):
                        thumbnail_path = ""

                clips.append(
                    MediaClip(
                        clip_id=_clip_id(source.source_id, index, start, end),
                        source_id=source.source_id,
                        source_path=source.source_path,
                        source_start=start,
                        source_end=end,
                        duration=round(end - start, 6),
                        description=description,
                        tags=tags,
                        width=width,
                        height=height,
                        quality_score=_quality_score(source),
                        usable=True,
                        thumbnail_path=thumbnail_path,
                    )
                )

            source.status = "ready"
            source.error = f"scene detection fallback: {detection_error}" if detection_error else ""
            written = self.catalog.replace_source_clips(source, clips)
            summary.sources_written += 1
            summary.clips_written += written

        if prune_missing:
            removed = self.catalog.delete_missing_sources(existing_paths, base)
            if removed:
                summary.errors.append(f"pruned_missing_sources={removed}")
        return summary
