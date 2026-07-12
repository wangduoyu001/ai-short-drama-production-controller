from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from short_drama_controller.v02_action_contract import ensure_action_contract
from short_drama_controller.v02_asset_expand import expand_project_assets
from short_drama_controller.v02_batch_inference import attach_batch_inference
from short_drama_controller.v02_coverage_qa import attach_coverage_qa
from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_full_cli import build_project, load_project, render_single_prompt, save_project
from short_drama_controller.v02_grid_strategy import attach_grid_strategy
from short_drama_controller.v02_preproduction import build_action_choreography, build_preproduction
from short_drama_controller.v02_qa_gate import evaluate
from short_drama_controller.v02_repair import repair_project
from short_drama_controller.v02_shot_bindings import attach_required_shot_bindings
from short_drama_controller.v02_shot_inference import attach_shot_inference
from short_drama_controller.v02_source_segments import attach_source_coverage


def run_smoke(out_dir: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "examples" / "input_script.md").read_text(encoding="utf-8")
    save_project(build_project(text, "v05_smoke"), out_dir)

    project = load_project(out_dir)
    before = evaluate(project)
    if before["qa_status 质检状态"] == "BLOCKER":
        save_project(repair_full_project(project), out_dir)

    project = load_project(out_dir)
    after = evaluate(project)
    if after["qa_status 质检状态"] == "BLOCKER":
        raise SystemExit(f"smoke failed: {after}")

    export_project(project, out_dir)

    required = [
        "project.yaml",
        "script.md",
        "chapter_intake.md",
        "story_events.md",
        "bible.md",
        "world_bible.md",
        "style_bible.md",
        "characters.md",
        "three_views.md",
        "style.md",
        "scene_plan.md",
        "coverage_qa.md",
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
        "exports/batch_inference.md",
        "exports/shot_table.csv",
        "exports/sound_table.csv",
        "exports/producer_table.csv",
        "exports/action_table.csv",
        "exports/shot_inference_table.csv",
        "exports/batch_inference_table.csv",
        "exports/grid_strategy_table.csv",
    ]
    missing = [name for name in required if not (out_dir / name).exists()]
    if missing:
        raise SystemExit(f"missing output files: {missing}")
    if (out_dir / "exports" / "v02_video_prompts.md").exists():
        raise SystemExit("mixed export filename: v02_video_prompts.md must not be generated")

    project_text = (out_dir / "project.yaml").read_text(encoding="utf-8")
    for text_item in [
        "source_segments 原文切片",
        "source_coverage 原文覆盖",
        "coverage_qa 关键实体覆盖QA",
        "chapter_intake 章节解析",
        "story_events 事件链",
        "world_bible 世界观",
        "style_bible 风格圣经",
        "story_bible 世界观圣经",
        "character_cards 角色卡",
        "three_view_prompts 三视图提示词",
        "scene_plan 场景计划",
        "asset_lock 资产锁定",
        "event_blocks 事件段落拆分",
        "drama_structure 短剧结构",
        "beat_map 剧情节拍表",
        "shot_plan 分镜计划",
        "shot_inference 单镜推理",
        "batch_inference 批量推理",
        "grid_strategy 宫格策略",
        "first_frame_prompt 首帧提示词",
        "end_frame_prompt 尾帧提示词",
    ]:
        if text_item not in project_text:
            raise SystemExit(f"project.yaml missing: {text_item}")
    qa_text = (out_dir / "qa.md").read_text(encoding="utf-8")
    if "allow_export 允许导出" not in qa_text:
        raise SystemExit("qa.md missing allow_export 允许导出")

    single = build_project("夜里，少年站在门口说：你终于来了。", "single_prompt_smoke")
    prompt_text = render_single_prompt(single.shots[0])
    for text_item in ["event_id 事件编号", "scene_id 场景编号", "character_id 角色编号", "prop_id 道具编号", "first_frame_prompt 首帧提示词", "image_prompt 图片提示词", "video_prompt 视频提示词", "end_frame_prompt 尾帧提示词", "sound_prompt 声音提示词", "negative_prompt 负面提示词", "fallback_prompt 备用提示词"]:
        if text_item not in prompt_text:
            raise SystemExit(f"single prompt missing: {text_item}")

    print("v05 smoke PASS")


def repair_full_project(project):
    project = repair_project(project)
    expand_project_assets(project)
    build_preproduction(project)
    attach_required_shot_bindings(project)
    attach_grid_strategy(project)
    attach_shot_inference(project)
    attach_batch_inference(project)
    build_action_choreography(project)
    ensure_action_contract(project)
    attach_source_coverage(project)
    attach_coverage_qa(project)
    return project


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", help="optional output directory; default uses a temporary directory")
    args = parser.parse_args()
    if args.out:
        run_smoke(Path(args.out))
        return
    with tempfile.TemporaryDirectory(prefix="v02_smoke_") as tmp:
        run_smoke(Path(tmp))


if __name__ == "__main__":
    main()
