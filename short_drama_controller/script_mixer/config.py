from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class DiscoveryConfig:
    tool_overrides: dict[str, str] = field(default_factory=dict)
    model_overrides: dict[str, list[str]] = field(default_factory=dict)
    extra_search_roots: list[str] = field(default_factory=list)
    max_scan_depth: int = 3
    max_entries_per_root: int = 5000


@dataclass(slots=True)
class MixingRules:
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 30
    minimum_source_count: int = 8
    preferred_source_count: int = 12
    max_single_source_ratio: float = 0.15
    max_single_source_seconds: float = 4.0
    max_continuous_clip_seconds: float = 3.0
    minimum_clip_seconds: float = 0.7
    source_reuse_gap: int = 3
    low_match_threshold: float = 0.45
    allow_missing_media_files_during_planning: bool = True


@dataclass(slots=True)
class RuntimeConfig:
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    mixing: MixingRules = field(default_factory=MixingRules)
    database_path: str = ".runtime/script_mixer/media.db"
    discovery_report_path: str = ".runtime/script_mixer/discovery.json"
    output_root: str = "outputs/script_mixer"
    text_model: str = ""
    vision_model: str = ""
    embedding_model: str = ""
    speech_model: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _merge_dataclass(instance: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        if not hasattr(instance, key):
            continue
        current = getattr(instance, key)
        if hasattr(current, "__dataclass_fields__") and isinstance(value, dict):
            _merge_dataclass(current, value)
        else:
            setattr(instance, key, value)
    return instance


def load_config(path: str | Path | None = None) -> RuntimeConfig:
    config = RuntimeConfig()
    if path is None:
        return config
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Config file not found: {source}")
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Config root must be a JSON object")
    return _merge_dataclass(config, payload)


def write_default_config(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing config: {target}")
    target.write_text(
        json.dumps(RuntimeConfig().to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
