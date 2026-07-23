from __future__ import annotations

import math
from collections import Counter, defaultdict

from .config import MixingRules
from .models import CandidateClip, ScriptUnit, Timeline, TimelineSegment, VisualIntent


class TimelinePlanningError(RuntimeError):
    pass


def _candidate_allowed(
    candidate: CandidateClip,
    recent_sources: list[str],
    source_seconds: dict[str, float],
    project_duration: float,
    rules: MixingRules,
    segment_duration: float,
) -> bool:
    clip = candidate.clip
    if recent_sources and recent_sources[-1] == clip.source_id:
        return False
    if clip.source_id in recent_sources[-rules.source_reuse_gap :]:
        return False
    if source_seconds[clip.source_id] + segment_duration > rules.max_single_source_seconds:
        return False
    if project_duration > 0:
        future_ratio = (source_seconds[clip.source_id] + segment_duration) / project_duration
        if future_ratio > rules.max_single_source_ratio:
            return False
    if clip.duration < min(segment_duration, rules.minimum_clip_seconds):
        return False
    return True


def _choose_candidate(
    candidates: list[CandidateClip],
    used_clip_ids: set[str],
    recent_sources: list[str],
    source_seconds: dict[str, float],
    project_duration: float,
    segment_duration: float,
    rules: MixingRules,
) -> CandidateClip | None:
    ranked: list[tuple[float, CandidateClip]] = []
    used_sources = set(source_seconds)
    for candidate in candidates:
        clip = candidate.clip
        if clip.clip_id in used_clip_ids:
            continue
        if not _candidate_allowed(
            candidate,
            recent_sources,
            source_seconds,
            project_duration,
            rules,
            segment_duration,
        ):
            continue
        diversity_bonus = 0.12 if clip.source_id not in used_sources else 0.0
        duration_fit = min(1.0, clip.duration / max(segment_duration, 0.001))
        fit_bonus = duration_fit * 0.03
        ranked.append((candidate.score + diversity_bonus + fit_bonus, candidate))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _relaxed_choice(
    candidates: list[CandidateClip],
    used_clip_ids: set[str],
    recent_sources: list[str],
) -> CandidateClip | None:
    for candidate in candidates:
        if candidate.clip.clip_id in used_clip_ids:
            continue
        if recent_sources and candidate.clip.source_id == recent_sources[-1]:
            continue
        return candidate
    for candidate in candidates:
        if candidate.clip.clip_id not in used_clip_ids:
            return candidate
    return candidates[0] if candidates else None


def _candidate_rank(candidates: list[CandidateClip], selected: CandidateClip) -> int:
    for index, candidate in enumerate(candidates, start=1):
        if candidate.clip.clip_id == selected.clip.clip_id:
            return index
    return 0


def plan_timeline(
    project_id: str,
    units: list[ScriptUnit],
    intents: list[VisualIntent],
    candidates_by_unit: dict[str, list[CandidateClip]],
    rules: MixingRules,
) -> Timeline:
    if not units:
        raise TimelinePlanningError("No script units supplied")
    intent_ids = {item.unit_id for item in intents}
    missing_intents = [unit.unit_id for unit in units if unit.unit_id not in intent_ids]
    if missing_intents:
        raise TimelinePlanningError(f"Missing visual intents: {missing_intents}")

    project_duration = round(max(unit.end for unit in units), 3)
    segments: list[TimelineSegment] = []
    warnings: list[str] = []
    used_clip_ids: set[str] = set()
    recent_sources: list[str] = []
    source_seconds: dict[str, float] = defaultdict(float)

    for unit in units:
        unit_candidates = candidates_by_unit.get(unit.unit_id, [])
        if not unit_candidates:
            raise TimelinePlanningError(f"No media candidates for {unit.unit_id}: {unit.text}")

        part_count = max(1, math.ceil(unit.duration / rules.max_continuous_clip_seconds))
        part_duration = unit.duration / part_count
        unit_cursor = unit.start

        for part_index in range(part_count):
            segment_duration = round(
                unit.end - unit_cursor if part_index == part_count - 1 else part_duration,
                3,
            )
            candidate = _choose_candidate(
                unit_candidates,
                used_clip_ids,
                recent_sources,
                source_seconds,
                project_duration,
                segment_duration,
                rules,
            )
            if candidate is None:
                candidate = _relaxed_choice(unit_candidates, used_clip_ids, recent_sources)
                if candidate is None:
                    raise TimelinePlanningError(f"Unable to select media for {unit.unit_id}")
                warnings.append(
                    f"{unit.unit_id} part {part_index + 1}: diversity constraints were relaxed"
                )

            clip = candidate.clip
            usable_duration = min(segment_duration, clip.duration)
            source_start = clip.source_start
            source_end = round(source_start + usable_duration, 3)
            timeline_end = round(unit_cursor + segment_duration, 3)
            speed = round(usable_duration / segment_duration, 4) if segment_duration > 0 else 1.0
            speed = max(0.5, min(2.0, speed))

            segment = TimelineSegment(
                segment_id=f"S{len(segments) + 1:03d}",
                unit_id=unit.unit_id,
                timeline_start=round(unit_cursor, 3),
                timeline_end=timeline_end,
                source_id=clip.source_id,
                source_path=clip.source_path,
                source_start=source_start,
                source_end=source_end,
                match_score=candidate.score,
                speed=speed,
                audio_enabled=clip.has_audio,
                match_reasons=candidate.reasons,
                clip_id=clip.clip_id,
                candidate_rank=_candidate_rank(unit_candidates, candidate),
            )
            segments.append(segment)
            used_clip_ids.add(clip.clip_id)
            recent_sources.append(clip.source_id)
            source_seconds[clip.source_id] += segment_duration
            unit_cursor = timeline_end

    source_counts = Counter(segment.source_id for segment in segments)
    if len(source_counts) < rules.minimum_source_count:
        warnings.append(
            f"Only {len(source_counts)} unique sources selected; required minimum is {rules.minimum_source_count}"
        )
    for source_id, seconds in sorted(source_seconds.items()):
        ratio = seconds / project_duration if project_duration else 0
        if seconds > rules.max_single_source_seconds + 0.001:
            warnings.append(f"Source {source_id} exceeds seconds limit: {seconds:.2f}s")
        if ratio > rules.max_single_source_ratio + 0.001:
            warnings.append(f"Source {source_id} exceeds ratio limit: {ratio:.1%}")

    low_matches = [segment.segment_id for segment in segments if segment.match_score < rules.low_match_threshold]
    if low_matches:
        warnings.append(f"Low-match segments require review: {', '.join(low_matches)}")

    return Timeline(
        project_id=project_id,
        width=rules.target_width,
        height=rules.target_height,
        fps=rules.fps,
        duration=project_duration,
        segments=segments,
        warnings=warnings,
    )
