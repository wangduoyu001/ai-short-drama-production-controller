from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from .config import SubtitleConfig
from .models import ScriptUnit
from .transcription import AlignedToken


@dataclass(slots=True)
class SubtitleCue:
    index: int
    start: float
    end: float
    text: str


def _visible_length(text: str) -> int:
    return len(re.sub(r"\s", "", text))


def wrap_subtitle_text(text: str, max_chars: int, max_lines: int) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean or max_chars <= 0 or max_lines <= 1 or _visible_length(clean) <= max_chars:
        return clean
    clauses = [item for item in re.split(r"(?<=[，。！？!?；;、,:：])", clean) if item]
    lines: list[str] = []
    buffer = ""
    for clause in clauses:
        candidate = f"{buffer}{clause}" if buffer else clause
        if buffer and _visible_length(candidate) > max_chars:
            lines.append(buffer.strip())
            buffer = clause
        else:
            buffer = candidate
    if buffer.strip():
        lines.append(buffer.strip())
    while len(lines) > max_lines:
        tail = lines.pop()
        lines[-1] = f"{lines[-1]}{tail}"
    if len(lines) == 1 and _visible_length(lines[0]) > max_chars:
        raw = lines[0]
        midpoint = max_chars
        lines = [raw[:midpoint], raw[midpoint:]]
        while len(lines) > max_lines:
            tail = lines.pop()
            lines[-1] += tail
    return "\n".join(item.strip() for item in lines if item.strip())


def build_subtitle_cues(units: list[ScriptUnit], config: SubtitleConfig) -> list[SubtitleCue]:
    cues: list[SubtitleCue] = []
    for index, unit in enumerate(units, start=1):
        start = max(0.0, unit.start)
        end = max(start + config.minimum_cue_seconds, unit.end)
        cues.append(
            SubtitleCue(
                index=index,
                start=round(start, 3),
                end=round(end, 3),
                text=wrap_subtitle_text(
                    unit.text,
                    max_chars=config.max_chars_per_line,
                    max_lines=config.max_lines,
                ),
            )
        )
    return cues


def _srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _ass_timestamp(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    secs, cents = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cents:02d}"


def write_srt(cues: list[SubtitleCue], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    for cue in cues:
        blocks.append(
            f"{cue.index}\n{_srt_timestamp(cue.start)} --> {_srt_timestamp(cue.end)}\n{cue.text}\n"
        )
    target.write_text("\n".join(blocks), encoding="utf-8-sig")
    return target


def _ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def _ass_header(config: SubtitleConfig, width: int, height: int) -> str:
    alignment = max(1, min(9, config.alignment))
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{config.font_name},{config.font_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,{config.bold},0,0,0,100,100,0,0,1,{config.outline},{config.shadow},{alignment},{config.margin_left},{config.margin_right},{config.margin_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_ass(
    cues: list[SubtitleCue],
    path: str | Path,
    config: SubtitleConfig,
    width: int,
    height: int,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    events = [
        f"Dialogue: 0,{_ass_timestamp(cue.start)},{_ass_timestamp(cue.end)},Default,,0,0,0,,{_ass_escape(cue.text)}"
        for cue in cues
    ]
    target.write_text(
        _ass_header(config, width, height) + "\n".join(events) + "\n",
        encoding="utf-8-sig",
    )
    return target


def write_karaoke_ass(
    tokens: list[AlignedToken],
    path: str | Path,
    config: SubtitleConfig,
    width: int,
    height: int,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    grouped: OrderedDict[str, list[AlignedToken]] = OrderedDict()
    for token in tokens:
        grouped.setdefault(token.unit_id, []).append(token)
    events: list[str] = []
    for unit_tokens in grouped.values():
        if not unit_tokens:
            continue
        start = unit_tokens[0].start
        end = max(token.end for token in unit_tokens)
        parts: list[str] = []
        for token in unit_tokens:
            centiseconds = max(1, int(round((token.end - token.start) * 100)))
            parts.append(r"{\k" + str(centiseconds) + "}" + _ass_escape(token.text))
        events.append(
            f"Dialogue: 0,{_ass_timestamp(start)},{_ass_timestamp(end)},Default,,0,0,0,,{''.join(parts)}"
        )
    target.write_text(
        _ass_header(config, width, height) + "\n".join(events) + "\n",
        encoding="utf-8-sig",
    )
    return target


def write_subtitles(
    units: list[ScriptUnit],
    project_dir: str | Path,
    config: SubtitleConfig,
    width: int,
    height: int,
    aligned_tokens: list[AlignedToken] | None = None,
) -> dict[str, str]:
    if not config.enabled:
        return {}
    cues = build_subtitle_cues(units, config)
    subtitle_dir = Path(project_dir) / "subtitles"
    result: dict[str, str] = {}
    formats = {item.casefold() for item in config.formats}
    if "srt" in formats:
        result["srt"] = str(write_srt(cues, subtitle_dir / "captions.srt"))
    if "ass" in formats:
        result["ass"] = str(
            write_ass(
                cues,
                subtitle_dir / "captions.ass",
                config=config,
                width=width,
                height=height,
            )
        )
        if aligned_tokens:
            result["karaoke_ass"] = str(
                write_karaoke_ass(
                    aligned_tokens,
                    subtitle_dir / "captions.karaoke.ass",
                    config=config,
                    width=width,
                    height=height,
                )
            )
    return result
