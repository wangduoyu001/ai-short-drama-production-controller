from __future__ import annotations

import argparse
from pathlib import Path

from .v02_assets import extract_assets
from .v02_dialogue_bind import bind_dialogue_to_characters
from .v02_exporters import export_project
from .v02_io import read_project, write_project, write_text
from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_quality import summary, validate
from .v02_repair import repair_project
from .v02_storyboard import build_shots
from .v02_cli import render_assets, render_producer, render_prompts, render_qa, render_script, render_sound, render_storyboard


def build_project(text: str, title: str | None) -> Project:
    assets = extract_assets(text)
    dialogues = bind_dialogue_to_characters(text, assets["characters 角色列表"])
    project = Project({
        "project_name 项目名": title or "untitled_short_drama 未命名短剧",
        "skill_version 技能版本": "0.2.2",
        "source_text 原文": text,
        "scope_gate 范围闸门": {"production_mode 制作模式": "fast_demo 快速样片模式"},
        "dialogue_lines 对白列表": dialogues,
        **assets,
    })
    build_shots(project)
    attach_sound_and_prompts(project)
    return project


def save_project(project: Project, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_project(out_dir / "project.yaml", project.data)
    write_text(out_dir / "script.md", render_script(project))
    write_text(out_dir / "assets.md", render_assets(project))
    write_text(out_dir / "storyboard.md", render_storyboard(project))
    write_text(out_dir / "producer.md", render_producer(project))
    write_text(out_dir / "sound.md", render_sound(project))
    write_text(out_dir / "prompts.md", render_prompts(project))
    write_text(out_dir / "qa.md", render_qa(summary(validate(project))))


def load_project(project_dir: Path) -> Project:
    return Project(read_project(project_dir / "project.yaml"))


def cmd_init(args: argparse.Namespace) -> None:
    text = Path(args.input).read_text(encoding="utf-8").strip()
    save_project(build_project(text, args.title), Path(args.out))
    print(f"v02_project 已创建: {args.out}")


def cmd_qa(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    qa = summary(validate(load_project(project_dir)))
    write_text(project_dir / "qa.md", render_qa(qa))
    print(qa)


def cmd_repair(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    save_project(repair_project(load_project(project_dir)), project_dir)
    print(f"v02_repair 返修替换完成: {project_dir}")


def cmd_export(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    export_project(load_project(project_dir), project_dir)
    print(f"v02_export 导出完成: {project_dir / 'exports'}")


def cmd_grid(args: argparse.Namespace) -> None:
    shot = next((x for x in load_project(Path(args.project)).shots if x["shot_id 镜头编号"] == args.shot), None)
    if not shot:
        raise SystemExit(f"shot not found: {args.shot}")
    print(shot.get("grid_prompt 宫格提示词") or "该镜头未判定为宫格硬切高风险镜头。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="short-drama-controller-v02")
    sub = parser.add_subparsers(required=True)
    for name, func in [("qa", cmd_qa), ("repair", cmd_repair), ("export", cmd_export)]:
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.set_defaults(func=func)
    p = sub.add_parser("init")
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--title")
    p.set_defaults(func=cmd_init)
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
