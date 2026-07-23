from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .catalog import clip_from_dict
from .config import RuntimeConfig
from .models import AudioPlan, CandidateClip, Timeline, TimelineSegment
from .reporting import build_timeline_report


class TimelineReviewError(RuntimeError):
    pass


class SegmentLockedError(TimelineReviewError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _dataclass_values(cls, payload: dict[str, Any]) -> dict[str, Any]:
    allowed = {item.name for item in fields(cls)}
    return {key: value for key, value in payload.items() if key in allowed}


def resolve_project_dir(project: str | Path, output_root: str | Path) -> Path:
    direct = Path(project).expanduser()
    if direct.is_dir():
        return direct.resolve()
    candidate = Path(output_root).expanduser() / str(project)
    if candidate.is_dir():
        return candidate.resolve()
    raise FileNotFoundError(f"Script mixer project not found: {project}")


def load_timeline(project_dir: str | Path) -> Timeline:
    project = Path(project_dir)
    path = project / "timeline.json"
    if not path.is_file():
        raise FileNotFoundError(f"Timeline not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TimelineReviewError("timeline.json root must be an object")
    raw_segments = payload.get("segments") or []
    if not isinstance(raw_segments, list):
        raise TimelineReviewError("timeline.json segments must be an array")
    segments = [
        TimelineSegment(**_dataclass_values(TimelineSegment, item))
        for item in raw_segments
        if isinstance(item, dict)
    ]
    if not segments:
        raise TimelineReviewError("timeline.json contains no segments")
    audio_payload = payload.get("audio") if isinstance(payload.get("audio"), dict) else {}
    audio = AudioPlan(**_dataclass_values(AudioPlan, audio_payload))
    duration = float(payload.get("duration") or max(item.timeline_end for item in segments))
    return Timeline(
        project_id=str(payload.get("project_id") or project.name),
        width=int(payload.get("width", 1080)),
        height=int(payload.get("height", 1920)),
        fps=int(payload.get("fps", 30)),
        duration=duration,
        segments=segments,
        audio=audio,
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


def save_timeline(project_dir: str | Path, timeline: Timeline) -> Path:
    target = Path(project_dir) / "timeline.json"
    _atomic_write_json(target, timeline.to_dict())
    return target


def load_candidates(project_dir: str | Path) -> dict[str, list[CandidateClip]]:
    path = Path(project_dir) / "candidates.json"
    if not path.is_file():
        raise FileNotFoundError(f"Candidate file not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TimelineReviewError("candidates.json root must be an object")
    result: dict[str, list[CandidateClip]] = {}
    for unit_id, rows in payload.items():
        if not isinstance(rows, list):
            continue
        candidates: list[CandidateClip] = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("clip"), dict):
                continue
            candidates.append(
                CandidateClip(
                    clip=clip_from_dict(row["clip"]),
                    score=float(row.get("score", 0.0)),
                    reasons=[str(item) for item in row.get("reasons", [])],
                )
            )
        result[str(unit_id)] = candidates
    return result


class TimelineReviewService:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def project_dir(self, project: str | Path) -> Path:
        return resolve_project_dir(project, self.config.output_root)

    def review(self, project: str | Path) -> dict[str, Any]:
        project_dir = self.project_dir(project)
        timeline = load_timeline(project_dir)
        return self._write_review_and_report(project_dir, timeline)

    def lock(self, project: str | Path, segment_id: str) -> dict[str, Any]:
        project_dir = self.project_dir(project)
        timeline = load_timeline(project_dir)
        segment = self._segment(timeline, segment_id)
        if segment.locked and segment.review_status == "approved":
            return self._write_review_and_report(project_dir, timeline)
        self._snapshot(project_dir, timeline, "lock", segment_id, {})
        segment.locked = True
        segment.review_status = "approved"
        save_timeline(project_dir, timeline)
        return self._write_review_and_report(project_dir, timeline)

    def unlock(self, project: str | Path, segment_id: str) -> dict[str, Any]:
        project_dir = self.project_dir(project)
        timeline = load_timeline(project_dir)
        segment = self._segment(timeline, segment_id)
        if not segment.locked:
            return self._write_review_and_report(project_dir, timeline)
        self._snapshot(project_dir, timeline, "unlock", segment_id, {})
        segment.locked = False
        if segment.review_status == "approved":
            segment.review_status = "unreviewed"
        save_timeline(project_dir, timeline)
        return self._write_review_and_report(project_dir, timeline)

    def replace(
        self,
        project: str | Path,
        segment_id: str,
        exclude_source_ids: list[str] | None = None,
        exclude_clip_ids: list[str] | None = None,
        keyword: str = "",
        shot_type: str = "",
        require_audio: bool | None = None,
        candidate_rank: int = 1,
        reason: str = "manual replacement",
        allow_missing_media: bool = False,
    ) -> dict[str, Any]:
        project_dir = self.project_dir(project)
        timeline = load_timeline(project_dir)
        segment = self._segment(timeline, segment_id)
        if segment.locked:
            raise SegmentLockedError(
                f"Segment {segment_id} is locked. Unlock it before replacement."
            )
        candidates_by_unit = load_candidates(project_dir)
        unit_candidates = candidates_by_unit.get(segment.unit_id, [])
        if not unit_candidates:
            raise TimelineReviewError(f"No saved candidates for unit {segment.unit_id}")
        excluded_sources = {item.casefold() for item in (exclude_source_ids or [])}
        excluded_clips = {item.casefold() for item in (exclude_clip_ids or [])}
        used_clip_ids = {
            item.clip_id.casefold()
            for item in timeline.segments
            if item.segment_id != segment.segment_id and item.clip_id
        }
        previous_source, next_source = self._neighbor_sources(timeline, segment.segment_id)
        keyword_terms = [item.casefold() for item in keyword.split() if item.strip()]
        filtered: list[tuple[int, CandidateClip]] = []
        cap = self.config.media_scan.maximum_source_process_seconds
        minimum_source_duration = max(
            0.1,
            min(
                segment.duration,
                max(self.config.mixing.minimum_clip_seconds, segment.duration * 0.5),
            ),
        )
        for original_rank, candidate in enumerate(unit_candidates, start=1):
            clip = candidate.clip
            if not clip.usable:
                continue
            if clip.clip_id.casefold() == segment.clip_id.casefold() and segment.clip_id:
                continue
            if (
                clip.source_id == segment.source_id
                and abs(clip.source_start - segment.source_start) < 0.001
            ):
                continue
            if clip.source_id.casefold() in excluded_sources:
                continue
            if clip.clip_id.casefold() in excluded_clips or clip.clip_id.casefold() in used_clip_ids:
                continue
            if previous_source and clip.source_id == previous_source:
                continue
            if next_source and clip.source_id == next_source:
                continue
            if require_audio is not None and clip.has_audio is not require_audio:
                continue
            if shot_type and shot_type.casefold() not in clip.shot_type.casefold():
                continue
            searchable = " ".join(
                [clip.description, *clip.tags, *clip.emotions, clip.shot_type, clip.camera_motion]
            ).casefold()
            if keyword_terms and not all(term in searchable for term in keyword_terms):
                continue
            if not allow_missing_media and not Path(clip.source_path).is_file():
                continue
            if clip.duration + 0.001 < minimum_source_duration:
                continue
            if cap > 0 and clip.source_start >= cap:
                continue
            filtered.append((original_rank, candidate))
        if not filtered:
            raise TimelineReviewError(
                "No replacement candidate satisfies the filters, neighbor diversity, duration, "
                "media existence, and source-processing window"
            )
        if candidate_rank < 1 or candidate_rank > len(filtered):
            raise TimelineReviewError(
                f"candidate_rank must be between 1 and {len(filtered)}, got {candidate_rank}"
            )
        original_rank, selected = filtered[candidate_rank - 1]
        clip = selected.clip
        self._snapshot(
            project_dir,
            timeline,
            "replace",
            segment_id,
            {
                "old_clip_id": segment.clip_id,
                "new_clip_id": clip.clip_id,
                "reason": reason,
                "filtered_candidate_rank": candidate_rank,
                "original_candidate_rank": original_rank,
            },
        )
        target_duration = max(0.001, segment.duration)
        source_available = clip.duration
        if cap > 0:
            source_available = min(source_available, max(0.0, cap - clip.source_start))
        usable_duration = min(target_duration, source_available)
        if usable_duration <= 0:
            raise TimelineReviewError("Replacement candidate has no usable duration")
        segment.clip_id = clip.clip_id
        segment.source_id = clip.source_id
        segment.source_path = clip.source_path
        segment.source_start = round(clip.source_start, 3)
        segment.source_end = round(clip.source_start + usable_duration, 3)
        segment.match_score = selected.score
        segment.match_reasons = selected.reasons
        segment.speed = round(max(0.5, min(2.0, usable_duration / target_duration)), 4)
        segment.audio_enabled = clip.has_audio
        segment.review_status = "replaced"
        segment.replacement_reason = reason
        segment.candidate_rank = original_rank
        save_timeline(project_dir, timeline)
        result = self._write_review_and_report(project_dir, timeline)
        result["replacement"] = {
            "segment_id": segment_id,
            "clip_id": clip.clip_id,
            "source_id": clip.source_id,
            "source_path": clip.source_path,
            "source_start": segment.source_start,
            "source_end": segment.source_end,
            "match_score": selected.score,
            "candidate_rank": original_rank,
            "reason": reason,
        }
        return result

    def rollback(self, project: str | Path) -> dict[str, Any]:
        project_dir = self.project_dir(project)
        log_path = project_dir / "revision_log.json"
        if not log_path.is_file():
            raise TimelineReviewError("No revisions are available for rollback")
        payload = json.loads(log_path.read_text(encoding="utf-8"))
        revisions = payload.get("revisions") if isinstance(payload, dict) else None
        if not isinstance(revisions, list) or not revisions:
            raise TimelineReviewError("No revisions are available for rollback")
        record = revisions.pop()
        snapshot_path = project_dir / str(record["snapshot_path"])
        restored = load_timeline(snapshot_path.parent) if snapshot_path.name == "timeline.json" else None
        if restored is None:
            raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
            segments = [
                TimelineSegment(**_dataclass_values(TimelineSegment, item))
                for item in raw.get("segments", [])
                if isinstance(item, dict)
            ]
            audio_payload = raw.get("audio") if isinstance(raw.get("audio"), dict) else {}
            restored = Timeline(
                project_id=str(raw.get("project_id") or project_dir.name),
                width=int(raw.get("width", 1080)),
                height=int(raw.get("height", 1920)),
                fps=int(raw.get("fps", 30)),
                duration=float(raw.get("duration") or max(item.timeline_end for item in segments)),
                segments=segments,
                audio=AudioPlan(**_dataclass_values(AudioPlan, audio_payload)),
                warnings=[str(item) for item in raw.get("warnings", [])],
            )
        save_timeline(project_dir, restored)
        payload["revisions"] = revisions
        _atomic_write_json(log_path, payload)
        rollback_path = project_dir / "rollback_log.json"
        rollback_payload = (
            json.loads(rollback_path.read_text(encoding="utf-8"))
            if rollback_path.is_file()
            else {"rollbacks": []}
        )
        rollback_payload.setdefault("rollbacks", []).append(
            {
                "rolled_back_at": _utc_now(),
                "revision": record,
            }
        )
        _atomic_write_json(rollback_path, rollback_payload)
        result = self._write_review_and_report(project_dir, restored)
        result["rolled_back_revision"] = record
        return result

    def _segment(self, timeline: Timeline, segment_id: str) -> TimelineSegment:
        for segment in timeline.segments:
            if segment.segment_id == segment_id:
                return segment
        raise TimelineReviewError(f"Timeline segment not found: {segment_id}")

    @staticmethod
    def _neighbor_sources(timeline: Timeline, segment_id: str) -> tuple[str, str]:
        for index, segment in enumerate(timeline.segments):
            if segment.segment_id != segment_id:
                continue
            previous_source = timeline.segments[index - 1].source_id if index > 0 else ""
            next_source = (
                timeline.segments[index + 1].source_id
                if index + 1 < len(timeline.segments)
                else ""
            )
            return previous_source, next_source
        return "", ""

    def _snapshot(
        self,
        project_dir: Path,
        timeline: Timeline,
        action: str,
        segment_id: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        log_path = project_dir / "revision_log.json"
        payload = (
            json.loads(log_path.read_text(encoding="utf-8"))
            if log_path.is_file()
            else {"revisions": []}
        )
        revisions = payload.setdefault("revisions", [])
        sequence = max((int(item.get("sequence", 0)) for item in revisions), default=0) + 1
        revision_id = f"R{sequence:04d}"
        snapshot_relative = Path("revisions") / f"{revision_id}_{action}_{segment_id}.json"
        snapshot_path = project_dir / snapshot_relative
        _atomic_write_json(snapshot_path, timeline.to_dict())
        record = {
            "sequence": sequence,
            "revision_id": revision_id,
            "created_at": _utc_now(),
            "action": action,
            "segment_id": segment_id,
            "snapshot_path": str(snapshot_relative).replace("\\", "/"),
            "details": details,
        }
        revisions.append(record)
        _atomic_write_json(log_path, payload)
        return record

    def _write_review_and_report(
        self,
        project_dir: Path,
        timeline: Timeline,
    ) -> dict[str, Any]:
        candidates_by_unit: dict[str, list[CandidateClip]] = {}
        candidate_error = ""
        try:
            candidates_by_unit = load_candidates(project_dir)
        except (FileNotFoundError, TimelineReviewError, json.JSONDecodeError) as exc:
            candidate_error = str(exc)
        cap = self.config.media_scan.maximum_source_process_seconds
        segment_rows: list[dict[str, Any]] = []
        for segment in timeline.segments:
            segment_rows.append(
                {
                    "segment_id": segment.segment_id,
                    "unit_id": segment.unit_id,
                    "timeline_start": segment.timeline_start,
                    "timeline_end": segment.timeline_end,
                    "duration": segment.duration,
                    "clip_id": segment.clip_id,
                    "source_id": segment.source_id,
                    "source_path": segment.source_path,
                    "source_start": segment.source_start,
                    "source_end": segment.source_end,
                    "source_exists": Path(segment.source_path).is_file(),
                    "within_source_window": cap <= 0 or segment.source_end <= cap + 0.001,
                    "match_score": segment.match_score,
                    "candidate_rank": segment.candidate_rank,
                    "candidate_count": len(candidates_by_unit.get(segment.unit_id, [])),
                    "locked": segment.locked,
                    "review_status": segment.review_status,
                    "replacement_reason": segment.replacement_reason,
                    "audio_enabled": segment.audio_enabled,
                }
            )
        review_payload = {
            "project_id": timeline.project_id,
            "generated_at": _utc_now(),
            "segment_count": len(timeline.segments),
            "locked_segment_count": sum(item.locked for item in timeline.segments),
            "unreviewed_segment_count": sum(
                item.review_status == "unreviewed" for item in timeline.segments
            ),
            "replaced_segment_count": sum(
                item.review_status == "replaced" for item in timeline.segments
            ),
            "candidate_error": candidate_error,
            "segments": segment_rows,
        }
        _atomic_write_json(project_dir / "review.json", review_payload)
        report = build_timeline_report(timeline, self.config, review=review_payload)
        _atomic_write_json(project_dir / "report.json", report)
        return {
            "project_dir": str(project_dir),
            "timeline_path": str(project_dir / "timeline.json"),
            "review_path": str(project_dir / "review.json"),
            "report_path": str(project_dir / "report.json"),
            "review": review_payload,
            "allow_final_export": report["allow_final_export"],
            "blockers": [
                *report.get("warnings", []),
                *report.get("audio_blockers", []),
            ],
        }
