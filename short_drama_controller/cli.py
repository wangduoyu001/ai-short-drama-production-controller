from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

from .director_system import build_default_director_graph, build_default_provider_registry, default_agent_team
from .v06_manager_sync import sync_production_plan
from .v06_unified_workflow import load_workflow_state, run_unified_workflow
from .version import MAIN_COMMAND, PACKAGE_VERSION


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


def cmd_run(args: argparse.Namespace) -> None:
    project_dir = Path(args.out)
    result = run_unified_workflow(
        Path(args.input),
        project_dir,
        title=args.title,
        resume=args.resume,
    )
    receipt = _manager_receipt(args, project_dir)
    print(
        json.dumps(
            {
                "workflow_id 工作流编号": result.workflow_id,
                "status 状态": result.status,
                "project_dir 项目目录": str(result.project_dir),
                "state_path 状态文件": str(result.state_path),
                "task_count 任务总数": result.task_count,
                "pending_external_tasks 待外部执行任务": result.pending_external_tasks,
                "manager_import 管理器导入": receipt,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def cmd_status(args: argparse.Namespace) -> None:
    print(json.dumps(load_workflow_state(Path(args.project)), ensure_ascii=False, indent=2))


def cmd_sync(args: argparse.Namespace) -> None:
    receipt = sync_production_plan(
        Path(args.project),
        args.manager_url,
        manager_project_id=args.manager_project_id,
        timeout_seconds=args.manager_timeout,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def cmd_graph_template(args: argparse.Namespace) -> None:
    payload = {
        "version": PACKAGE_VERSION,
        "graph": build_default_director_graph().to_dict(),
        "agents": [
            {
                "role": item.role.value,
                "objective": item.objective,
                "inputs": list(item.inputs),
                "outputs": list(item.outputs),
                "can_block": item.can_block,
            }
            for item in default_agent_team()
        ],
        "providers": build_default_provider_registry().to_dict(),
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output)
        return
    print(text, end="")


def cmd_doctor(_: argparse.Namespace) -> None:
    root = Path(__file__).resolve().parents[1]
    checks = {
        "python_supported": sys.version_info >= (3, 10),
        "pyproject_exists": (root / "pyproject.toml").is_file(),
        "workflow_contract_exists": (root / "workflows" / "novel_to_drama.v1.json").is_file(),
        "examples_exist": (root / "examples").is_dir(),
    }
    payload = {
        "version": PACKAGE_VERSION,
        "python": platform.python_version(),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "BLOCKER",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if payload["status"] != "PASS":
        raise SystemExit(1)


def _add_manager_options(parser: argparse.ArgumentParser, *, required: bool) -> None:
    parser.add_argument(
        "--manager-url",
        required=required,
        help="loopback manager URL, for example http://127.0.0.1:8000",
    )
    parser.add_argument("--manager-project-id")
    parser.add_argument("--manager-timeout", type=float, default=10.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=MAIN_COMMAND)
    parser.add_argument("--version", action="version", version=PACKAGE_VERSION)
    sub = parser.add_subparsers(required=True)

    run = sub.add_parser("run", aliases=["run-all"], help="generate the complete production plan")
    run.add_argument("--input", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--title")
    run.add_argument("--resume", action="store_true")
    _add_manager_options(run, required=False)
    run.set_defaults(func=cmd_run)

    status = sub.add_parser("status", aliases=["workflow-status"], help="show workflow state")
    status.add_argument("--project", required=True)
    status.set_defaults(func=cmd_status)

    sync = sub.add_parser("sync", aliases=["sync-plan"], help="import a plan into the local manager")
    sync.add_argument("--project", required=True)
    _add_manager_options(sync, required=True)
    sync.set_defaults(func=cmd_sync)

    graph = sub.add_parser("graph-template", help="print or save the director graph contract")
    graph.add_argument("--out")
    graph.set_defaults(func=cmd_graph_template)

    doctor = sub.add_parser("doctor", help="run deterministic local checks")
    doctor.set_defaults(func=cmd_doctor)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
