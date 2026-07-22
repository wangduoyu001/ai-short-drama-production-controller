from __future__ import annotations

import re
from pathlib import Path

from .models import ScriptUnit


_SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？!?；;])\s*|\n+")
_CLAUSE_BOUNDARY = re.compile(r"(?<=[，、,:：])\s*")


def normalize_script(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _visible_length(text: str) -> int:
    return len(re.sub(r"\s|[，。！？!?；;、,:：\"'“”‘’（）()【】]", "", text))


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    if _visible_length(sentence) <= max_chars:
        return [sentence.strip()]
    clauses = [item.strip() for item in _CLAUSE_BOUNDARY.split(sentence) if item.strip()]
    if len(clauses) <= 1:
        return [sentence.strip()]
    chunks: list[str] = []
    buffer = ""
    for clause in clauses:
        candidate = f"{buffer}{clause}" if buffer else clause
        if buffer and _visible_length(candidate) > max_chars:
            chunks.append(buffer.strip())
            buffer = clause
        else:
            buffer = candidate
    if buffer.strip():
        chunks.append(buffer.strip())
    return chunks


def split_script(text: str, max_chars: int = 26) -> list[str]:
    normalized = normalize_script(text)
    if not normalized:
        return []
    sentences = [item.strip() for item in _SENTENCE_BOUNDARY.split(normalized) if item.strip()]
    units: list[str] = []
    for sentence in sentences:
        units.extend(_split_long_sentence(sentence, max_chars=max_chars))
    return units


def estimate_duration(text: str, chinese_chars_per_second: float = 4.2, minimum: float = 0.8) -> float:
    length = max(_visible_length(text), 1)
    punctuation_pause = 0.0
    punctuation_pause += 0.18 * len(re.findall(r"[，、,:：]", text))
    punctuation_pause += 0.35 * len(re.findall(r"[。！？!?；;]", text))
    return round(max(minimum, length / chinese_chars_per_second + punctuation_pause), 3)


def infer_role(index: int, total: int, text: str) -> str:
    if index == 0:
        return "hook"
    if index == total - 1:
        return "conclusion"
    if re.search(r"但是|然而|其实|却|真正|问题是|关键是|不是", text):
        return "turn"
    if re.search(r"第一|第二|第三|首先|其次|最后|步骤|方法", text):
        return "explanation"
    return "body"


def build_script_units(text: str, target_duration: float | None = None) -> list[ScriptUnit]:
    parts = split_script(text)
    if not parts:
        raise ValueError("Script is empty after normalization")
    raw_durations = [estimate_duration(item) for item in parts]
    raw_total = sum(raw_durations)
    scale = target_duration / raw_total if target_duration and raw_total > 0 else 1.0

    units: list[ScriptUnit] = []
    cursor = 0.0
    for index, (part, raw_duration) in enumerate(zip(parts, raw_durations, strict=True), start=1):
        duration = round(raw_duration * scale, 3)
        start = round(cursor, 3)
        end = round(start + duration, 3)
        role = infer_role(index - 1, len(parts), part)
        importance = 0.9 if role in {"hook", "turn", "conclusion"} else 0.6
        units.append(
            ScriptUnit(
                unit_id=f"U{index:03d}",
                text=part,
                start=start,
                end=end,
                duration=duration,
                role=role,
                importance=importance,
            )
        )
        cursor = end
    return units


def load_script(path: str | Path) -> str:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Script file not found: {source}")
    return source.read_text(encoding="utf-8")
