from __future__ import annotations

import argparse
import json
from pathlib import Path

from .catalog import MediaCatalog, import_manifest
from .config import load_config, write_default_config
from .integration import IntegrationChecker
from .pipeline import ScriptMixerPipeline
from .replan import ProjectReplanner
from .review import TimelineReviewService, load_timeline, resolve_project_dir
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
    subparsers.add_parser("models", help="读取Ollama和Whisper模型、能力与自动选择结果")
    subparsers.add_parser("init-db", help="初始化素材SQLite数据库")
    subparsers.add_parser("catalog-status", help="显示已入库原视频、镜头、音轨和向量数量")

    integration = subparsers.add_parser(
        "integration-check",
        help="执行真实电脑环境、字幕、编码、素材边界和可选试剪验收",
    )
    integration.add_argument("--media-root", help="真实本地素材目录；提供后执行增量扫描和40秒边界检查")
    integration.add_argument("--script", help="真实试剪使用的UTF-8文案文件")
    integration.add_argument("--voice", help="真实试剪使用的配音音频；未提供时使用原视频音频")
    integration.add_argument(
        "--full-media-scan",
        action="store_true",
        help="对素材执行完整场景检测和缩略图生成；默认使用快速增量扫描",
    )
    integration.add_argument(
        "--force-media-scan",
        action="store_true",
        help="强制重新分析真实素材，不复用未变化记录",
    )
    integration.add_argument(
        "--run-trial",
        action="store_true",
        help="完成基础检查后运行真实时间线规划、字幕和MP4渲染",
    )
    integration.add_argument(
        "--trial-duration",
        type=float,
        help="没有真实配音时的试剪时长，默认使用配置中的30秒",
    )
    integration.add_argument(
        "--no-transcribe-trial",
        action="store_true",
        help="真实配音试剪时不调用Whisper，改用比例时间轴",
    )
    integration.add_argument(
        "--report",
        help="集成报告输出路径；默认.runtime/script_mixer/integration_report.json",
    )

    scan = subparsers.add_parser("scan-media", help="扫描本地视频目录并增量写入素材库")
    scan.add_argument("--root", required=True, help="本地原始视频目录")
    scan.add_argument(
        "--fast",
        action="store_true",
        help="快速入库：跳过场景检测和缩略图，使用固定窗口切分",
    )
    scan.add_argument(
        "--force",
        action="store_true",
        help="强制重新分析，即使文件指纹没有变化",
    )
    scan.add_argument(
        "--prune-missing",
        action="store_true",
        help="删除数据库中属于该目录但本地已经不存在的素材记录",
    )

    enrich = subparsers.add_parser("enrich-media", help="使用本地Ollama视觉模型分析关键帧")
    enrich.add_argument("--limit", type=int, help="本次最多分析多少个镜头")
    enrich.add_argument("--force", action="store_true", help="强制重新分析已有描述的镜头")

    embeddings = subparsers.add_parser(
        "build-embeddings",
        help="使用本地Ollama嵌入模型增量构建镜头语义向量",
    )
    embeddings.add_argument("--limit", type=int, help="本次最多处理多少个镜头")
    embeddings.add_argument("--force", action="store_true", help="强制重建未变化镜头的向量")
    embeddings.add_argument("--batch-size", type=int, default=32, help="批量嵌入条数，默认32")

    ingest = subparsers.add_parser("import-manifest", help="导入镜头清单JSON")
    ingest.add_argument("--manifest", required=True)

    plan = subparsers.add_parser("plan", help="根据文案生成画面意图和混剪时间线")
    plan.add_argument("--script", required=True, help="UTF-8文案文件")
    plan.add_argument("--duration", type=float, help="无真实配音时的目标时长；默认按语速估算")
    plan.add_argument("--project-id")
    plan.add_argument(
        "--audio-mode",
        choices=["auto", "narration", "source", "mixed", "mute"],
        default="auto",
        help="auto=有配音用配音、无配音保留原声；mixed=配音和压低后的原声混合",
    )
    plan.add_argument("--voice", help="真实配音音频；其实际时长优先于--duration")
    plan.add_argument(
        "--voice-duration",
        type=float,
        help="已知配音时长时可直接提供；否则使用自动发现的FFprobe读取",
    )
    plan.add_argument(
        "--no-transcribe",
        dest="transcribe_narration",
        action="store_false",
        default=None,
        help="不调用Whisper，按配音总时长比例分配每句时间",
    )
    plan.add_argument(
        "--transcript-json",
        help="使用已有Whisper JSON进行逐句对齐，不重新执行Whisper",
    )
    plan.add_argument(
        "--whisper-model",
        help="本次使用的本地Whisper模型名称或.pt路径；未提供时自动扫描",
    )
    plan.add_argument("--burn-subtitles", action="store_true", help="渲染时优先烧录逐字ASS字幕")
    plan.add_argument("--render", action="store_true", help="规划后调用自动发现的FFmpeg渲染")
    plan.add_argument("--dry-run", action="store_true", help="仅生成FFmpeg命令，不执行")

    review = subparsers.add_parser("review-project", help="生成或刷新时间线人工审核清单与QA报告")
    review.add_argument("--project", required=True, help="项目ID或项目目录")

    lock = subparsers.add_parser("lock-segment", help="锁定已确认镜头，防止后续替换")
    lock.add_argument("--project", required=True)
    lock.add_argument("--segment", required=True, help="时间线片段ID，例如S002")

    unlock = subparsers.add_parser("unlock-segment", help="解除镜头锁定")
    unlock.add_argument("--project", required=True)
    unlock.add_argument("--segment", required=True)

    replace = subparsers.add_parser("replace-segment", help="从已保存候选中替换单个时间线镜头")
    replace.add_argument("--project", required=True)
    replace.add_argument("--segment", required=True)
    replace.add_argument("--exclude-source", action="append", default=[], help="排除来源ID，可重复")
    replace.add_argument("--exclude-clip", action="append", default=[], help="排除镜头ID，可重复")
    replace.add_argument("--keyword", default="", help="候选描述、标签和情绪必须包含的关键词")
    replace.add_argument("--shot-type", default="", help="要求的景别关键词")
    audio_group = replace.add_mutually_exclusive_group()
    audio_group.add_argument(
        "--require-audio",
        dest="require_audio",
        action="store_const",
        const=True,
        default=None,
        help="只选择有原视频音轨的候选",
    )
    audio_group.add_argument(
        "--require-silent",
        dest="require_audio",
        action="store_const",
        const=False,
        help="只选择无音轨候选",
    )
    replace.add_argument("--candidate-rank", type=int, default=1, help="筛选后选择第几个候选，默认1")
    replace.add_argument("--reason", default="manual replacement", help="本次替换原因")
    replace.add_argument(
        "--allow-missing-media",
        action="store_true",
        help="允许选择本机不存在的候选路径；仅用于迁移排查，不建议渲染",
    )

    replan = subparsers.add_parser(
        "replan-project",
        help="使用原项目文案单元、画面意图和候选池重新规划未锁定镜头",
    )
    replan.add_argument("--project", required=True)

    rollback = subparsers.add_parser("rollback-project", help="回退最近一次锁定、解锁、替换或重新规划")
    rollback.add_argument("--project", required=True)

    rerender = subparsers.add_parser("rerender-project", help="使用已返修时间线覆盖重渲染final.mp4")
    rerender.add_argument("--project", required=True)
    rerender.add_argument("--burn-subtitles", action="store_true")
    rerender.add_argument("--dry-run", action="store_true")
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

    if args.command == "models":
        result = pipeline.model_status()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        available = bool(result["available"] or result.get("whisper", {}).get("available"))
        return 0 if available else 1

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
            "duration_seconds": round(original_duration, 3),
            "original_duration_seconds": round(original_duration, 3),
            "indexed_duration_seconds": round(indexed_duration, 3),
            "ignored_tail_seconds": round(ignored_tail, 3),
            "capped_source_count": sum(source.ignored_tail_seconds > 0 for source in sources),
            "maximum_source_process_seconds": config.media_scan.maximum_source_process_seconds,
            "missing_source_files": sum(not Path(source.source_path).exists() for source in sources),
            "thumbnail_count": sum(bool(clip.thumbnail_path) for clip in clips),
            "analyzed_clip_count": sum(
                bool(clip.description and clip.shot_type != "unknown") for clip in clips
            ),
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
        success = report.trial_completed if args.run_trial else report.environment_ready
        return 0 if success else 1

    if args.command == "scan-media":
        summary = pipeline.scan_media(
            root=args.root,
            fast=args.fast,
            force=args.force,
            prune_missing=args.prune_missing,
        )
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.failed_files == 0 else 1

    if args.command == "enrich-media":
        summary = pipeline.enrich_media(limit=args.limit, force=args.force)
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.failed == 0 else 1

    if args.command == "build-embeddings":
        summary = pipeline.build_embeddings(
            limit=args.limit,
            force=args.force,
            batch_size=args.batch_size,
        )
        print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
        return 0 if summary.failed == 0 else 1

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
        }
        if args.render:
            output = pipeline.render(
                timeline,
                project_dir,
                burn_subtitles=args.burn_subtitles,
                dry_run=args.dry_run,
            )
            result["render_output"] = str(output)
            result["burn_subtitles"] = args.burn_subtitles
            result["dry_run"] = args.dry_run
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    review_service = TimelineReviewService(config)
    if args.command == "review-project":
        result = review_service.review(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "lock-segment":
        result = review_service.lock(args.project, args.segment)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "unlock-segment":
        result = review_service.unlock(args.project, args.segment)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "replace-segment":
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
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "replan-project":
        result = ProjectReplanner(config).replan(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "rollback-project":
        result = review_service.rollback(args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "rerender-project":
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
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


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
