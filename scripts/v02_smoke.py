from __future__ import annotations

import shutil
from pathlib import Path

from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_full_cli import build_project, load_project, render_single_prompt, save_project
from short_drama_controller.v02_quality import summary, validate
from short_drama_controller.v02_repair import repair_project


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "tmp_v02_smoke"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    text = (root / "examples" / "input_script.md").read_text(encoding="utf-8")
    save_project(build_project(text, "v04_smoke"), out_dir)

    project = load_project(out_dir)
    before = summary(validate(project))
    if before["qa_status 质检状态"] == "BLOCKER":
        save_project(repair_project(project), out_dir)

    project = load_project(out_dir)
    after = summary(validate(project))
    if after["qa_status 质检状态"] == "BLOCKER":
        raise SystemExit(f"smoke failed: {after}")

    export_project(project, out_dir)

    required = [
        "project.yaml",
        "script.md",
        "chapter_intake.md",
        "bible.md",
        "characters.md",
        "three_views.md",
        "style.md",
        "scene_plan.md",
        "assets.md",
        "storyboard.md",
        "producer.md",
        "sound.md",
        "prompts.md",
        "qa.md",
        "exports/first_frame_prompts.md",
        "exports/image_prompts.md",
        "exports/video_prompts.md",
        "exports/end_frame_prompts.md",
        "exports/negative_prompts.md",
        "exports/fallback_shots.md",
        "exports/grid_prompts.md",
        "exports/shot_table.csv",
        "exports/sound_table.csv",
        "exports/producer_table.csv",
        "exports/action_table.csv",
        "exports/shot_inference_table.csv",
    ]
    missing = [name for name in required if not (out_dir / name).exists()]
    if missing:
        raise SystemExit(f"missing output files: {missing}")

    project_text = (out_dir / "project.yaml").read_text(encoding="utf-8")
    for text_item in [
        "source_segments 原文切片",
        "source_coverage 原文覆盖",
        "chapter_intake 章节解析",
        "story_bible 世界观圣经",
        "character_cards 角色卡",
        "three_view_prompts 三视图提示词",
        "scene_plan 场景计划",
        "asset_lock 资产锁定",
        "event_blocks 事件段落拆分",
        "drama_structure 短剧结构",
        "shot_inference 单镜推理",
        "first_frame_prompt 首帧提示词",
        "end_frame_prompt 尾帧提示词",
    ]:
        if text_item not in project_text:
            raise SystemExit(f"project.yaml missing: {text_item}")

    single = build_project("夜里，少年站在门口说：你终于来了。", "single_prompt_smoke")
    prompt_text = render_single_prompt(single.shots[0])
    for text_item in ["first_frame_prompt 首帧提示词", "image_prompt 图片提示词", "video_prompt 视频提示词", "end_frame_prompt 尾帧提示词", "sound_prompt 声音提示词", "negative_prompt 负面提示词", "fallback_prompt 备用提示词"]:
        if text_item not in prompt_text:
            raise SystemExit(f"single prompt missing: {text_item}")

    print("v04 smoke PASS")


if __name__ == "__main__":
    main()
