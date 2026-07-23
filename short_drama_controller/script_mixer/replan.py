from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .models import ScriptUnit, VisualIntent
from .planner import plan_timeline
from .review import (
    TimelineReviewError,
    TimelineReviewService,
    load_candidates,
    load_timeline,
    resolve_project_dir,
    save_timeline,
)


def _values(cls, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in payload.items() if key in allowed}


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required project file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TimelineReviewError(f"{path.name} must contain a JSON array")
    return [item for item in payload if isinstance(item, dict)]


class ProjectReplanner:
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self.review_service = TimelineReviewService(config)

    def replan(self, project: str | Path) -> dict[str, Any]:
        project_dir = resolve_project_dir(project, self.config.output_root)
        current = load_timeline(project_dir)
        units = [
            ScriptUnit(**_values(ScriptUnit, item))
            for item in _load_rows(project_dir / "script_units.json")
        ]
        intents = [
            VisualIntent(**_values(VisualIntent, item))
            for item in _load_rows(project_dir / "visual_intents.json")
        ]
        candidates = load_candidates(project_dir)
        locked = {
            segment.segment_id: segment
            for segment in current.segments
            if segment.locked
        }
        self.review_service._snapshot(
            project_dir,
            current,
            "replan",
            "ALL",
            {
                "locked_segments": sorted(locked),
                "unlocked_segment_count": len(current.segments) - len(locked),
            },
        )
        replanned = plan_timeline(
            project_id=current.project_id,
            units=units,
            intents=intents,
            candidates_by_unit=candidates,
            rules=self.config.mixing,
            locked_segments=locked,
        )
        replanned.width = current.width
        replanned.height = current.height
        replanned.fps = current.fps
        replanned.duration = current.duration
        replanned.audio = current.audio
        save_timeline(project_dir, replanned)
        result = self.review_service._write_review_and_report(project_dir, replanned)
        result["replan"] = {
            "project_id": current.project_id,
            "locked_segments_preserved": sorted(locked),
            "segment_count": len(replanned.segments),
            "changed_segments": [
                new.segment_id
                for old, new in zip(current.segments, replanned.segments)
                if (
                    old.clip_id != new.clip_id
                    or old.source_id != new.source_id
                    or abs(old.source_start - new.source_start) > 0.001
                )
            ],
        }
        return result
