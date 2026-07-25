from __future__ import annotations

import argparse
import json
from pathlib import Path

from .v02_full_cli import cmd_doctor
from .v06_manager_sync import sync_production_plan
from .v06_unified_workflow import load_workflow_state, run_unified_workflow


def _manager_receipt(args: argparse.Namespace, project_dir: Path) -> dict | None:
    if args.manager_project_id and not args.manager_url:
        raise SystemExit("--manager-project-id requires --manager-url")
    if not args.manager_url:
        return None
    return sync_production_plan(
        project_dir,
        args.manager_url,
        manager_project_id=args.manager_project_id,
        timeout_seconds=args.manager_timeout,
    )


def cmd_run_all(args: argparse.Namespace) -> None:
    project_dir = Path(args.out)
    result = run_unified_workflow(
        Path(args.input),
        project_dir,
        title=args.title,
        resume=args.resume,
    )
    receipt = _manager_receipt(args, project_dir)
    print(json.dumps({
        "workflow_id 工作流编号": result.workflow_id,
        "status 状态": result.status,
        "project_dir 项目目录": str(result.project_dir),
        "state_path 状态文件": str(result.state_path),
        "task_count 任务总数": result.task_count,
        "pending_external_tasks 待外部执行任务": result.pending_external_tasks,
        "manager_import 管理器导入": receipt,
        "execution_note 执行说明": (
            "已生成生产任务清单"
            + ("并导入本机 Comfy Cloud Manager" if receipt else "")
            + "；未调用模型、未提交 ComfyUI /prompt、未启动 GPU、未产生推理费用。"
        ),
    }, ensure_ascii=False, indent=2))


def cmd_sync_plan(args: argparse.Namespace) -> None:
    receipt = sync_production_plan(
        Path(args.project),
        args.manager_url,
        manager_project_id=args.manager_project_id,
        timeout_seconds=args.manager_timeout,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def cmd_workflow_status(args: argparse.Namespace) -> None:
    print(json.dumps(load_workflow_state(Path(args.project)), ensure_ascii=False, indent=2))


def _add_manager_options(parser: argparse.ArgumentParser, *, optional_url: bool) -> None:
    parser.add_argument(
        "--manager-url",
        required=not optional_url,
        help="loopback Comfy Cloud Manager URL, for example http://127.0.0.1:8000",
    )
    parser.add_argument("--manager-project-id", help="optional prj_... project binding in Comfy Cloud Manager")
    parser.add_argument("--manager-timeout", type=float, default=10.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="short-drama-controller-v06")
    sub = parser.add_subparsers(required=True)

    run_all = sub.add_parser("run-all")
    run_all.add_argument("--input", required=True)
    run_all.add_argument("--out", required=True)
    run_all.add_argument("--title")
    run_all.add_argument("--resume", action="store_true", help="skip completed local stages")
    _add_manager_options(run_all, optional_url=True)
    run_all.set_defaults(func=cmd_run_all)

    sync_plan = sub.add_parser("sync-plan")
    sync_plan.add_argument("--project", required=True)
    _add_manager_options(sync_plan, optional_url=False)
    sync_plan.set_defaults(func=cmd_sync_plan)

    status = sub.add_parser("workflow-status")
    status.add_argument("--project", required=True)
    status.set_defaults(func=cmd_workflow_status)

    doctor = sub.add_parser("doctor")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
