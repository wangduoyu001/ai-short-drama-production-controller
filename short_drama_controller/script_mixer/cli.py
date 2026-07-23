from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import MediaCatalog, import_manifest
from .config import load_config, write_default_config
from .edit_package import EditPackageExporter
from .integration import IntegrationChecker
from .jianying_draft import jianying_status
from .pipeline import ScriptMixerPipeline
from .replan import ProjectReplanner
from .review import TimelineReviewService, load_timeline, resolve_project_dir
from .script_parser import load_script


def _add_audio_plan_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--audio-mode",
        choices=["auto", "narration", "source", "mixed", "mute"],
        default="auto",
        help="auto=有配音用配音、无配音保留原声；mixed=配音和压低后的原声混合",
    )
    parser.add_argument("--voice", help="真实配音音频；其实际时长优先于--duration")
    parser.add_argument(
        "--voice-duration",
        type=float,
        help="已知配音时长时可直接提供；否则使用自动发现的FFprobe读取",
    )
    parser.add_argument(
        "--no-transcribe",
        dest="transcribe_narration",
        action="store_false",
        default=None,
        help="不调用Whisper，按配音总时长比例分配每句时间",
    )
    parser.add_argument(
        "--transcript-json",
        help="使用已有Whisper JSON进行逐句对齐，不重新执行Whisper",
    )
    parser.add_argument(
        "--whisper-model",
        help="本次使用的本地Whisper模型名称或.pt路径；未提供时自动扫描",
    )


def _add_edit_package_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--draft-root", help="剪映草稿目录；未提供时自动发现或读取本地配置")
    parser.add_argument("--draft-name", help="剪映草稿名称；默认AI粗剪_<项目ID>")
    parser.add_argument("--no-draft", action="store_true", help="只生成标准编辑包，不生成剪映草稿")
    parser.add_argument(
        "--require-draft",
        action="store_true",
        help="剪映草稿生成失败时返回失败；默认保留可用编辑包并警告",
    )
    parser.add_argument("--candidate-count", type=int, help="每个片段导出多少个备用候选")
    parser.add_argument("--handle-before", type=float, help="当前选中区间前保留多少秒余量")
    parser.add_argument("--handle-after", type=float, help="当前选中区间后保留多少秒余量")
    parser.add_argument("--force-package", action="store_true", help="不复用已有代理，强制重新导出")
    parser.add_argument("--package-dry-run", action="store_true", help="只生成编辑包FFmpeg命令")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="script-driven-mixer",
        description="根据输入文案从本地素材库规划多来源混剪时间线，并导出剪映可编辑工程。",
    )
    parser.add_argument("--config", help="JSON配置文件路径；未提供时使用空路径默认配置")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_config = subparsers.add_parser("init-config", help="生成不包含本机路径的默认配置")
    init_config.add_argument("--out", default="script_mixer.config.json")

    subparsers.add_parser("doctor", help="扫描本机软件、模型和常见缓存位置")
    subparsers.add_parser("models", help="读取Ollama和Whisper模型、能力与自动选择结果")
    subparsers.add_parser("jianying-status", help="检查剪映草稿目录和草稿生成依赖")
    subparsers.add_parser("init-db", help="初始化素材SQLite数据库")
    subparsers.add_parser("catalog-status", help="显示已入库原视频、镜头、音轨和向量数量")

    integration = subparsers.add_parser(
        "integration-check",
        help="执行真实电脑环境、字幕、编码、素材边界和可选试剪验收",
    )
    integration.add_argument("--media-root", help="真实本地素材目录；提供后执行增量扫描和40秒边界检查")
    integration.add_argument("--script", help="真实试剪使用的UTF-8文案文件")
    integration.add_argument("--voice", help="真实试剪使用的配音音频；未提供时使用原视频音频")
    integration.add_argument("--full-media-scan", action="store_true")
    integration.add_argument("--force-media-scan", action="store_true")
    integration.add_argument("--run-trial", action="store_true")
    integration.add_argument("--trial-duration", type=float)
    integration.add_argument("--no-transcribe-trial", action="store_true")
    integration.add_argument("--report")

    scan = subparsers.add_parser("scan-media", help="扫描本地视频目录并增量写入素材库")
    scan.add_argument("--root", required=True, help="本地原始视频目录")
    scan.add_argument("--fast", action="store_true")
    scan.add_argument("--force", action="store_true")
    scan.add_argument("--prune-missing", action="store_true")

    enrich = subparsers.add_parser("enrich-media", help="使用本地Ollama视觉模型分析关键帧")
    enrich.add_argument("--limit", type=int)
    enrich.add_argument("--force", action="store_true")

    embeddings = subparsers.add_parser("build-embeddings", help="构建镜头语义向量")
    embeddings.add_argument("--limit", type=int)
    embeddings.add_argument("--force", action="store_true")
    embeddings.add_argument("--batch-size", type=int, default=32)

    ingest = subparsers.add_parser("import-manifest", help="导入镜头清单JSON")
    ingest.add_argument("--manifest", required=True)

    plan = subparsers.add_parser("plan", help="根据文案生成画面意图和混剪时间线")
    plan.add_argument("--script", required=True, help="UTF-8文案文件")
    plan.add_argument("--duration", type=float)
    plan.add_argument("--project-id")
    _add_audio_plan_arguments(plan)
    plan.add_argument("--burn-subtitles", action="store_true")
    plan.add_argument("--render", action="store_true")
    plan.add_argument("--dry-run", action="store_true")

    make = subparsers.add_parser(
        "make-jianying-project",
        help="从素材目录和文案一键生成预览、剪映编辑包和可选草稿",
    )
    make.add_argument("--script", required=True)
    make.add_argument("--media-root", help="提供时先增量扫描；不提供则使用现有素材库")
    make.add_argument("--project-id")
    make.add_argument("--duration", type=float)
    make.add_argument("--fast-scan", action="store_true", help="固定窗口快速扫描")
    make.add_argument("--force-scan", action="store_true")
    make.add_argument("--skip-enrich", action="store_true", help="跳过视觉分析")
    make.add_argument("--skip-embeddings", action="store_true", help="跳过向量构建")
    make.add_argument("--enrich-limit", type=int)
    make.add_argument("--embedding-limit", type=int)
    make.add_argument("--embedding-batch-size", type=int, default=32)
    make.add_argument("--no-preview", action="store_true")
    make.add_argument("--burn-subtitles", action="store_true")
    _add_audio_plan_arguments(make)
    _add_edit_package_arguments(make)

    package = subparsers.add_parser(
        "export-jianying-package",
        help="把已有项目导出为可自由拖动的剪映编辑包和可选草稿",
    )
    package.add_argument("--project", required=True)
    _add_edit_package_arguments(package)

    review = subparsers.add_parser("review-project", help="生成或刷新时间线人工审核清单与QA报告")
    review.add_argument("--project", required=True)

    lock = subparsers.add_parser("lock-segment", help="锁定已确认镜头")
    lock.add_argument("--project", required=True)
    lock.add_argument("--segment", required=True)

    unlock = subparsers.add_parser("unlock-segment", help="解除镜头锁定")
    unlock.add_argument("--project", required=True)
    unlock.add_argument("--segment", required=True)

    replace = subparsers.add_parser("replace-segment", help="从已保存候选中替换单个镜头")
    replace.add_argument("--project", required=True)
    replace.add_argument("--segment", required=True)
    replace.add_argument("--exclude-source", action="append", default=[])
    replace.add_argument("--exclude-clip", action="append", default=[])
    replace.add_argument("--keyword", default="")
    replace.add_argument("--shot-type", default="")
    audio_group = replace.add_mutually_exclusive_group()
    audio_group.add_argument("--require-audio", dest="require_audio", action="store_const", const=True, default=None)
    audio_group.add_argument("--require-silent", dest="require_audio", action="store_const", const=False)
    replace.add_argument("--candidate-rank", type=int, default=1)
    replace.add_argument("--reason", default="manual replacement")
    replace.add_argument("--allow-missing-media", action="store_true")

    replan = subparsers.add_parser("replan-project", help="保留锁定镜头，重新规划未锁定镜头")
    replan.add_argument("--project", required=True)

    rollback = subparsers.add_parser("rollback-project", help="回退最近一次返修")
    rollback.add_argument("--project", required=True)

    rerender = subparsers.add_parser("rerender-project", help="使用返修时间线覆盖重渲染final.mp4")
    rerender.add_argument("--project", required=True)
    rerender.add_argument("--burn-subtitles", action="store_true")
    rerender.add_argument("--dry-run", action="store_true")
    return parser


def _edit_package_exporter(pipeline: ScriptMixerPipeline) -> EditPackageExporter:
    discovery = pipeline.doctor()
    ffmpeg = discovery.tools.get("ffmpeg")
    ffprobe = discovery.tools.get("ffprobe")
    return EditPackageExporter(
        pipeline.config,
        ffmpeg_path=ffmpeg.executable if ffmpeg else None,
        ffprobe_path=ffprobe.executable if ffprobe else None,
    )


def _export_edit_package(exporter: EditPackageExporter, args, project) -> dict:
    return exporter.export(
        project=project,
        draft_root=args.draft_root,
        draft_name=args.draft_name,
        create_draft=not args.no_draft,
        require_draft=args.require_draft,
        candidate_count=args.candidate_count,
        handle_before=args.handle_before,
        handle_after=args.handle_after,
        force=args.force_package,
        dry_run=args.package_dry_run,
    )


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
        print(json.dumps(pipeline.doctor().to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "models":
        result = pipeline.model_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["available"] or result.get("whisper", {}).get("available") else 1

    if args.command == "jianying-status":
        result = jianying_status(config)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ready"] else 1

    if args.command == "init-db":
        catalog = MediaCatalog(config.database_path)
        catalog.initialize()
        print(Path(config.database_path))
        return 0

    if args.command == "catalog-status":
        sources = pipeline.catalog.list_sources()
        clips = pipeline.catalog.list_clips(usable_only=False)
        status_counts: dict[str, int] = {}
        for source in sources:
            status_counts[source.status] = status_counts.get(source.status, 0) + 1
        original_duration = sum(source.duration for source in sources)
        indexed_duration = sum(source.indexed_duration for source in sources)
        ignored_tail = sum(source.ignored_tail_seconds for source in sources)
        result = {
            "database": config.database_path,
            "source_count": len(sources),
            "source_with_audio_count": sum(source.has_audio for source in sources),
            "clip_count": len(clips),
            "clip_with_audio_count": sum(clip.has_audio for clip in clips),
            "source_status": status_counts,
            "original_duration_seconds": round(original_duration, 3),
            "indexed_duration_seconds": round(indexed_duration, 3),
            "ignored_tail_seconds": round(ignored_tail, 3),
            "capped_source_count": sum(source.ignored_tail_seconds > 0 for source in sources),
            "maximum_source_process_seconds": config.media_scan.maximum_source_process_seconds,
            "missing_source_files": sum(not Path(source.source_path).exists() for source in sources),
            "thumbnail_count": sum(bool(clip.thumbnail_path) for clip in clips),
            "analyzed_clip_count": sum(bool(clip.description and clip.shot_type != "unknown") for clip in clips),
            "embedding_cache": pipeline.embedding_store.model_counts(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "integration-check":
        report = IntegrationChecker(pipeline).run(
            media_root=args.media_root,
            script_path=args.script,
            voice_path=args.voice,
            full_media_scan=args.full_media_scan,
            force_media_scan=args.force_media_scan,
            run_trial=args.run_trial,
            trial_duration=args.trial_duration,
            transcribe_trial=not args.no_transcribe_trial,
            report_path=args.report,
        )
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return 0 if (report.trial_completed if args.run_trial else report.environment_ready) else 1

    if args.command == "scan-media":
        summary = pipeline.scan_media(args.root, fast=args.fast, force=args.force, prune_missing=args.prune_missing)
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.failed_files == 0 else 1

    if args.command == "enrich-media":
        summary = pipeline.enrich_media(limit=args.limit, force=args.force)
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.failed == 0 else 1

    if args.command == "build-embeddings":
        summary = pipeline.build_embeddings(limit=args.limit, force=args.force, batch_size=args.batch_size)
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.failed == 0 else 1

    if args.command == "import-manifest":
        count = import_manifest(pipeline.catalog, args.manifest)
        print(json.dumps({"imported": count, "database": config.database_path}, ensure_ascii=False))
        return 0

    if args.command in {"plan", "make-jianying-project"}:
        preparation: dict = {}
        if args.command == "make-jianying-project" and args.media_root:
            scan = pipeline.scan_media(
                args.media_root,
                fast=args.fast_scan,
                force=args.force_scan,
                prune_missing=False,
            )
            preparation["scan"] = scan.to_dict()
            if not args.skip_enrich:
                try:
                    preparation["enrichment"] = pipeline.enrich_media(
                        limit=args.enrich_limit,
                        force=False,
                    ).to_dict()
                except Exception as exc:
                    preparation["enrichment_warning"] = f"{type(exc).__name__}: {exc}"
            if not args.skip_embeddings:
                try:
                    preparation["embeddings"] = pipeline.build_embeddings(
                        limit=args.embedding_limit,
                        force=False,
                        batch_size=args.embedding_batch_size,
                    ).to_dict()
                except Exception as exc:
                    preparation["embedding_warning"] = f"{type(exc).__name__}: {exc}"

        script_text = load_script(args.script)
        timeline, project_dir = pipeline.plan(
            script_text=script_text,
            project_id=args.project_id,
            target_duration=args.duration,
            narration_path=args.voice,
            audio_mode=args.audio_mode,
            narration_duration=args.voice_duration,
            transcribe_narration=args.transcribe_narration,
            transcript_json_path=args.transcript_json,
            whisper_model=args.whisper_model,
        )
        result = {
            "project_id": timeline.project_id,
            "project_dir": str(project_dir),
            "duration": timeline.duration,
            "segments": len(timeline.segments),
            "audio": asdict_audio(timeline.audio),
            "warnings": [*timeline.warnings, *timeline.audio.warnings],
            "preparation": preparation,
        }
        should_render = args.render if args.command == "plan" else not args.no_preview
        if should_render:
            output = pipeline.render(
                timeline,
                project_dir,
                burn_subtitles=args.burn_subtitles,
                dry_run=args.dry_run if args.command == "plan" else False,
            )
            result["preview_output"] = str(output)
        if args.command == "make-jianying-project":
            result["edit_package"] = _export_edit_package(
                _edit_package_exporter(pipeline), args, project_dir
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "export-jianying-package":
        result = _export_edit_package(_edit_package_exporter(pipeline), args, args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result.get("failures") else 1

    review_service = TimelineReviewService(config)
    if args.command == "review-project":
        result = review_service.review(args.project)
    elif args.command == "lock-segment":
        result = review_service.lock(args.project, args.segment)
    elif args.command == "unlock-segment":
        result = review_service.unlock(args.project, args.segment)
    elif args.command == "replace-segment":
        result = review_service.replace(
            project=args.project,
            segment_id=args.segment,
            exclude_source_ids=args.exclude_source,
            exclude_clip_ids=args.exclude_clip,
            keyword=args.keyword,
            shot_type=args.shot_type,
            require_audio=args.require_audio,
            candidate_rank=args.candidate_rank,
            reason=args.reason,
            allow_missing_media=args.allow_missing_media,
        )
    elif args.command == "replan-project":
        result = ProjectReplanner(config).replan(args.project)
    elif args.command == "rollback-project":
        result = review_service.rollback(args.project)
    elif args.command == "rerender-project":
        project_dir = resolve_project_dir(args.project, config.output_root)
        timeline = load_timeline(project_dir)
        review_result = review_service.review(project_dir)
        output = pipeline.render(
            timeline,
            project_dir,
            burn_subtitles=True if args.burn_subtitles else None,
            dry_run=args.dry_run,
        )
        result = {
            "project_dir": str(project_dir),
            "output": str(output),
            "dry_run": args.dry_run,
            "allow_final_export": review_result["allow_final_export"],
            "review_path": review_result["review_path"],
            "report_path": review_result["report_path"],
        }
    else:
        parser.error(f"Unsupported command: {args.command}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def asdict_audio(audio) -> dict:
    return {
        "mode": audio.mode,
        "narration_path": audio.narration_path,
        "narration_duration": audio.narration_duration,
        "source_audio_segments": audio.source_audio_segments,
        "source_audio_coverage": audio.source_audio_coverage,
        "transcript_path": audio.transcript_path,
        "transcription_model": audio.transcription_model,
        "transcription_language": audio.transcription_language,
        "timing_source": audio.timing_source,
        "alignment_coverage": audio.alignment_coverage,
        "subtitle_srt_path": audio.subtitle_srt_path,
        "subtitle_ass_path": audio.subtitle_ass_path,
        "subtitle_karaoke_ass_path": audio.subtitle_karaoke_ass_path,
        "warnings": audio.warnings,
    }


if __name__ == "__main__":
    raise SystemExit(main())
