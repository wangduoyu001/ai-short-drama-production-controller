from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .v02_dialogue import extract_dialogue

SPEECH_HINTS = ["回道", "冷笑", "低声", "沉声", "心想", "暗道", "说", "问", "喊", "道", "答"]
SPATIAL_WORDS = ["画面左", "画面右", "左侧", "右侧", "前景", "后景", "中景"]


def known_speaker_names(characters: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for character in characters:
        for key in ["character_name 角色名", "character_id 角色编号"]:
            value = character.get(key)
            if value:
                names.append(str(value))
        aliases = character.get("aliases 代称", [])
        if isinstance(aliases, list):
            names.extend(str(x) for x in aliases if x)
    return unique(names)


def bind_dialogue_to_characters(text: str, characters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lines = extract_dialogue(text)
    names = known_speaker_names(characters)
    for line in lines:
        raw = line.get("speaker_name 说话人", "")
        bound = bind_speaker(raw, names, text, line.get("source_span 原文位置", [0, 0])[0])
        line["raw_speaker 原始说话人"] = raw
        line["speaker_name 说话人"] = bound["speaker_name 说话人"]
        line["speaker_bind_confidence 说话人绑定置信度"] = bound["speaker_bind_confidence 说话人绑定置信度"]
        line["speaker_bind_reason 绑定原因"] = bound["speaker_bind_reason 绑定原因"]
    return lines


def bind_speaker(raw: str, known_names: Iterable[str], source_text: str, quote_start: int) -> dict[str, Any]:
    names = list(known_names)
    raw_clean = cleanup_name(raw)
    if raw_clean in names:
        return result(raw_clean, "high 高", "raw_name_exact 原始说话人精确匹配")

    context = source_text[max(0, quote_start - 60): quote_start]
    nearest = nearest_known_name(context, names)
    if nearest:
        return result(nearest, "high 高", "nearest_known_name_before_quote 引号前最近角色名")

    if raw_clean:
        partial = partial_match(raw_clean, names)
        if partial:
            return result(partial, "medium 中", "partial_alias_match 别名局部匹配")

    fallback = names[0] if names else raw_clean or "旁白"
    return result(fallback, "low 低", "fallback_to_first_character 回退到第一角色")


def cleanup_name(value: str) -> str:
    text = value.strip()
    for hint in SPEECH_HINTS:
        text = text.replace(hint, "")
    return text.strip(" ，。；：、\n\t")[-12:]


def nearest_known_name(context: str, known_names: list[str]) -> str | None:
    best_name = None
    best_pos = -1
    for name in known_names:
        pos = context.rfind(name)
        if pos > best_pos:
            best_name = name
            best_pos = pos
    return best_name


def partial_match(raw: str, known_names: list[str]) -> str | None:
    for name in known_names:
        if raw and (raw in name or name in raw):
            return name
    return None


def result(name: str, confidence: str, reason: str) -> dict[str, str]:
    return {
        "speaker_name 说话人": name,
        "speaker_bind_confidence 说话人绑定置信度": confidence,
        "speaker_bind_reason 绑定原因": reason,
    }


def unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
