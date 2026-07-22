from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .catalog import MediaCatalog
from .config import RuntimeConfig
from .environment import discover_environment, save_discovery_report
from .intent import IntentProvider, build_visual_intents
from .models import DiscoveryReport, ScriptUnit, Timeline, VisualIntent
from .planner import plan_timeline
from .render import render_timeline, save_render_plan
from .retrieval import HybridRetriever, VectorSearchProvider
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

    def doctor(self) -> DiscoveryReport:
        report = discover_environment(self.config.discovery)
        save_discovery_report(report, self.config.discovery_report_path)
        return report

    def plan(
        self,
        script_text: str,
        project_id: str | None = None,
        target_duration: float | None = None,
    ) -> tuple[Timeline, Path]:
        project_id = project_id or datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
        units = build_script_units(script_text, target_duration=target_duration)
        intents = build_visual_intents(units, provider=self.intent_provider)
        clips = self.catalog.list_clips(usable_only=True)
        if not clips:
            raise RuntimeError(
                "Media catalog is empty. Import a clip manifest or run a future analyzer adapter first."
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

    @staticmethod
    def _build_report(timeline: Timeline) -> dict:
        source_seconds: dict[str, float] = {}
        low_match_segments: list[str] = []
        for segment in timeline.segments:
            source_seconds[segment.source_id] = source_seconds.get(segment.source_id, 0.0) + segment.duration
            if segment.match_score < 0.45:
                low_match_segments.append(segment.segment_id)
        highest_source_ratio = (
            max(source_seconds.values()) / timeline.duration if source_seconds and timeline.duration else 0.0
        )
        return {
            "project_id": timeline.project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "duration": timeline.duration,
            "segment_count": len(timeline.segments),
            "unique_source_count": len(source_seconds),
            "highest_single_source_ratio": round(highest_source_ratio, 4),
            "source_seconds": {key: round(value, 3) for key, value in source_seconds.items()},
            "low_match_segments": low_match_segments,
            "warnings": timeline.warnings,
            "allow_final_export": not timeline.warnings and not low_match_segments,
        }

    @staticmethod
    def _write_json(path: Path, payload) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
