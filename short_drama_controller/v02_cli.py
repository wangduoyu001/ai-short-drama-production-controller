from __future__ import annotations

import argparse
from pathlib import Path

from .v02_assets import extract_assets
from .v02_dialogue import extract_dialogue
from .v02_io import read_project, write_project, write_text
from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_qa import summary, validate
from .v02_storyboard import build_shots


def init_project(input_path: Path, out_dir: Path, title: str | None) -> None:
    text = input_path.read_text(encoding="utf-8").strip()
    project = Project({
        "project_name 项目名": title or "untitled_short_drama 未命名短剧",
        "skill_version 技能版本": "0.2.0",
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


def write_outputs(project: Project, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_project(out_dir / "project.yaml", project.data)
    write_text(out_dir / "storyboard.md", render_storyboard(project))
    write_text(out_dir / "prompts.md", render_prompts(project))
    qa = summary(validate(project))
    write_text(out_dir / "qa.md", render_qa(qa))


def render_storyboard(project: Project) -> str:
    lines = ["# storyboard 分镜"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}")
        for key, value in shot.items():
            lines.append(f"- {key}：{value}")
    return "\n".join(lines)


def render_prompts(project: Project) -> str:
    lines = ["# prompts 提示词"]
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
    lines = ["# qa_report 质检报告", f"qa_status 质检状态：{qa['qa_status 质检状态']}", f"blocker_count 阻塞问题数：{qa['blocker_count 阻塞问题数']}", f"warning_count 警告问题数：{qa['warning_count 警告问题数']}"]
    for issue in qa["issues 问题列表"]:
        lines.append(f"- {issue}")
    return "\n".join(lines)


def cmd_init(args: argparse.Namespace) -> None:
    init_project(Path(args.input), Path(args.out), args.title)
    print(f"v02_project 已创建: {args.out}")


def cmd_qa(args: argparse.Namespace) -> None:
    project = load(Path(args.project))
    qa = summary(validate(project))
    write_text(Path(args.project) / "qa.md", render_qa(qa))
    print(qa)


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
