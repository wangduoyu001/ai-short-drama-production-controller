from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .v02_assets import extract_assets
from .v02_dialogue import extract_dialogue
from .v02_exporters import export_project
from .v02_io import read_project, write_project, write_text
from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_quality import summary, validate
from .v02_repair import repair_project
from .v02_storyboard import build_shots


def init_project(input_path: Path, out_dir: Path, title: str | None) -> None:
    text = input_path.read_text(encoding="utf-8").strip()
    project = Project({
        "project_name 项目名": title or "untitled_short_drama 未命名短剧",
        "skill_version 技能版本": "0.2.3",
        "source_text 原文": text,
        "scope_gate 范围闸门": {
            "production_mode 制作模式": "fast_demo 快速样片模式",
            "reduced_scope 压缩后范围": "60-90秒，8-12镜，2-3人，1个主场景，正反打对白优先。",
        },
        "dialogue_lines 对白列表": extract_dialogue(text),
        **extract_assets(text),
    })
    build_shots(project)
    attach_sound_and_prompts(project)
    write_outputs(project, out_dir)


def load(out_dir: Path) -> Project:
    return Project(read_project(out_dir / "project.yaml"))


def save(project: Project, out_dir: Path) -> None:
    write_outputs(project, out_dir)


def write_outputs(project: Project, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_project(out_dir / "project.yaml", project.data)
    write_text(out_dir / "script.md", render_script(project))
    write_text(out_dir / "assets.md", render_assets(project))
    write_text(out_dir / "storyboard.md", render_storyboard(project))
    write_text(out_dir / "producer.md", render_producer(project))
    write_text(out_dir / "sound.md", render_sound(project))
    write_text(out_dir / "prompts.md", render_prompts(project))
    qa = summary(validate(project))
    write_text(out_dir / "qa.md", render_qa(qa))


def render_script(project: Project) -> str:
    lines = ["# script 剧本拆解文档", "", "## source_text 原文", project.data.get("source_text 原文", "")]
    lines.append("\n## dialogue_lines 对白列表")
    for item in project.data.get("dialogue_lines 对白列表", []):
        lines.append(f"- speaker 说话人：{item.get('speaker_name 说话人', '未知')} | dialogue 出口对白：{item.get('dialogue_line 出口对白', '无')} | os 画外音：{item.get('os_line 画外音', '无')}")
    lines.append("\n## source_coverage 原文覆盖说明")
    lines.append("原文必须保留在 project.yaml / 项目总控数据 与本 script.md / 剧本拆解文档中；返修时直接覆盖本文件，不生成副本。")
    return "\n".join(lines)


def render_assets(project: Project) -> str:
    lines = ["# assets 资产锁定文档"]
    lines.append("\n## characters 角色资产")
    for char in project.characters:
        lines.append(render_dict_block(char))
    lines.append("\n## scenes 场景资产")
    for scene in project.scenes:
        lines.append(render_dict_block(scene))
    lines.append("\n## props 道具资产")
    for prop in project.props:
        lines.append(render_dict_block(prop))
    lines.append("\n## asset_rule 资产规则")
    lines.append("角色、场景、道具只在本文件锁定；修改后直接覆盖本文件，不生成 assets_new.md / assets_final.md。")
    return "\n".join(lines)


def render_storyboard(project: Project) -> str:
    lines = ["# storyboard 分镜执行文档"]
    lines += render_code_block("storyboard_grid_ascii 分镜总览简笔图", project.data.get("storyboard_grid_ascii 分镜总览简笔图", "缺少分镜总览简笔图"))
    dialogue_grid = project.data.get("dialogue_coverage_ascii 对白覆盖图", "")
    if dialogue_grid:
        lines += render_code_block("dialogue_coverage_ascii 对白覆盖图", dialogue_grid)
    director_read = project.data.get("director_read 导演读本", {})
    if director_read:
        lines.append("\n## director_read 导演读本")
        lines.append(render_dict_block(director_read))
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}")
        lines += render_code_block("sketch_ascii 简笔手绘图", shot.get("sketch_ascii 简笔手绘图", "缺少单镜头简笔手绘图"), level="###")
        motion_grid = shot.get("motion_grid_ascii 动作拆解六宫格", "")
        if motion_grid:
            lines += render_code_block("motion_grid_ascii 动作拆解六宫格", motion_grid, level="###")
        for key, value in shot.items():
            if key in {"sketch_ascii 简笔手绘图", "motion_grid_ascii 动作拆解六宫格"}:
                continue
            lines.append(f"- {key}：{value}")
    return "\n".join(lines)


def render_producer(project: Project) -> str:
    lines = ["# producer 制片执行文档"]
    lines.append("\n## producer_plan 制片执行计划")
    lines.append(render_dict_block(project.data.get("producer_plan 制片执行计划", {})))
    lines.append("\n## project_state_capsule 项目状态胶囊")
    lines.append(render_dict_block(project.data.get("project_state_capsule 项目状态胶囊", {})))
    lines.append("\n## clip_contracts 单段镜头合同")
    for shot in project.shots:
        lines.append(f"- {shot.get('shot_id 镜头编号')} / {shot.get('clip_id 单段编号')}：本段只拍={shot.get('this_clip_only 本段只拍')}；后续保留={shot.get('reserved_for_later 后续保留')}；计划结束={shot.get('planned_end_state 计划结束状态')}；实际结尾={shot.get('observed_end_state 实际生成结尾状态')}")
    lines.append("\n## retake_rule 返修规则")
    lines.append("每次返修只改一个变量，例如镜头、动作、光线、对白、声音、参考图之一；修完直接覆盖旧文件。")
    return "\n".join(lines)


def render_sound(project: Project) -> str:
    lines = ["# sound 声音设计文档"]
    lines.append("\n## sound_plan 声音设计计划")
    lines.append(render_dict_block(project.data.get("sound_plan 声音设计计划", {})))
    lines.append("\n## sound_by_shot 分镜声音表")
    for shot in project.shots:
        lines.append(f"\n### {shot['shot_id 镜头编号']}")
        for key in [
            "speaker_mode 发声模式", "mouth_state 嘴型状态", "dialogue_line 出口对白", "os_line 画外音",
            "ambience_sfx 环境底音", "foley_sfx 拟音", "prop_sfx 道具音", "action_sfx 动作音", "music_note 音乐建议", "silence_note 静默说明",
        ]:
            lines.append(f"- {key}：{shot.get(key, '')}")
    return "\n".join(lines)


def render_prompts(project: Project) -> str:
    lines = ["# prompts 生成提示词文档"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']}")
        lines.append("### image_prompt 图片提示词")
        lines.append(shot["image_prompt 图片提示词"])
        lines.append("### video_prompt 视频提示词")
        lines.append(shot["video_prompt 视频提示词"])
        if shot.get("grid_prompt 宫格提示词"):
            lines.append("### grid_prompt 宫格提示词")
            lines.append(shot["grid_prompt 宫格提示词"])
    return "\n".join(lines)


def render_qa(qa: dict) -> str:
    lines = [
        "# qa_report 质检返修文档",
        f"qa_status 质检状态：{qa['qa_status 质检状态']}",
        f"blocker_count 阻塞问题数：{qa['blocker_count 阻塞问题数']}",
        f"warning_count 警告问题数：{qa['warning_count 警告问题数']}",
    ]
    for issue in qa["issues 问题列表"]:
        lines.append(f"- {issue}")
    lines.append("\n## overwrite_rule 覆盖规则")
    lines.append("返修后直接覆盖旧文档，禁止生成 qa_final.md / prompts_v2.md / storyboard_fixed.md。")
    return "\n".join(lines)


def render_code_block(title: str, content: object, level: str = "##") -> list[str]:
    fence = "`" * 3
    return [f"\n{level} {title}", f"{fence}text", str(content), fence]


def render_dict_block(data: Any) -> str:
    if isinstance(data, dict):
        return "\n".join(f"- {key}：{value}" for key, value in data.items()) or "- none 无"
    if isinstance(data, list):
        return "\n".join(f"- {value}" for value in data) or "- none 无"
    return f"- {data}"


def cmd_init(args: argparse.Namespace) -> None:
    init_project(Path(args.input), Path(args.out), args.title)
    print(f"v02_project 已创建: {args.out}")


def cmd_qa(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = load(project_dir)
    qa = summary(validate(project))
    write_text(project_dir / "qa.md", render_qa(qa))
    print(qa)


def cmd_repair(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = repair_project(load(project_dir))
    save(project, project_dir)
    print(f"v02_repair 返修替换完成: {project_dir}")


def cmd_export(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = load(project_dir)
    export_project(project, project_dir)
    print(f"v02_export 导出完成: {project_dir / 'exports'}")


def cmd_grid(args: argparse.Namespace) -> None:
    project = load(Path(args.project))
    shot = next((x for x in project.shots if x["shot_id 镜头编号"] == args.shot), None)
    if not shot:
        raise SystemExit(f"shot not found: {args.shot}")
    print(shot.get("grid_prompt 宫格提示词") or "该镜头未判定为宫格硬切高风险镜头。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m short_drama_controller.v02_cli")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("init")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("qa")
    p.add_argument("--project", required=True)
    p.set_defaults(func=cmd_qa)

    p = sub.add_parser("repair")
    p.add_argument("--project", required=True)
    p.set_defaults(func=cmd_repair)

    p = sub.add_parser("export")
    p.add_argument("--project", required=True)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("grid")
    p.add_argument("--project", required=True)
    p.add_argument("--shot", required=True)
    p.set_defaults(func=cmd_grid)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
