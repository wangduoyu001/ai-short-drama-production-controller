from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .audio import AudioProbeError, build_audio_plan, probe_audio, resolve_audio_mode
from .catalog import MediaCatalog
from .config import RuntimeConfig
from .embeddings import (
    EmbeddingSummary,
    OllamaEmbeddingIndexer,
    OllamaVectorSearchProvider,
    SQLiteEmbeddingStore,
)
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
from .subtitles import write_subtitles
from .transcription import (
    AlignmentResult,
    TranscriptionError,
    TranscriptionResult,
    align_script_to_transcription,
    load_transcription_json,
    resolve_whisper_model,
    run_whisper_cli,
)


class ScriptMixerPipeline:
    def __init__(
        self,
        config: RuntimeConfig | None = None,
        intent_provider: IntentProvider | None = None,
        vector_provider: VectorSearchProvider | None = None,
    ):
        self.config = config or RuntimeConfig()
        self.intent_provider = intent_provider
        self._provided_vector_provider = vector_provider
        self.catalog = MediaCatalog(self.config.database_path)
        self.catalog.initialize()
        self.embedding_store = SQLiteEmbeddingStore(self.config.database_path)
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
        discovery = self.doctor()
        whisper_tool = discovery.tools.get("whisper")
        whisper_model = resolve_whisper_model(
            settings.speech_model,
            discovery.models.get("whisper", []),
            allow_download=self.config.transcription.allow_model_download,
        )
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
                "embedding_model": "",
                "speech_model": whisper_model or "",
            },
            "whisper": {
                "available": bool(whisper_tool and whisper_tool.available),
                "executable": whisper_tool.executable if whisper_tool else "",
                "selected_model": whisper_model or "",
                "allow_model_download": self.config.transcription.allow_model_download,
            },
            "embedding_cache": self.embedding_store.model_counts(),
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
            embedding = client.select_model("embedding", settings.embedding_model)
            result["selected"]["text_model"] = text.name if text else ""
            result["selected"]["vision_model"] = vision.name if vision else ""
            result["selected"]["embedding_model"] = embedding.name if embedding else ""
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

    def _resolve_vector_provider(self) -> VectorSearchProvider | None:
        if self._provided_vector_provider is not None:
            return self._provided_vector_provider
        client = self._get_ollama_client()
        if client is None:
            return None
        try:
            model = client.select_model(
                capability="embedding",
                preferred=self.config.local_models.embedding_model,
            )
        except OllamaError:
            return None
        if model is None or self.embedding_store.count(model.name) == 0:
            return None
        return OllamaVectorSearchProvider(
            store=self.embedding_store,
            client=client,
            model=model.name,
        )

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

    def build_embeddings(
        self,
        limit: int | None = None,
        force: bool = False,
        batch_size: int = 32,
    ) -> EmbeddingSummary:
        client = self._get_ollama_client()
        if client is None:
            raise RuntimeError("Ollama is unavailable; run models and verify the local service")
        try:
            model = client.select_model(
                capability="embedding",
                preferred=self.config.local_models.embedding_model,
            )
        except OllamaError as exc:
            raise RuntimeError(str(exc)) from exc
        if model is None:
            raise RuntimeError("No installed Ollama model reports the embedding capability")
        indexer = OllamaEmbeddingIndexer(
            catalog=self.catalog,
            store=self.embedding_store,
            client=client,
            model=model.name,
        )
        summary = indexer.build(
            limit=limit,
            force=force,
            batch_size=batch_size,
        )
        report_path = Path(self.config.database_path).parent / "last_embeddings.json"
        self._write_json(report_path, summary.to_dict())
        return summary

    def _prepare_audio(
        self,
        narration_path: str | Path | None,
        requested_mode: str | None,
        target_duration: float | None,
        narration_duration: float | None,
    ) -> tuple[str, str, float | None, float, list[str]]:
        mode = resolve_audio_mode(
            requested_mode or self.config.audio.default_mode,
            narration_path,
        )
        resolved_path = ""
        measured_duration = max(0.0, float(narration_duration or 0.0))
        warnings: list[str] = []
        if mode in {"narration", "mixed"}:
            resolved_path = str(Path(str(narration_path)).expanduser().resolve())
            if measured_duration <= 0:
                discovery = self.doctor()
                ffprobe = discovery.tools.get("ffprobe")
                try:
                    measured_duration = probe_audio(
                        resolved_path,
                        ffprobe.executable if ffprobe else None,
                    ).duration
                except (AudioProbeError, FileNotFoundError) as exc:
                    raise RuntimeError(str(exc)) from exc
            if target_duration and abs(target_duration - measured_duration) > 0.2:
                warnings.append(
                    f"Requested duration {target_duration:.3f}s was overridden by narration duration "
                    f"{measured_duration:.3f}s"
                )
            effective_duration: float | None = measured_duration
        else:
            effective_duration = target_duration
        return mode, resolved_path, effective_duration, measured_duration, warnings

    def _prepare_timed_units(
        self,
        script_text: str,
        project_id: str,
        mode: str,
        narration_path: str,
        duration: float | None,
        transcribe_narration: bool | None,
        transcript_json_path: str | Path | None,
        whisper_model: str | None,
    ) -> tuple[list[ScriptUnit], TranscriptionResult | None, AlignmentResult | None, list[str]]:
        fallback = build_script_units(script_text, target_duration=duration)
        if mode not in {"narration", "mixed"} or not narration_path:
            return fallback, None, None, []
        should_transcribe = (
            self.config.transcription.auto_transcribe_narration
            if transcribe_narration is None
            else transcribe_narration
        )
        if not self.config.transcription.enabled or not should_transcribe:
            return fallback, None, None, ["Whisper transcription was disabled; proportional timing was used"]

        warnings: list[str] = []
        transcription: TranscriptionResult
        try:
            if transcript_json_path:
                transcription = load_transcription_json(
                    transcript_json_path,
                    audio_path=narration_path,
                    duration_override=duration,
                )
            else:
                discovery = self.doctor()
                whisper_tool = discovery.tools.get("whisper")
                selected_model = resolve_whisper_model(
                    whisper_model or self.config.local_models.speech_model,
                    discovery.models.get("whisper", []),
                    allow_download=self.config.transcription.allow_model_download,
                )
                transcription = run_whisper_cli(
                    whisper_path=whisper_tool.executable if whisper_tool else None,
                    audio_path=narration_path,
                    model=selected_model,
                    output_dir=Path(self.config.transcription.output_root) / project_id,
                    config=self.config.transcription,
                    initial_prompt=script_text,
                    duration_override=duration,
                )
        except (TranscriptionError, FileNotFoundError, OSError, ValueError) as exc:
            warnings.append(f"Whisper timing fallback: {exc}")
            return fallback, None, None, warnings

        alignment = align_script_to_transcription(
            script_text=script_text,
            transcription=transcription,
            minimum_coverage=self.config.transcription.minimum_alignment_coverage,
            max_chars=self.config.transcription.max_script_unit_chars,
        )
        warnings.extend(transcription.warnings)
        warnings.extend(alignment.warnings)
        return alignment.units, transcription, alignment, warnings

    def plan(
        self,
        script_text: str,
        project_id: str | None = None,
        target_duration: float | None = None,
        narration_path: str | Path | None = None,
        audio_mode: str | None = None,
        narration_duration: float | None = None,
        transcribe_narration: bool | None = None,
        transcript_json_path: str | Path | None = None,
        whisper_model: str | None = None,
    ) -> tuple[Timeline, Path]:
        project_id = project_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
        mode, resolved_narration, effective_duration, measured_duration, audio_warnings = (
            self._prepare_audio(
                narration_path=narration_path,
                requested_mode=audio_mode,
                target_duration=target_duration,
                narration_duration=narration_duration,
            )
        )
        units, transcription, alignment, timing_warnings = self._prepare_timed_units(
            script_text=script_text,
            project_id=project_id,
            mode=mode,
            narration_path=resolved_narration,
            duration=effective_duration,
            transcribe_narration=transcribe_narration,
            transcript_json_path=transcript_json_path,
            whisper_model=whisper_model,
        )
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

        retriever = HybridRetriever(
            vector_provider=self._resolve_vector_provider(),
            prefer_source_audio=mode in {"source", "mixed"},
        )
        usage_counts = self.catalog.recent_usage_counts()
        candidates_by_unit = {
            intent.unit_id: retriever.retrieve(
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
        timeline.audio = build_audio_plan(
            segments=timeline.segments,
            duration=timeline.duration,
            config=self.config.audio,
            requested_mode=mode,
            narration_path=resolved_narration or None,
            narration_duration=measured_duration,
        )
        timeline.audio.warnings.extend([*audio_warnings, *timing_warnings])
        timeline.audio.timing_source = alignment.timing_source if alignment else "estimated"
        timeline.audio.alignment_coverage = alignment.coverage if alignment else 0.0
        if transcription:
            timeline.audio.transcription_model = transcription.model
            timeline.audio.transcription_language = transcription.language

        project_dir = Path(self.config.output_root) / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        subtitle_paths = write_subtitles(
            units=units,
            project_dir=project_dir,
            config=self.config.subtitles,
            width=timeline.width,
            height=timeline.height,
            aligned_tokens=alignment.tokens if alignment else None,
        )
        timeline.audio.subtitle_srt_path = subtitle_paths.get("srt", "")
        timeline.audio.subtitle_ass_path = subtitle_paths.get("ass", "")
        timeline.audio.subtitle_karaoke_ass_path = subtitle_paths.get("karaoke_ass", "")
        if transcription:
            timeline.audio.transcript_path = str(project_dir / "transcript.json")

        self._write_project(
            project_dir=project_dir,
            script_text=script_text,
            units=units,
            intents=intents,
            timeline=timeline,
            candidates_by_unit=candidates_by_unit,
            transcription=transcription,
            alignment=alignment,
        )
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
        audio_mode: str | None = None,
        burn_subtitles: bool | None = None,
        dry_run: bool = False,
    ) -> Path:
        project_path = Path(project_dir)
        discovery = self.doctor()
        ffmpeg = discovery.tools.get("ffmpeg")
        output_path = project_path / "exports" / "final.mp4"
        should_burn = (
            self.config.subtitles.burn_in_by_default
            if burn_subtitles is None
            else burn_subtitles
        )
        subtitle_path = ""
        if should_burn:
            subtitle_path = (
                timeline.audio.subtitle_karaoke_ass_path
                or timeline.audio.subtitle_ass_path
                or timeline.audio.subtitle_srt_path
            )
        command = render_timeline(
            timeline=timeline,
            ffmpeg_path=ffmpeg.executable if ffmpeg else None,
            output_path=output_path,
            voice_path=voice_path,
            audio_mode=audio_mode,
            subtitle_path=subtitle_path or None,
            dry_run=dry_run,
        )
        save_render_plan(command, project_path / "render_plan.json", timeline.audio)
        return output_path

    def _write_project(
        self,
        project_dir: Path,
        script_text: str,
        units: list[ScriptUnit],
        intents: list[VisualIntent],
        timeline: Timeline,
        candidates_by_unit: dict,
        transcription: TranscriptionResult | None,
        alignment: AlignmentResult | None,
    ) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "exports").mkdir(exist_ok=True)
        (project_dir / "script.txt").write_text(script_text, encoding="utf-8")
        self._write_json(project_dir / "script_units.json", [asdict(item) for item in units])
        self._write_json(project_dir / "visual_intents.json", [asdict(item) for item in intents])
        if transcription:
            self._write_json(project_dir / "transcript.json", transcription.to_dict())
        if alignment:
            self._write_json(project_dir / "alignment.json", alignment.to_dict())
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
        audio_blockers: list[str] = []
        if timeline.audio.mode == "source" and timeline.audio.source_audio_coverage < 0.5:
            audio_blockers.append(
                f"source audio coverage {timeline.audio.source_audio_coverage:.1%} is below 50%"
            )
        if timeline.audio.mode in {"narration", "mixed"} and timeline.audio.narration_duration <= 0:
            audio_blockers.append("narration duration is unavailable")
        subtitle_review_required = bool(
            timeline.audio.mode in {"narration", "mixed"}
            and timeline.audio.timing_source != "whisper_alignment"
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
            "audio": asdict(timeline.audio),
            "audio_blockers": audio_blockers,
            "subtitle_review_required": subtitle_review_required,
            "warnings": list(dict.fromkeys([*blocking_warnings, *timeline.audio.warnings])),
            "allow_final_export": not blocking_warnings and not low_match_segments and not audio_blockers,
        }

    @staticmethod
    def _write_json(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
