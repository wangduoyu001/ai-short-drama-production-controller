from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .catalog import MediaCatalog
from .config import RuntimeConfig
from .enrichment import EnrichmentSummary, MediaEnricher
from .environment import discover_environment, save_discovery_report
from .intent import IntentProvider, build_visual_intents
from .models import DiscoveryReport, MediaScanSummary, ScriptUnit, Timeline, VisualIntent
from .ollama_adapter import (
    OllamaClient,
    OllamaError,
    OllamaIntentProvider,
    OllamaVisionProvider,
)
from .planner import plan_timeline
from .render import render_timeline, save_render_plan
from .retrieval import HybridRetriever, VectorSearchProvider
from .scanner import MediaScanner
from .script_parser import build_script_units


class ScriptMixerPipeline:
    def __init__(
        self,
        config: RuntimeConfig | None = None,
        intent_provider: IntentProvider | None = None,
        vector_provider: VectorSearchProvider | None = None,
    ):
        self.config = config or RuntimeConfig()
        self.intent_provider = intent_provider
        self.retriever = HybridRetriever(vector_provider=vector_provider)
        self.catalog = MediaCatalog(self.config.database_path)
        self.catalog.initialize()
        self._ollama_client: OllamaClient | None = None
        self._model_resolution_attempted = False

    def doctor(self) -> DiscoveryReport:
        report = discover_environment(self.config.discovery)
        save_discovery_report(report, self.config.discovery_report_path)
        return report

    def _get_ollama_client(self) -> OllamaClient | None:
        if self._ollama_client is not None:
            return self._ollama_client
        settings = self.config.local_models
        if not settings.auto_select_ollama_models and not (
            settings.text_model or settings.vision_model or settings.embedding_model
        ):
            return None
        client = OllamaClient(
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout_seconds,
        )
        if not client.is_available():
            return None
        self._ollama_client = client
        return client

    def model_status(self) -> dict:
        settings = self.config.local_models
        client = self._get_ollama_client()
        result = {
            "base_url": settings.ollama_base_url,
            "available": client is not None,
            "configured": {
                "text_model": settings.text_model,
                "vision_model": settings.vision_model,
                "embedding_model": settings.embedding_model,
                "speech_model": settings.speech_model,
            },
            "installed_models": [],
            "selected": {
                "text_model": "",
                "vision_model": "",
            },
            "errors": [],
        }
        if client is None:
            return result
        try:
            names = client.list_model_names()
            installed: list[dict] = []
            for name in names:
                try:
                    model = client.show_model(name)
                    installed.append(
                        {
                            "name": model.name,
                            "capabilities": model.capabilities,
                            "family": model.family,
                            "parameter_size": model.parameter_size,
                            "quantization_level": model.quantization_level,
                        }
                    )
                except OllamaError as exc:
                    result["errors"].append(f"{name}: {exc}")
            result["installed_models"] = installed
            text = client.select_model("completion", settings.text_model)
            vision = client.select_model("vision", settings.vision_model)
            result["selected"]["text_model"] = text.name if text else ""
            result["selected"]["vision_model"] = vision.name if vision else ""
        except OllamaError as exc:
            result["errors"].append(str(exc))
        return result

    def _resolve_intent_provider(self) -> IntentProvider | None:
        if self.intent_provider is not None:
            return self.intent_provider
        if self._model_resolution_attempted:
            return None
        self._model_resolution_attempted = True
        client = self._get_ollama_client()
        if client is None:
            return None
        try:
            model = client.select_model(
                capability="completion",
                preferred=self.config.local_models.text_model,
            )
        except OllamaError:
            return None
        if model is None:
            return None
        self.intent_provider = OllamaIntentProvider(client=client, model=model.name)
        return self.intent_provider

    def scan_media(
        self,
        root: str | Path,
        fast: bool = False,
        force: bool = False,
        prune_missing: bool = False,
    ) -> MediaScanSummary:
        discovery = self.doctor()
        ffprobe = discovery.tools.get("ffprobe")
        ffmpeg = discovery.tools.get("ffmpeg")
        scanner = MediaScanner(
            catalog=self.catalog,
            config=self.config.media_scan,
            ffprobe_path=ffprobe.executable if ffprobe else None,
            ffmpeg_path=ffmpeg.executable if ffmpeg else None,
        )
        summary = scanner.scan(
            root=root,
            fast=fast,
            force=force,
            prune_missing=prune_missing,
        )
        report_path = Path(self.config.database_path).parent / "last_scan.json"
        self._write_json(report_path, summary.to_dict())
        return summary

    def enrich_media(
        self,
        limit: int | None = None,
        force: bool = False,
    ) -> EnrichmentSummary:
        client = self._get_ollama_client()
        if client is None:
            raise RuntimeError("Ollama is unavailable; run models and verify the local service")
        try:
            model = client.select_model(
                capability="vision",
                preferred=self.config.local_models.vision_model,
            )
        except OllamaError as exc:
            raise RuntimeError(str(exc)) from exc
        if model is None:
            raise RuntimeError("No installed Ollama model reports the vision capability")
        provider = OllamaVisionProvider(client=client, model=model.name)
        summary = MediaEnricher(self.catalog, provider).enrich(limit=limit, force=force)
        report_path = Path(self.config.database_path).parent / "last_enrichment.json"
        self._write_json(report_path, summary.to_dict())
        return summary

    def plan(
        self,
        script_text: str,
        project_id: str | None = None,
        target_duration: float | None = None,
    ) -> tuple[Timeline, Path]:
        project_id = project_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
        units = build_script_units(script_text, target_duration=target_duration)
        provider = self._resolve_intent_provider()
        intents = build_visual_intents(units, provider=provider)
        clips = self.catalog.list_clips(usable_only=True)
        if not clips:
            raise RuntimeError(
                "Media catalog is empty. Run scan-media on a local media directory or import a clip manifest."
            )

        if not self.config.mixing.allow_missing_media_files_during_planning:
            clips = [clip for clip in clips if clip.validate_source()]
            if not clips:
                raise RuntimeError("No indexed media files exist on this computer")

        usage_counts = self.catalog.recent_usage_counts()
        candidates_by_unit = {
            intent.unit_id: self.retriever.retrieve(
                intent,
                clips,
                usage_counts=usage_counts,
                limit=50,
            )
            for intent in intents
        }
        timeline = plan_timeline(
            project_id=project_id,
            units=units,
            intents=intents,
            candidates_by_unit=candidates_by_unit,
            rules=self.config.mixing,
        )
        project_dir = self._write_project(project_id, script_text, units, intents, timeline, candidates_by_unit)
        self.catalog.record_usage(
            project_id,
            (
                (segment.segment_id, self._clip_id_for_segment(segment, candidates_by_unit), segment.source_id)
                for segment in timeline.segments
            ),
        )
        return timeline, project_dir

    @staticmethod
    def _clip_id_for_segment(segment, candidates_by_unit) -> str:
        candidates = candidates_by_unit.get(segment.unit_id, [])
        for candidate in candidates:
            clip = candidate.clip
            if clip.source_id == segment.source_id and clip.source_path == segment.source_path:
                if abs(clip.source_start - segment.source_start) < 0.001:
                    return clip.clip_id
        return f"unknown:{segment.segment_id}"

    def render(
        self,
        timeline: Timeline,
        project_dir: str | Path,
        voice_path: str | Path | None = None,
        dry_run: bool = False,
    ) -> Path:
        project_path = Path(project_dir)
        discovery = self.doctor()
        ffmpeg = discovery.tools.get("ffmpeg")
        output_path = project_path / "exports" / "final.mp4"
        command = render_timeline(
            timeline=timeline,
            ffmpeg_path=ffmpeg.executable if ffmpeg else None,
            output_path=output_path,
            voice_path=voice_path,
            dry_run=dry_run,
        )
        save_render_plan(command, project_path / "render_plan.json")
        return output_path

    def _write_project(
        self,
        project_id: str,
        script_text: str,
        units: list[ScriptUnit],
        intents: list[VisualIntent],
        timeline: Timeline,
        candidates_by_unit: dict,
    ) -> Path:
        project_dir = Path(self.config.output_root) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "exports").mkdir(exist_ok=True)
        (project_dir / "script.txt").write_text(script_text, encoding="utf-8")
        self._write_json(project_dir / "script_units.json", [asdict(item) for item in units])
        self._write_json(project_dir / "visual_intents.json", [asdict(item) for item in intents])
        self._write_json(project_dir / "timeline.json", timeline.to_dict())
        self._write_json(
            project_dir / "candidates.json",
            {
                unit_id: [
                    {
                        "clip": asdict(candidate.clip),
                        "score": candidate.score,
                        "reasons": candidate.reasons,
                    }
                    for candidate in candidates[:10]
                ]
                for unit_id, candidates in candidates_by_unit.items()
            },
        )
        self._write_json(project_dir / "report.json", self._build_report(timeline))
        return project_dir

    def _build_report(self, timeline: Timeline) -> dict:
        source_seconds: dict[str, float] = {}
        low_match_segments: list[str] = []
        for segment in timeline.segments:
            source_seconds[segment.source_id] = source_seconds.get(segment.source_id, 0.0) + segment.duration
            if segment.match_score < self.config.mixing.low_match_threshold:
                low_match_segments.append(segment.segment_id)
        highest_source_ratio = (
            max(source_seconds.values()) / timeline.duration if source_seconds and timeline.duration else 0.0
        )
        required_sources_met = len(source_seconds) >= self.config.mixing.minimum_source_count
        blocking_warnings = list(timeline.warnings)
        if not required_sources_met:
            blocking_warnings.append(
                f"unique source count {len(source_seconds)} is below required {self.config.mixing.minimum_source_count}"
            )
        return {
            "project_id": timeline.project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "duration": timeline.duration,
            "segment_count": len(timeline.segments),
            "unique_source_count": len(source_seconds),
            "required_source_count": self.config.mixing.minimum_source_count,
            "highest_single_source_ratio": round(highest_source_ratio, 4),
            "source_seconds": {key: round(value, 3) for key, value in source_seconds.items()},
            "low_match_segments": low_match_segments,
            "warnings": list(dict.fromkeys(blocking_warnings)),
            "allow_final_export": not blocking_warnings and not low_match_segments,
        }

    @staticmethod
    def _write_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
