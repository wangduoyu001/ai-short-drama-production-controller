from __future__ import annotations

import json
import subprocess
import unicodedata
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from .config import TranscriptionConfig
from .models import ModelLocation, ScriptUnit
from .script_parser import build_script_units, infer_role, split_script


class TranscriptionError(RuntimeError):
    pass


@dataclass(slots=True)
class TranscriptWord:
    text: str
    start: float
    end: float
    probability: float = 0.0


@dataclass(slots=True)
class TranscriptSegment:
    segment_id: int
    text: str
    start: float
    end: float
    words: list[TranscriptWord] = field(default_factory=list)


@dataclass(slots=True)
class TranscriptionResult:
    audio_path: str
    model: str
    language: str
    duration: float
    text: str
    segments: list[TranscriptSegment]
    command: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "audio_path": self.audio_path,
            "model": self.model,
            "language": self.language,
            "duration": self.duration,
            "text": self.text,
            "segments": [
                {
                    "segment_id": segment.segment_id,
                    "text": segment.text,
                    "start": segment.start,
                    "end": segment.end,
                    "words": [asdict(word) for word in segment.words],
                }
                for segment in self.segments
            ],
            "command": self.command,
            "warnings": self.warnings,
        }


@dataclass(slots=True)
class AlignmentResult:
    units: list[ScriptUnit]
    coverage: float
    timing_source: str
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "coverage": self.coverage,
            "timing_source": self.timing_source,
            "warnings": self.warnings,
            "units": [asdict(unit) for unit in self.units],
        }


Runner = Callable[..., subprocess.CompletedProcess[str]]


def _number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, result)


def parse_whisper_payload(
    payload: dict,
    audio_path: str | Path,
    model: str,
    command: list[str] | None = None,
    duration_override: float | None = None,
) -> TranscriptionResult:
    segments: list[TranscriptSegment] = []
    for index, raw_segment in enumerate(payload.get("segments") or []):
        if not isinstance(raw_segment, dict):
            continue
        words: list[TranscriptWord] = []
        for raw_word in raw_segment.get("words") or []:
            if not isinstance(raw_word, dict):
                continue
            start = _number(raw_word.get("start"))
            end = max(start, _number(raw_word.get("end")))
            text = str(raw_word.get("word") or raw_word.get("text") or "")
            if text.strip():
                words.append(
                    TranscriptWord(
                        text=text,
                        start=round(start, 6),
                        end=round(end, 6),
                        probability=_number(raw_word.get("probability")),
                    )
                )
        start = _number(raw_segment.get("start"))
        end = max(start, _number(raw_segment.get("end")))
        segments.append(
            TranscriptSegment(
                segment_id=int(raw_segment.get("id", index)),
                text=str(raw_segment.get("text") or "").strip(),
                start=round(start, 6),
                end=round(end, 6),
                words=words,
            )
        )
    measured = max((segment.end for segment in segments), default=0.0)
    duration = max(_number(duration_override), measured)
    return TranscriptionResult(
        audio_path=str(Path(audio_path).expanduser().resolve()),
        model=model,
        language=str(payload.get("language") or ""),
        duration=round(duration, 6),
        text=str(payload.get("text") or "").strip(),
        segments=segments,
        command=list(command or []),
    )


def load_transcription_json(
    path: str | Path,
    audio_path: str | Path,
    model: str = "external-json",
    duration_override: float | None = None,
) -> TranscriptionResult:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Whisper JSON not found: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TranscriptionError(f"Whisper JSON is invalid: {source}") from exc
    if not isinstance(payload, dict):
        raise TranscriptionError("Whisper JSON root must be an object")
    return parse_whisper_payload(
        payload,
        audio_path=audio_path,
        model=model,
        duration_override=duration_override,
    )


def _checkpoint_priority(path: Path) -> tuple[int, str]:
    name = path.stem.casefold()
    priorities = (
        ("turbo", 0),
        ("large-v3", 1),
        ("medium", 2),
        ("small", 3),
        ("base", 4),
        ("tiny", 5),
    )
    for marker, priority in priorities:
        if marker in name:
            return priority, name
    return 10, name


def discover_whisper_checkpoints(locations: list[ModelLocation]) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for location in locations:
        if not location.path:
            continue
        path = Path(location.path).expanduser()
        candidates = [path] if path.is_file() else list(path.glob("*.pt")) if path.is_dir() else []
        for candidate in candidates:
            if candidate.suffix.casefold() != ".pt" or not candidate.is_file():
                continue
            resolved = candidate.resolve()
            key = str(resolved).casefold()
            if key not in seen:
                seen.add(key)
                files.append(resolved)
    files.sort(key=_checkpoint_priority)
    return files


def resolve_whisper_model(
    configured: str,
    locations: list[ModelLocation],
    allow_download: bool = False,
) -> str | None:
    checkpoints = discover_whisper_checkpoints(locations)
    preferred = configured.strip()
    if preferred:
        preferred_path = Path(preferred).expanduser()
        if preferred_path.is_file():
            return str(preferred_path.resolve())
        normalized = preferred.casefold().removesuffix(".pt")
        for checkpoint in checkpoints:
            if checkpoint.stem.casefold() == normalized:
                return str(checkpoint)
        return preferred if allow_download else None
    if checkpoints:
        return str(checkpoints[0])
    return "turbo" if allow_download else None


def build_whisper_command(
    whisper_path: str,
    audio_path: str | Path,
    model: str,
    output_dir: str | Path,
    config: TranscriptionConfig,
    initial_prompt: str = "",
) -> list[str]:
    command = [
        whisper_path,
        str(Path(audio_path).expanduser().resolve()),
        "--model",
        model,
        "--output_dir",
        str(Path(output_dir).expanduser().resolve()),
        "--output_format",
        "json",
        "--task",
        config.task,
        "--word_timestamps",
        "True" if config.word_timestamps else "False",
        "--verbose",
        "False",
    ]
    if config.language:
        command.extend(["--language", config.language])
    if config.device:
        command.extend(["--device", config.device])
    if config.fp16 is not None:
        command.extend(["--fp16", "True" if config.fp16 else "False"])
    prompt = initial_prompt.strip()[: config.initial_prompt_max_chars]
    if prompt:
        command.extend(["--initial_prompt", prompt])
    return command


def run_whisper_cli(
    whisper_path: str | None,
    audio_path: str | Path,
    model: str | None,
    output_dir: str | Path,
    config: TranscriptionConfig,
    initial_prompt: str = "",
    duration_override: float | None = None,
    runner: Runner | None = None,
) -> TranscriptionResult:
    if not whisper_path:
        raise TranscriptionError("Whisper CLI was not discovered")
    if not model:
        raise TranscriptionError(
            "No local Whisper checkpoint was discovered and model downloads are disabled"
        )
    audio = Path(audio_path).expanduser().resolve()
    if not audio.is_file():
        raise FileNotFoundError(f"Narration file not found: {audio}")
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    command = build_whisper_command(
        whisper_path=whisper_path,
        audio_path=audio,
        model=model,
        output_dir=target_dir,
        config=config,
        initial_prompt=initial_prompt,
    )
    execute = runner or subprocess.run
    try:
        completed = execute(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=config.timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise TranscriptionError(f"Whisper execution failed: {exc}") from exc
    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "unknown Whisper error").strip()
        raise TranscriptionError(f"Whisper failed: {error[-1200:]}")
    expected = target_dir / f"{audio.stem}.json"
    if expected.is_file():
        result_path = expected
    else:
        candidates = sorted(target_dir.glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)
        if not candidates:
            raise TranscriptionError("Whisper completed but no JSON output was produced")
        result_path = candidates[0]
    result = load_transcription_json(
        result_path,
        audio_path=audio,
        model=model,
        duration_override=duration_override,
    )
    result.command = command
    return result


def _clean_characters(text: str) -> list[str]:
    characters: list[str] = []
    for char in text.casefold():
        category = unicodedata.category(char)
        if char.isspace() or category.startswith(("P", "Z", "S")):
            continue
        characters.append(char)
    return characters


def _timed_characters(result: TranscriptionResult) -> list[tuple[str, float, float]]:
    timed: list[tuple[str, float, float]] = []
    for segment in result.segments:
        if segment.words:
            sources = [(word.text, word.start, word.end) for word in segment.words]
        else:
            sources = [(segment.text, segment.start, segment.end)]
        for text, start, end in sources:
            chars = _clean_characters(text)
            if not chars:
                continue
            duration = max(0.001, end - start)
            for index, char in enumerate(chars):
                char_start = start + duration * index / len(chars)
                char_end = start + duration * (index + 1) / len(chars)
                timed.append((char, round(char_start, 6), round(char_end, 6)))
    return timed


def _interpolate(anchors: list[tuple[int, float]], position: int) -> float:
    if position <= anchors[0][0]:
        return anchors[0][1]
    if position >= anchors[-1][0]:
        return anchors[-1][1]
    left = anchors[0]
    for right in anchors[1:]:
        if position <= right[0]:
            span = right[0] - left[0]
            if span <= 0:
                return max(left[1], right[1])
            ratio = (position - left[0]) / span
            return left[1] + (right[1] - left[1]) * ratio
        left = right
    return anchors[-1][1]


def align_script_to_transcription(
    script_text: str,
    transcription: TranscriptionResult,
    minimum_coverage: float = 0.55,
    max_chars: int = 26,
) -> AlignmentResult:
    parts = split_script(script_text, max_chars=max_chars)
    if not parts:
        raise ValueError("Script is empty after normalization")
    script_chars: list[str] = []
    ranges: list[tuple[int, int]] = []
    for part in parts:
        start = len(script_chars)
        script_chars.extend(_clean_characters(part))
        ranges.append((start, len(script_chars)))
    timed = _timed_characters(transcription)
    transcript_chars = [item[0] for item in timed]
    duration = max(
        transcription.duration,
        max((item[2] for item in timed), default=0.0),
        0.001,
    )
    if not script_chars or not transcript_chars:
        fallback = build_script_units(script_text, target_duration=duration)
        return AlignmentResult(
            units=fallback,
            coverage=0.0,
            timing_source="proportional_fallback",
            warnings=["Whisper output contains no usable timed characters"],
        )

    matcher = SequenceMatcher(None, script_chars, transcript_chars, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    coverage = matched / max(1, len(script_chars))
    if coverage < minimum_coverage:
        fallback = build_script_units(script_text, target_duration=duration)
        return AlignmentResult(
            units=fallback,
            coverage=round(coverage, 6),
            timing_source="proportional_fallback",
            warnings=[
                f"Script-to-transcript alignment coverage {coverage:.1%} is below "
                f"the required {minimum_coverage:.1%}"
            ],
        )

    anchor_times: dict[int, list[float]] = {0: [0.0], len(script_chars): [duration]}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            script_index = block.a + offset
            transcript_index = block.b + offset
            _char, start, end = timed[transcript_index]
            anchor_times.setdefault(script_index, []).append(start)
            anchor_times.setdefault(script_index + 1, []).append(end)
    anchors = sorted(
        (position, sum(values) / len(values))
        for position, values in anchor_times.items()
    )
    monotonic: list[tuple[int, float]] = []
    last_time = 0.0
    for position, value in anchors:
        value = max(last_time, min(duration, value))
        monotonic.append((position, value))
        last_time = value

    units: list[ScriptUnit] = []
    cursor = 0.0
    for index, (part, (char_start, char_end)) in enumerate(zip(parts, ranges), start=1):
        start = max(cursor, _interpolate(monotonic, char_start))
        end = max(start + 0.05, _interpolate(monotonic, char_end))
        if index == len(parts):
            end = duration
        end = min(duration, end)
        role = infer_role(index - 1, len(parts), part)
        units.append(
            ScriptUnit(
                unit_id=f"U{index:03d}",
                text=part,
                start=round(start, 3),
                end=round(end, 3),
                duration=round(max(0.001, end - start), 3),
                role=role,
                importance=0.9 if role in {"hook", "turn", "conclusion"} else 0.6,
            )
        )
        cursor = end
    return AlignmentResult(
        units=units,
        coverage=round(coverage, 6),
        timing_source="whisper_alignment",
    )
