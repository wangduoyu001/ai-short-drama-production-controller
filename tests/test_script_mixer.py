from __future__ import annotations

from pathlib import Path

from short_drama_controller.script_mixer.catalog import MediaCatalog
from short_drama_controller.script_mixer.config import MixingRules
from short_drama_controller.script_mixer.intent import build_visual_intents
from short_drama_controller.script_mixer.models import MediaClip
from short_drama_controller.script_mixer.planner import plan_timeline
from short_drama_controller.script_mixer.render import build_ffmpeg_command
from short_drama_controller.script_mixer.retrieval import HybridRetriever
from short_drama_controller.script_mixer.script_parser import build_script_units, split_script


def _clip(index: int) -> MediaClip:
    return MediaClip(
        clip_id=f"C{index:03d}",
        source_id=f"SRC{index:03d}",
        source_path=f"D:/media/source_{index:03d}.mp4",
        source_start=1.0,
        source_end=6.0,
        duration=5.0,
        description="人物使用手机和电脑制作短视频，工作、自动化、效率",
        tags=["自媒体", "手机", "电脑", "工作", "系统", "效率"],
        emotions=["专注", "希望"],
        shot_type="中景",
        width=1080,
        height=1920,
        quality_score=0.9,
    )


def test_script_split_and_duration_scaling() -> None:
    text = "很多人做自媒体很努力。但是每天都在重复低价值工作。真正需要的是可复用的内容系统。"
    parts = split_script(text, max_chars=18)
    assert len(parts) >= 3
    units = build_script_units(text, target_duration=30.0)
    assert round(units[-1].end, 2) == 30.0
    assert units[0].role == "hook"
    assert units[-1].role == "conclusion"


def test_catalog_roundtrip(tmp_path: Path) -> None:
    catalog = MediaCatalog(tmp_path / "media.db")
    catalog.initialize()
    catalog.upsert_clip(_clip(1))
    clips = catalog.list_clips()
    assert len(clips) == 1
    assert clips[0].clip_id == "C001"
    assert "自媒体" in clips[0].tags


def test_retrieval_and_diverse_timeline() -> None:
    script = "。".join(
        [
            "很多人做自媒体",
            "每天都很努力",
            "却在重复工作",
            "失败并不是偶然",
            "问题在于没有系统",
            "真正的机会来自流程",
            "把工作交给自动化",
            "把经验变成模板",
            "让内容持续复用",
            "最后获得稳定增长",
        ]
    ) + "。"
    units = build_script_units(script, target_duration=30.0)
    intents = build_visual_intents(units)
    clips = [_clip(index) for index in range(1, 15)]
    retriever = HybridRetriever()
    candidates = {intent.unit_id: retriever.retrieve(intent, clips) for intent in intents}
    timeline = plan_timeline(
        project_id="test_project",
        units=units,
        intents=intents,
        candidates_by_unit=candidates,
        rules=MixingRules(),
    )
    assert round(timeline.duration, 2) == 30.0
    assert len({segment.source_id for segment in timeline.segments}) >= 8
    assert all(
        left.source_id != right.source_id
        for left, right in zip(timeline.segments, timeline.segments[1:])
    )


def test_ffmpeg_command_contains_concat() -> None:
    script = "输入文案以后匹配本地画面。最后生成三十秒混剪视频。"
    units = build_script_units(script, target_duration=6.0)
    intents = build_visual_intents(units)
    clips = [_clip(index) for index in range(1, 10)]
    retriever = HybridRetriever()
    candidates = {intent.unit_id: retriever.retrieve(intent, clips) for intent in intents}
    rules = MixingRules(minimum_source_count=2, max_single_source_ratio=0.6)
    timeline = plan_timeline("render_test", units, intents, candidates, rules)
    command = build_ffmpeg_command(timeline, "ffmpeg", "output.mp4")
    joined = " ".join(command)
    assert "filter_complex" in joined
    assert "concat=n=" in joined
    assert command[-1] == "output.mp4"
