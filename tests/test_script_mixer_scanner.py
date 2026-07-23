from __future__ import annotations

import subprocess
from pathlib import Path

from short_drama_controller.script_mixer.catalog import MediaCatalog
from short_drama_controller.script_mixer.config import MediaScanConfig
from short_drama_controller.script_mixer.media_probe import parse_ffprobe_payload
from short_drama_controller.script_mixer.models import MediaSource
from short_drama_controller.script_mixer.scanner import MediaScanner, discover_media_files
from short_drama_controller.script_mixer.scene_detection import (
    build_scene_ranges,
    detect_scene_changes,
    fixed_windows,
)


def _source_from_probe(kwargs, duration: float) -> MediaSource:
    path = Path(kwargs["path"])
    stat = path.stat()
    return MediaSource(
        source_id=kwargs["source_id"],
        source_path=str(path.resolve()),
        filename=path.name,
        extension=path.suffix.casefold(),
        file_size=stat.st_size,
        modified_ns=stat.st_mtime_ns,
        fingerprint=kwargs["fingerprint"],
        duration=duration,
        width=1920,
        height=1080,
        fps=30.0,
        video_codec="h264",
        audio_codec="aac",
        has_audio=True,
    )


def _fake_probe(**kwargs) -> MediaSource:
    return _source_from_probe(kwargs, 9.0)


def _fake_long_probe(**kwargs) -> MediaSource:
    return _source_from_probe(kwargs, 95.0)


def _fake_scene(**kwargs) -> list[float]:
    return [2.0, 5.0]


def _fake_long_scene(**kwargs) -> list[float]:
    assert kwargs.get("max_duration") == 40.0
    return [2.0, 12.0, 39.0, 55.0]


def _fake_thumbnail(**kwargs) -> Path:
    target = Path(kwargs["output_path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"thumbnail")
    return target


def test_parse_ffprobe_payload_rotation(tmp_path: Path) -> None:
    source = tmp_path / "vertical.mp4"
    source.write_bytes(b"video")
    payload = {
        "format": {"duration": "12.5"},
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "avg_frame_rate": "30000/1001",
                "tags": {"rotate": "90"},
            },
            {"codec_type": "audio", "codec_name": "aac"},
        ],
    }
    result = parse_ffprobe_payload(
        payload=payload,
        path=source,
        source_id="SRC_TEST",
        fingerprint="abc",
        file_size=source.stat().st_size,
        modified_ns=source.stat().st_mtime_ns,
    )
    assert result.duration == 12.5
    assert result.has_audio is True
    assert result.is_vertical is True
    assert result.display_dimensions == (1080, 1920)
    assert 29.9 < result.fps < 30.0


def test_scene_range_fallback_and_long_scene_split() -> None:
    assert fixed_windows(7.0, 3.0, 0.7) == [(0.0, 3.0), (3.0, 6.0), (6.0, 7.0)]
    ranges = build_scene_ranges(
        duration=15.0,
        cut_points=[2.0, 12.0],
        minimum_seconds=0.7,
        maximum_seconds=4.0,
        fallback_window_seconds=3.0,
    )
    assert ranges[0] == (0.0, 2.0)
    assert ranges[-1] == (12.0, 15.0)
    assert all(0.7 <= end - start <= 4.0 for start, end in ranges)


def test_scene_detection_limits_ffmpeg_to_processing_window(tmp_path: Path) -> None:
    source = tmp_path / "long.mp4"
    source.write_bytes(b"video")
    captured: list[str] = []

    def runner(command, **_kwargs):
        captured.extend(command)
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="",
            stderr="pts_time:10.000\npts_time:39.500\npts_time:45.000\n",
        )

    result = detect_scene_changes(
        source,
        "ffmpeg",
        threshold=0.34,
        max_duration=40.0,
        runner=runner,
    )
    assert captured[captured.index("-t") + 1] == "40.000000"
    assert result == [10.0, 39.5]


def test_discover_media_files_filters_extensions(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "a.mp4").write_bytes(b"a")
    (nested / "b.MOV").write_bytes(b"b")
    (nested / "ignore.txt").write_text("x", encoding="utf-8")
    files = discover_media_files(tmp_path, MediaScanConfig(generate_thumbnails=False))
    assert [item.name for item in files] == ["a.mp4", "b.MOV"]


def test_incremental_media_scan(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    first = media_root / "办公室_电脑.mp4"
    second = media_root / "城市_夜景.mp4"
    first.write_bytes(b"first-video")
    second.write_bytes(b"second-video")

    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    config = MediaScanConfig(
        generate_thumbnails=False,
        scene_detection_enabled=True,
        minimum_scene_seconds=0.7,
        maximum_scene_seconds=6.0,
    )
    scanner = MediaScanner(
        catalog=catalog,
        config=config,
        ffprobe_path="fake-ffprobe",
        ffmpeg_path="fake-ffmpeg",
        probe_function=_fake_probe,
        scene_function=_fake_scene,
    )

    first_summary = scanner.scan(media_root)
    assert first_summary.new_files == 2
    assert first_summary.sources_written == 2
    assert first_summary.clips_written == 6
    assert first_summary.capped_files == 0
    assert first_summary.indexed_duration_seconds == 18.0
    assert len(catalog.list_sources()) == 2
    assert len(catalog.list_clips()) == 6
    assert any("办公室" in clip.tags for clip in catalog.list_clips())

    second_summary = scanner.scan(media_root)
    assert second_summary.unchanged_files == 2
    assert second_summary.clips_written == 0

    first.write_bytes(b"first-video-changed")
    third_summary = scanner.scan(media_root)
    assert third_summary.changed_files == 1
    assert third_summary.unchanged_files == 1
    assert third_summary.clips_written == 3
    assert len(catalog.list_clips()) == 6


def test_long_source_only_indexes_first_40_seconds(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    source_path = media_root / "long_source.mp4"
    source_path.write_bytes(b"long-video")
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    scanner = MediaScanner(
        catalog=catalog,
        config=MediaScanConfig(
            maximum_source_process_seconds=40.0,
            generate_thumbnails=False,
            scene_detection_enabled=True,
        ),
        ffprobe_path="fake-ffprobe",
        ffmpeg_path="fake-ffmpeg",
        probe_function=_fake_long_probe,
        scene_function=_fake_long_scene,
    )

    summary = scanner.scan(media_root)
    stored = catalog.list_sources()[0]
    clips = catalog.list_clips()
    assert summary.capped_files == 1
    assert summary.indexed_duration_seconds == 40.0
    assert summary.ignored_tail_seconds == 55.0
    assert stored.duration == 95.0
    assert stored.indexed_duration == 40.0
    assert stored.ignored_tail_seconds == 55.0
    assert clips
    assert max(clip.source_end for clip in clips) == 40.0
    assert all(0.0 <= clip.source_start < clip.source_end <= 40.0 for clip in clips)
    assert "ignored tail 55.000s" in stored.error


def test_existing_full_index_is_rebuilt_when_40_second_limit_is_enabled(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    source_path = media_root / "reindex.mp4"
    source_path.write_bytes(b"video")
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    unlimited = MediaScanner(
        catalog=catalog,
        config=MediaScanConfig(
            maximum_source_process_seconds=0.0,
            generate_thumbnails=False,
            scene_detection_enabled=False,
        ),
        ffprobe_path="fake-ffprobe",
        ffmpeg_path=None,
        probe_function=_fake_long_probe,
    )
    first = unlimited.scan(media_root, fast=True)
    assert first.new_files == 1
    assert catalog.list_sources()[0].indexed_duration == 95.0
    assert max(clip.source_end for clip in catalog.list_clips()) == 95.0

    capped = MediaScanner(
        catalog=catalog,
        config=MediaScanConfig(
            maximum_source_process_seconds=40.0,
            generate_thumbnails=False,
            scene_detection_enabled=False,
        ),
        ffprobe_path="fake-ffprobe",
        ffmpeg_path=None,
        probe_function=_fake_long_probe,
    )
    second = capped.scan(media_root, fast=True)
    assert second.changed_files == 1
    assert second.capped_files == 1
    assert catalog.list_sources()[0].indexed_duration == 40.0
    assert max(clip.source_end for clip in catalog.list_clips()) == 40.0


def test_fast_scan_upgrades_without_force(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    source = media_root / "upgrade.mp4"
    source.write_bytes(b"video")
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    config = MediaScanConfig(
        generate_thumbnails=True,
        thumbnail_root=str(tmp_path / "thumbs"),
        scene_detection_enabled=True,
    )
    scanner = MediaScanner(
        catalog=catalog,
        config=config,
        ffprobe_path="fake-ffprobe",
        ffmpeg_path="fake-ffmpeg",
        probe_function=_fake_probe,
        scene_function=_fake_scene,
        thumbnail_function=_fake_thumbnail,
    )

    fast_summary = scanner.scan(media_root, fast=True)
    assert fast_summary.new_files == 1
    assert catalog.list_sources()[0].status == "fast"
    assert all(not clip.thumbnail_path for clip in catalog.list_clips())

    full_summary = scanner.scan(media_root)
    assert full_summary.changed_files == 1
    assert full_summary.thumbnails_written == 3
    assert catalog.list_sources()[0].status == "ready"
    assert all(Path(clip.thumbnail_path).is_file() for clip in catalog.list_clips())


def test_prune_missing_source(tmp_path: Path) -> None:
    media_root = tmp_path / "media"
    media_root.mkdir()
    source = media_root / "temporary.mp4"
    source.write_bytes(b"video")
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    scanner = MediaScanner(
        catalog=catalog,
        config=MediaScanConfig(generate_thumbnails=False),
        ffprobe_path="fake-ffprobe",
        ffmpeg_path=None,
        probe_function=_fake_probe,
    )
    scanner.scan(media_root, fast=True)
    assert len(catalog.list_sources()) == 1
    source.unlink()
    scanner.scan(media_root, fast=True, prune_missing=True)
    assert catalog.list_sources() == []
    assert catalog.list_clips() == []
