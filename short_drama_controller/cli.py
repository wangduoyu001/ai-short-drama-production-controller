from __future__ import annotations

import argparse
from pathlib import Path

from .core import create_project_from_input, write_project_files
from .exporters import export_project
from .project_io import load_project
from .repair import repair_project
from .validators import qa_summary, validate_project
from .yaml_io import write_text


def cmd_init(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    out_dir = Path(args.out)
    text = input_path.read_text(encoding="utf-8")
    project = create_project_from_input(text, title=args.title)
    write_project_files(project, out_dir)
    print(f"created_project 已创建项目: {out_dir}")


def cmd_qa(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = load_project(project_dir)
    issues = validate_project(project)
    summary = qa_summary(issues)
    write_text(project_dir / "qa.md", render_qa(summary))
    print(f"qa_status 质检状态: {summary['qa_status 质检状态']}")
    print(f"blocker_count 阻塞问题数: {summary['blocker_count 阻塞问题数']}")
    print(f"warning_count 警告问题数: {summary['warning_count 警告问题数']}")


def cmd_repair(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = load_project(project_dir)
    repair_project(project)
    write_project_files(project, project_dir)
    issues = validate_project(project)
    summary = qa_summary(issues)
    write_text(project_dir / "qa.md", render_qa(summary, repaired=True))
    print(f"repair_replace 返修替换完成: {project_dir}")
    print(f"qa_status 质检状态: {summary['qa_status 质检状态']}")


def cmd_export(args: argparse.Namespace) -> None:
    project_dir = Path(args.project)
    project = load_project(project_dir)
    export_project(project, project_dir)
    print(f"export_pack 平台导出完成: {project_dir / 'exports'}")


def render_qa(summary: dict, repaired: bool = False) -> str:
    lines = ["# qa_report 质检报告\n"]
    lines.append(f"qa_status 质检状态：{summary['qa_status 质检状态']}")
    lines.append(f"blocker_count 阻塞问题数：{summary['blocker_count 阻塞问题数']}")
    lines.append(f"warning_count 警告问题数：{summary['warning_count 警告问题数']}")
    if repaired:
        lines.append("repair_replace 返修替换：已执行自动返修并覆盖目标文件。")
    lines.append("\n## issues 问题列表\n")
    for issue in summary["issues 问题列表"]:
        lines.append(f"- {issue['level 等级']} | {issue['code 代码']} | {issue['message 信息']} | {issue['repair_action 返修动作']}")
    if not summary["issues 问题列表"]:
        lines.append("- PASS | no_issue | 当前未发现阻塞问题 | 无需返修")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="short-drama-controller")
    sub = parser.add_subparsers(required=True)
    p_init = sub.add_parser("init", help="create project from input")
    p_init.add_argument("--input", required=True)
    p_init.add_argument("--out", required=True)
    p_init.add_argument("--title", default=None)
    p_init.set_defaults(func=cmd_init)
    p_qa = sub.add_parser("qa", help="run QA gate")
    p_qa.add_argument("--project", required=True)
    p_qa.set_defaults(func=cmd_qa)
    p_repair = sub.add_parser("repair", help="repair and replace project files")
    p_repair.add_argument("--project", required=True)
    p_repair.set_defaults(func=cmd_repair)
    p_export = sub.add_parser("export", help="export platform prompts and edit tables")
    p_export.add_argument("--project", required=True)
    p_export.set_defaults(func=cmd_export)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
