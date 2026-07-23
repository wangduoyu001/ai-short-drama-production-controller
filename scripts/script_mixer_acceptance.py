from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from short_drama_controller.script_mixer.config import load_config
from short_drama_controller.script_mixer.integration import IntegrationChecker
from short_drama_controller.script_mixer.pipeline import ScriptMixerPipeline


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete local script-mixer acceptance sequence: environment preflight, "
            "real media scan, optional vision enrichment and embeddings, then a real preview render."
        )
    )
    parser.add_argument("--config", help="Local JSON config; omitted paths remain auto-discovered")
    parser.add_argument("--media-root", required=True, help="Real local media directory")
    parser.add_argument("--script", required=True, help="UTF-8 narration script")
    parser.add_argument("--voice", help="Optional real narration audio")
    parser.add_argument(
        "--fast-scan",
        action="store_true",
        help="Use fixed-window incremental scan instead of full scene detection and thumbnails",
    )
    parser.add_argument(
        "--force-media-scan",
        action="store_true",
        help="Reprocess media even when fingerprints are unchanged",
    )
    parser.add_argument(
        "--skip-semantic-index",
        action="store_true",
        help="Skip Ollama vision enrichment and embedding construction",
    )
    parser.add_argument(
        "--enrich-limit",
        type=int,
        help="Optional maximum number of clips to enrich during this run",
    )
    parser.add_argument(
        "--embedding-limit",
        type=int,
        help="Optional maximum number of clips to embed during this run",
    )
    parser.add_argument("--embedding-batch-size", type=int, default=32)
    parser.add_argument("--trial-duration", type=float, default=30.0)
    parser.add_argument(
        "--no-transcribe",
        action="store_true",
        help="Do not run Whisper during the real narration trial",
    )
    parser.add_argument(
        "--report",
        help="Override integration report path",
    )
    return parser


def _write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _check_status(report, check_id: str) -> str:
    for item in report.checks:
        if item.check_id == check_id:
            return item.status
    return "missing"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config(args.config)
    if args.report:
        config.integration.report_path = args.report
    pipeline = ScriptMixerPipeline(config=config)

    session_started = time.perf_counter()
    preflight = IntegrationChecker(pipeline).run(report_path=config.integration.report_path)
    if not preflight.environment_ready:
        print(json.dumps(preflight.to_dict(), ensure_ascii=False, indent=2))
        return 1

    stage_report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "media_scan": {},
        "semantic_enrichment": {"status": "skip"},
        "semantic_embeddings": {"status": "skip"},
    }

    scan_started = time.perf_counter()
    scan = pipeline.scan_media(
        root=args.media_root,
        fast=args.fast_scan,
        force=args.force_media_scan,
        prune_missing=False,
    )
    stage_report["media_scan"] = {
        "status": "pass" if scan.failed_files == 0 else "warn",
        "duration_seconds": round(time.perf_counter() - scan_started, 3),
        "summary": scan.to_dict(),
    }

    semantic_ok = True
    if not args.skip_semantic_index:
        try:
            enrich_started = time.perf_counter()
            enrichment = pipeline.enrich_media(limit=args.enrich_limit, force=False)
            stage_report["semantic_enrichment"] = {
                "status": "pass" if enrichment.failed == 0 else "fail",
                "duration_seconds": round(time.perf_counter() - enrich_started, 3),
                "summary": enrichment.to_dict(),
            }
            semantic_ok = enrichment.failed == 0
        except Exception as exc:
            semantic_ok = False
            stage_report["semantic_enrichment"] = {
                "status": "fail",
                "duration_seconds": 0.0,
                "error": f"{type(exc).__name__}: {exc}",
            }

        if semantic_ok:
            try:
                embedding_started = time.perf_counter()
                embeddings = pipeline.build_embeddings(
                    limit=args.embedding_limit,
                    force=False,
                    batch_size=args.embedding_batch_size,
                )
                stage_report["semantic_embeddings"] = {
                    "status": "pass" if embeddings.failed == 0 else "fail",
                    "duration_seconds": round(time.perf_counter() - embedding_started, 3),
                    "summary": embeddings.to_dict(),
                }
                semantic_ok = embeddings.failed == 0
            except Exception as exc:
                semantic_ok = False
                stage_report["semantic_embeddings"] = {
                    "status": "fail",
                    "duration_seconds": 0.0,
                    "error": f"{type(exc).__name__}: {exc}",
                }

    final_report = IntegrationChecker(pipeline).run(
        media_root=args.media_root,
        script_path=args.script,
        voice_path=args.voice,
        full_media_scan=not args.fast_scan,
        force_media_scan=False,
        run_trial=semantic_ok,
        trial_duration=args.trial_duration,
        transcribe_trial=not args.no_transcribe,
        report_path=config.integration.report_path,
    )

    payload = final_report.to_dict()
    stage_report["finished_at"] = datetime.now(timezone.utc).isoformat()
    stage_report["total_duration_seconds"] = round(time.perf_counter() - session_started, 3)
    stage_report["semantic_index_required"] = not args.skip_semantic_index
    stage_report["semantic_index_ready"] = semantic_ok
    stage_report["preflight_environment_ready"] = preflight.environment_ready
    stage_report["media_library_status"] = _check_status(final_report, "media_library")
    stage_report["real_trial_status"] = _check_status(final_report, "real_trial")
    payload["acceptance_session"] = stage_report
    payload.setdefault("performance", {}).update(
        {
            "acceptance_total_seconds": stage_report["total_duration_seconds"],
            "semantic_enrichment_seconds": stage_report["semantic_enrichment"].get(
                "duration_seconds", 0.0
            ),
            "semantic_embedding_seconds": stage_report["semantic_embeddings"].get(
                "duration_seconds", 0.0
            ),
        }
    )
    if not semantic_ok:
        payload.setdefault("blockers", []).append(
            "semantic preparation failed; real trial was not executed"
        )
        payload["ready_for_real_trial"] = False
        payload["trial_completed"] = False
    report_path = Path(config.integration.report_path)
    _write_report(report_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("trial_completed") and not payload.get("blockers") else 1


if __name__ == "__main__":
    raise SystemExit(main())
