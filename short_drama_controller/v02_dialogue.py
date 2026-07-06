from __future__ import annotations

from typing import Any

QUOTE_PAIRS = [("“", "”"), ('"', '"'), ("「", "」"), ("『", "』")]


def extract_dialogue(text: str) -> list[dict[str, Any]]:
    spans = find_quoted_spans(text)
    lines: list[dict[str, Any]] = []
    for idx, (start, end, value) in enumerate(spans, start=1):
        ctx = text[max(0, start - 28): start]
        speaker = infer_speaker(ctx)
        mode = "os_voice OS画外音" if any(x in ctx for x in ["心想", "暗道", "内心", "OS", "旁白"]) else "spoken_dialogue 出口对白"
        lines.append({
            "dialogue_id 对白编号": f"DL{idx:03d}",
            "speaker_name 说话人": speaker,
            "speaker_mode 发声模式": mode,
            "text 台词": value.strip(),
            "mouth_state 嘴型状态": "all_closed 全员闭口" if mode.startswith("os_voice") else "speaker_open 说话人开口",
            "source_span 原文位置": [start, end],
        })
    return lines


def find_quoted_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for left, right in QUOTE_PAIRS:
        start = 0
        while True:
            i = text.find(left, start)
            if i < 0:
                break
            j = text.find(right, i + 1)
            if j < 0 or (left == right and j == i):
                break
            spans.append((i, j + 1, text[i + 1:j]))
            start = j + 1
    return sorted(spans, key=lambda x: x[0])


def infer_speaker(context: str) -> str:
    verbs = ["回道", "冷笑", "心想", "暗道", "说", "问", "喊", "道"]
    for verb in verbs:
        pos = context.rfind(verb)
        if pos > 0:
            prefix = context[:pos].strip(" ，。；：、\n\t")
            token = prefix[-8:].strip(" ，。；：、\n\t")
            return token or "旁白"
    return "主角" if "我" in context else "旁白"


def force_reverse_shot_units(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for line in lines:
        is_spoken = line["speaker_mode 发声模式"].startswith("spoken_dialogue")
        units.append({
            "unit_id 单元编号": f"DU{len(units)+1:03d}",
            "speaker_name 说话人": line["speaker_name 说话人"],
            "speaker_mode 发声模式": line["speaker_mode 发声模式"],
            "dialogue_line 出口对白": line["text 台词"] if is_spoken else "无",
            "os_line 画外音": line["text 台词"] if not is_spoken else "无",
            "mouth_state 嘴型状态": line["mouth_state 嘴型状态"],
        })
    return units
