from __future__ import annotations

from typing import Any

from .v02_models import Project


def attach_required_shot_bindings(project: Project) -> None:
    beat_events = ensure_beat_event_ids(project)
    first_prop = project.props[0].get("prop_id 道具编号", "PROP_01") if project.props else "PROP_01"
    for index, shot in enumerate(project.shots, 1):
        beat_id = shot.get("beat_id 节拍编号", f"B{index:03d}")
        characters = normalize_characters(shot.get("on_screen_characters 在场人物", []), project)
        shot["event_id 事件编号"] = shot.get("event_id 事件编号") or beat_events.get(beat_id) or event_id_from_clip(shot.get("clip_id 单段编号", ""), index)
        shot["character_id 角色编号"] = characters
        shot["prop_id 道具编号"] = shot.get("prop_id 道具编号") or first_prop
        shot["source_quote 原文证据"] = shot.get("source_quote 原文证据") or shot.get("source_quote 原文节拍证据", "")
    project.data["shot_plan 分镜计划"] = build_shot_plan(project)


def ensure_beat_event_ids(project: Project) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index, beat in enumerate(project.data.get("beat_map 剧情节拍表", []), 1):
        beat_id = beat.get("beat_id 节拍编号", f"B{index:03d}")
        event_id = beat.get("event_id 事件编号") or event_id_from_clip(beat.get("clip_id 片段编号", ""), index)
        beat["event_id 事件编号"] = event_id
        mapping[beat_id] = event_id
    return mapping


def build_shot_plan(project: Project) -> list[dict[str, Any]]:
    rows = []
    for shot in project.shots:
        rows.append({
            "shot_id 镜头编号": shot.get("shot_id 镜头编号", ""),
            "source_quote 原文证据": shot.get("source_quote 原文证据", shot.get("source_quote 原文节拍证据", "")),
            "event_id 事件编号": shot.get("event_id 事件编号", ""),
            "beat_id 节拍编号": shot.get("beat_id 节拍编号", ""),
            "scene_id 场景编号": shot.get("scene_id 场景编号", ""),
            "character_id 角色编号": shot.get("character_id 角色编号", ""),
            "prop_id 道具编号": shot.get("prop_id 道具编号", ""),
            "shot_purpose 镜头目的": shot.get("shot_purpose 镜头目的", ""),
            "this_clip_only 本段只拍": shot.get("this_clip_only 本段只拍", ""),
        })
    return rows


def normalize_characters(value: Any, project: Project) -> list[str]:
    if isinstance(value, list):
        ids = [str(item) for item in value if item]
    elif value:
        ids = [str(value)]
    else:
        ids = []
    known = {c.get("character_id 角色编号") for c in project.characters}
    valid = [cid for cid in ids if cid in known]
    if valid:
        return valid
    if project.characters:
        return [project.characters[0].get("character_id 角色编号", "CHAR_01")]
    return ["CHAR_01"]


def event_id_from_clip(clip_id: object, fallback_index: int) -> str:
    digits = "".join(ch for ch in str(clip_id) if ch.isdigit())
    if digits:
        return f"EV{int(digits):03d}"
    return f"EV{fallback_index:03d}"
