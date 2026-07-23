from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from short_drama_controller.script_mixer.config import RuntimeConfig
from short_drama_controller.script_mixer.jianying_draft import (
    create_jianying_draft,
    discover_jianying_draft_roots,
)


class FakeSegment:
    def __init__(self, path, target_timerange, source_timerange=None):
        self.path = path
        self.target_timerange = target_timerange
        self.source_timerange = source_timerange
        self.keyframes = []

    def add_keyframe(self, *args):
        self.keyframes.append(args)
        return self


class FakeScript:
    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height
        self.tracks = []
        self.segments = []
        self.subtitles = []
        self.saved = False

    def add_track(self, track_type, track_name=None, relative_index=0):
        self.tracks.append((track_type, track_name, relative_index))
        return self

    def add_segment(self, segment, track_name=None):
        self.segments.append((track_name, segment))
        return self

    def import_srt(self, path, track_name=None):
        self.subtitles.append((track_name, path))

    def save(self):
        self.saved = True


class FakeDraftFolder:
    latest_script = None

    def __init__(self, root):
        self.root = root

    def create_draft(self, name, width, height):
        script = FakeScript(name, width, height)
        FakeDraftFolder.latest_script = script
        return script


def _fake_module():
    return SimpleNamespace(
        DraftFolder=FakeDraftFolder,
        TrackType=SimpleNamespace(video="video", audio="audio"),
        VideoSegment=FakeSegment,
        AudioSegment=FakeSegment,
        trange=lambda start, duration: (start, duration),
    )


def test_discover_configured_draft_root(tmp_path: Path) -> None:
    root = tmp_path / "JianyingPro Drafts"
    root.mkdir()
    result = discover_jianying_draft_roots(root)
    assert result == [root.resolve()]


def test_create_jianying_draft_places_video_audio_narration_and_subtitles(
    tmp_path: Path,
) -> None:
    root = tmp_path / "JianyingPro Drafts"
    root.mkdir()
    video = tmp_path / "package" / "video" / "S001.mp4"
    source_audio = tmp_path / "package" / "audio" / "S001_source.wav"
    narration = tmp_path / "package" / "audio" / "narration.wav"
    subtitle = tmp_path / "package" / "subtitles" / "captions.srt"
    for path in (video, source_audio, narration, subtitle):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"asset")
    config = RuntimeConfig()
    config.edit_package.jianying_draft_root = str(root)
    manifest = {
        "project_id": "demo",
        "timeline": {"width": 1080, "height": 1920, "duration": 3.0},
        "audio_mode": "mixed",
        "segments": [
            {
                "segment_id": "S001",
                "proxy_video_path": str(video),
                "source_audio_path": str(source_audio),
                "timeline_start": 0.0,
                "timeline_duration": 3.0,
                "selected_in": 1.0,
                "selected_duration": 3.0,
            }
        ],
        "narration": {"output_path": str(narration)},
        "subtitles": {"srt": str(subtitle)},
    }
    result = create_jianying_draft(
        manifest,
        config,
        draft_module=_fake_module(),
    )
    script = FakeDraftFolder.latest_script
    assert result["created"] is True
    assert result["subtitle_imported"] is True
    assert script is not None and script.saved is True
    assert script.width == 1080
    assert script.height == 1920
    assert [track[1] for track in script.tracks] == ["AI粗剪视频", "原声", "配音"]
    assert len(script.segments) == 3
    video_track, video_segment = script.segments[0]
    assert video_track == "AI粗剪视频"
    assert video_segment.target_timerange == ("0.000000s", "3.000000s")
    assert video_segment.source_timerange == ("1.000000s", "3.000000s")
    source_track, source_segment = script.segments[1]
    assert source_track == "原声"
    assert source_segment.keyframes[0][1] == config.audio.mixed_source_volume
    narration_track, narration_segment = script.segments[2]
    assert narration_track == "配音"
    assert narration_segment.keyframes[0][1] == config.audio.narration_volume
    assert script.subtitles == [("字幕", str(subtitle.resolve()))]
