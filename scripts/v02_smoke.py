from __future__ import annotations

import shutil
from pathlib import Path

from short_drama_controller.v02_cli import init_project, load, save
from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_full_cli import build_project, render_single_prompt
from short_drama_controller.v02_quality import summary, validate
from short_drama_controller.v02_repair import repair_project


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "tmp_v02_smoke"
    if out_dir.exists():
        shutil.rmtree(out_dir)

    init_project(root / "examples" / "input_script.md", out_dir, "v02_smoke")
    project = load(out_dir)
    before = summary(validate(project))
    if before["qa_status 质检状态"] == "BLOCKER":
        project = repair_project(project)
        save(project, out_dir)

    project = load(out_dir)
    after = summary(validate(project))
    if after["qa_status 质检状态"] == "BLOCKER":
        raise SystemExit(f"v02 smoke failed: {after}")

    export_project(project, out_dir)
    required = [
        out_dir / "project.yaml",
        out_dir / "script.md",
        out_dir / "assets.md",
        out_dir / "storyboard.md",
        out_dir / "producer.md",
        out_dir / "sound.md",
        out_dir / "prompts.md",
        out_dir / "qa.md",
        out_dir / "exports" / "video_prompts.md",
        out_dir / "exports" / "grid_prompts.md",
        out_dir / "exports" / "shot_table.csv",
        out_dir / "exports" / "sound_table.csv",
        out_dir / "exports" / "producer_table.csv",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(f"missing output files: {missing}")

    storyboard = (out_dir / "storyboard.md").read_text(encoding="utf-8")
    must_contain = [
        "storyboard_grid_ascii 分镜总览简笔图",
        "dialogue_coverage_ascii 对白覆盖图",
        "sketch_ascii 简笔手绘图",
        "movement_arrow 运动箭头",
        "camera_arrow 镜头箭头",
        "source_text_ref 原文引用位置",
        "evidence_quote 原文证据句",
        "invented_flag 是否AI补充",
    ]
    missing_text = [item for item in must_contain if item not in storyboard]
    if missing_text:
        raise SystemExit(f"storyboard missing required text: {missing_text}")

    project_text = (out_dir / "project.yaml").read_text(encoding="utf-8")
    if "approval_gates 确认闸门" not in project_text:
        raise SystemExit("project.yaml missing approval_gates 确认闸门")

    single = build_project("夜色中的破庙里，少年握着断刀，背对门口。他低声说：你终于来了。", "single_prompt_smoke")
    prompt_text = render_single_prompt(single.shots[0])
    for item in ["image_prompt 图片提示词", "video_prompt 视频提示词", "sound_prompt 声音提示词", "negative_prompt 负面提示词", "fallback_prompt 备用提示词"]:
        if item not in prompt_text:
            raise SystemExit(f"single prompt missing: {item}")

    forbidden = ["final", "fixed", "new", "最终版", "修复记录", "优化建议"]
    bad_files = [p.name for p in out_dir.rglob("*") if p.is_file() and any(x in p.name for x in forbidden)]
    if bad_files:
        raise SystemExit(f"forbidden output files: {bad_files}")

    print("v02 smoke PASS")


if __name__ == "__main__":
    main()
