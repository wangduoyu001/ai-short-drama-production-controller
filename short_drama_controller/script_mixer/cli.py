from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import MediaCatalog, import_manifest
from .config import load_config, write_default_config
from .pipeline import ScriptMixerPipeline
from .script_parser import load_script


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="script-driven-mixer",
        description="根据输入文案从本地素材库规划多来源混剪时间线。",
    )
    parser.add_argument("--config", help="JSON配置文件路径；未提供时使用空路径默认配置")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_config = subparsers.add_parser("init-config", help="生成不包含本机路径的默认配置")
    init_config.add_argument("--out", default="script_mixer.config.json")

    subparsers.add_parser("doctor", help="扫描本机软件、模型和常见缓存位置")
    subparsers.add_parser("init-db", help="初始化素材SQLite数据库")

    ingest = subparsers.add_parser("import-manifest", help="导入镜头清单JSON")
    ingest.add_argument("--manifest", required=True)

    plan = subparsers.add_parser("plan", help="根据文案生成画面意图和混剪时间线")
    plan.add_argument("--script", required=True, help="UTF-8文案文件")
    plan.add_argument("--duration", type=float, help="目标时长；未提供时按语速估算")
    plan.add_argument("--project-id")
    plan.add_argument("--render", action="store_true", help="规划后调用自动发现的FFmpeg渲染")
    plan.add_argument("--voice", help="可选配音文件")
    plan.add_argument("--dry-run", action="store_true", help="仅生成FFmpeg命令，不执行")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        path = write_default_config(args.out)
        print(path)
        return 0

    config = load_config(args.config)
    pipeline = ScriptMixerPipeline(config=config)

    if args.command == "doctor":
        report = pipeline.doctor()
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "init-db":
        catalog = MediaCatalog(config.database_path)
        catalog.initialize()
        print(Path(config.database_path))
        return 0

    if args.command == "import-manifest":
        count = import_manifest(pipeline.catalog, args.manifest)
        print(json.dumps({"imported": count, "database": config.database_path}, ensure_ascii=False))
        return 0

    if args.command == "plan":
        script_text = load_script(args.script)
        timeline, project_dir = pipeline.plan(
            script_text=script_text,
            project_id=args.project_id,
            target_duration=args.duration,
        )
        result = {
            "project_id": timeline.project_id,
            "project_dir": str(project_dir),
            "duration": timeline.duration,
            "segments": len(timeline.segments),
            "warnings": timeline.warnings,
        }
        if args.render:
            output = pipeline.render(
                timeline,
                project_dir,
                voice_path=args.voice,
                dry_run=args.dry_run,
            )
            result["render_output"] = str(output)
            result["dry_run"] = args.dry_run
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
