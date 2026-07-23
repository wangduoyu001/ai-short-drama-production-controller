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
    subparsers.add_parser("models", help="读取Ollama和Whisper模型、能力与自动选择结果")
    subparsers.add_parser("init-db", help="初始化素材SQLite数据库")
    subparsers.add_parser("catalog-status", help="显示已入库原视频、镜头、音轨和向量数量")

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
        action="store_true",
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
    plan.add_argument("--burn-subtitles", action="store_true", help="渲染时把ASS或SRT字幕烧录进视频")
    plan.add_argument("--render", action="store_true", help="规划后调用自动发现的FFmpeg渲染")
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
        result = {
            "database": config.database_path,
            "source_count": len(sources),
            "source_with_audio_count": sum(source.has_audio for source in sources),
            "clip_count": len(clips),
            "clip_with_audio_count": sum(clip.has_audio for clip in clips),
            "source_status": status_counts,
            "duration_seconds": round(sum(source.duration for source in sources), 3),
            "missing_source_files": sum(not Path(source.source_path).exists() for source in sources),
            "thumbnail_count": sum(bool(clip.thumbnail_path) for clip in clips),
            "analyzed_clip_count": sum(
                bool(clip.description and clip.shot_type != "unknown") for clip in clips
            ),
            "embedding_cache": pipeline.embedding_store.model_counts(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

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
            transcribe_narration=not args.no_transcribe,
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
        "warnings": audio.warnings,
    }


if __name__ == "__main__":
    raise SystemExit(main())
