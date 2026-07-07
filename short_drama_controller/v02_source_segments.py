from __future__ import annotations

import re
from typing import Any

from .v02_models import Project


def build_source_segments(project: Project) -> None:
    text = str(project.data.get("source_text 原文", ""))
    segments = []
    for index, quote in enumerate(split_source_text(text), 1):
        segments.append({
            "segment_id 原文段落编号": f"SEG_{index:03d}",
            "source_quote 原文句子": quote,
            "char_count 字数": len(quote),
            "dialogue_candidates 对白候选": extract_dialogue(quote),
            "used_in_event_blocks 使用事件段": [],
            "used_in_beats 使用节拍": [],
            "used_in_shots 使用镜头": [],
            "coverage_status 覆盖状态": "pending 待覆盖",
        })
    project.data["source_segments 原文切片"] = segments


def attach_source_coverage(project: Project) -> None:
    segments = project.data.get("source_segments 原文切片", [])
    if not segments:
        build_source_segments(project)
        segments = project.data.get("source_segments 原文切片", [])

    event_blocks = project.data.get("event_blocks 事件段落拆分", [])
    beat_map = project.data.get("beat_map 剧情节拍表", [])
    shots = project.data.get("shots 分镜列表", [])

    for segment in segments:
        quote = str(segment.get("source_quote 原文句子", ""))
        segment["used_in_event_blocks 使用事件段"] = match_records(quote, event_blocks, "block_id 段落编号")
        segment["used_in_beats 使用节拍"] = match_records(quote, beat_map, "beat_id 节拍编号")
        segment["used_in_shots 使用镜头"] = match_records(quote, shots, "shot_id 镜头编号")
        segment["coverage_status 覆盖状态"] = infer_status(segment)

    project.data["source_coverage 原文覆盖"] = summarize_coverage(segments)


def split_source_text(text: str) -> list[str]:
    compact = " ".join(text.split())
    if not compact:
        return ["空输入"]
    parts = re.split(r"(?<=[。！？!?；;])", compact)
    lines = [part.strip() for part in parts if part.strip()]
    if len(lines) <= 1 and len(compact) > 120:
        lines = [compact[i:i + 80] for i in range(0, len(compact), 80)]
    return lines


def extract_dialogue(text: str) -> list[str]:
    quoted = re.findall(r"[“\"]([^”\"]+)[”\"]", text)
    colon = re.findall(r"[：:]([^。！？!?；;]+)", text)
    return [item.strip() for item in quoted + colon if item.strip()]


def match_records(quote: str, records: list[dict[str, Any]], id_key: str) -> list[str]:
    if not quote:
        return []
    matches = []
    probe = quote[:24]
    for record in records:
        text = " ".join(str(value) for value in record.values())
        if quote in text or probe in text:
            record_id = str(record.get(id_key, ""))
            if record_id:
                matches.append(record_id)
    return matches


def infer_status(segment: dict[str, Any]) -> str:
    if segment.get("used_in_shots 使用镜头"):
        return "covered_by_shot 已进入镜头"
    if segment.get("used_in_beats 使用节拍"):
        return "covered_by_beat 已进入节拍"
    if segment.get("used_in_event_blocks 使用事件段"):
        return "covered_by_event 已进入事件段"
    return "missing 未覆盖"


def summarize_coverage(segments: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(segments)
    missing = [s.get("segment_id 原文段落编号", "") for s in segments if s.get("coverage_status 覆盖状态") == "missing 未覆盖"]
    covered = total - len(missing)
    return {
        "total_segments 总切片数": total,
        "covered_segments 已覆盖切片数": covered,
        "missing_segments 未覆盖切片": missing,
        "coverage_ratio 覆盖比例": round(covered / total, 3) if total else 0,
    }
