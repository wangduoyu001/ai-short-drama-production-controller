from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import DiscoveryConfig
from .models import DiscoveryReport, ModelLocation, ToolLocation


_TOOL_NAMES: dict[str, tuple[str, ...]] = {
    "ffmpeg": ("ffmpeg", "ffmpeg.exe"),
    "ffprobe": ("ffprobe", "ffprobe.exe"),
    "ollama": ("ollama", "ollama.exe"),
    "python": ("python", "python.exe", "python3"),
    "git": ("git", "git.exe"),
    "nvidia_smi": ("nvidia-smi", "nvidia-smi.exe"),
    "whisper": ("whisper", "whisper.exe"),
}

_MODEL_MARKERS: dict[str, tuple[str, ...]] = {
    "ollama": ("manifests", "blobs"),
    "huggingface": ("models--",),
    "comfyui": ("checkpoints", "clip", "vae", "loras"),
    "whisper": ("tiny.pt", "base.pt", "small.pt", "medium.pt", "large-v3.pt"),
}


def _existing(paths: Iterable[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if key not in seen and resolved.exists():
            seen.add(key)
            result.append(resolved)
    return result


def _common_roots() -> list[Path]:
    home = Path.home()
    env = os.environ
    roots = [
        home,
        home / ".ollama" / "models",
        home / ".cache" / "huggingface" / "hub",
        home / ".cache" / "whisper",
        home / "ComfyUI",
        home / "Documents" / "ComfyUI",
    ]
    for key in (
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "LOCALAPPDATA",
        "APPDATA",
        "USERPROFILE",
        "HF_HOME",
        "HUGGINGFACE_HUB_CACHE",
        "TRANSFORMERS_CACHE",
        "OLLAMA_MODELS",
        "WHISPER_MODEL_DIR",
        "COMFYUI_PATH",
    ):
        value = env.get(key)
        if value:
            roots.append(Path(value))
    return _existing(roots)


def _run_version(executable: str) -> str | None:
    commands = ([executable, "-version"], [executable, "--version"], [executable, "version"])
    for command in commands:
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=4,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        output = (completed.stdout or completed.stderr).strip().splitlines()
        if output:
            return output[0][:300]
    return None


def _discover_tool(name: str, candidates: tuple[str, ...], override: str | None) -> ToolLocation:
    if override:
        path = Path(override).expanduser()
        if path.exists():
            return ToolLocation(name=name, executable=str(path.resolve()), source="config_override", version=_run_version(str(path)))
        return ToolLocation(name=name, source="invalid_config_override")
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return ToolLocation(name=name, executable=found, source="PATH", version=_run_version(found))
    return ToolLocation(name=name)


def _limited_walk(root: Path, max_depth: int, max_entries: int):
    root_depth = len(root.parts)
    visited = 0
    for current, dirs, files in os.walk(root):
        visited += len(dirs) + len(files)
        if visited > max_entries:
            return
        current_path = Path(current)
        depth = len(current_path.parts) - root_depth
        if depth >= max_depth:
            dirs[:] = []
        dirs[:] = [item for item in dirs if item not in {".git", "node_modules", "venv", ".venv", "__pycache__"}]
        yield current_path, dirs, files


def _append_model(found: dict[str, list[ModelLocation]], group: str, path: Path, source: str, model_type: str) -> None:
    resolved = str(path.resolve())
    existing = {item.path.casefold() for item in found[group] if item.path}
    if resolved.casefold() not in existing:
        found[group].append(ModelLocation(name=path.name, path=resolved, source=source, model_type=model_type))


def _discover_models(config: DiscoveryConfig, roots: list[Path]) -> dict[str, list[ModelLocation]]:
    found: dict[str, list[ModelLocation]] = {name: [] for name in _MODEL_MARKERS}
    for group, overrides in config.model_overrides.items():
        found.setdefault(group, [])
        for raw_path in overrides:
            path = Path(raw_path).expanduser()
            if path.exists():
                _append_model(found, group, path, "config_override", group)

    for root in roots:
        lowered_root = str(root).casefold()
        if ".ollama" in lowered_root and root.is_dir():
            _append_model(found, "ollama", root, "common_root", "ollama_store")
        if "huggingface" in lowered_root and root.is_dir():
            _append_model(found, "huggingface", root, "common_root", "huggingface_cache")
        if "whisper" in lowered_root and root.is_dir():
            _append_model(found, "whisper", root, "common_root", "whisper_cache")

        try:
            walker = _limited_walk(root, config.max_scan_depth, config.max_entries_per_root)
            for current, dirs, files in walker:
                dir_names = {item.casefold() for item in dirs}
                file_names = {item.casefold() for item in files}
                current_name = current.name.casefold()

                if current_name == "models" and "comfyui" in str(current.parent).casefold():
                    _append_model(found, "comfyui", current, "filesystem_scan", "comfyui_models")
                if {"manifests", "blobs"}.issubset(dir_names):
                    _append_model(found, "ollama", current, "filesystem_scan", "ollama_store")
                if any(name.startswith("models--") for name in dirs):
                    _append_model(found, "huggingface", current, "filesystem_scan", "huggingface_cache")
                if any(marker in file_names for marker in _MODEL_MARKERS["whisper"]):
                    _append_model(found, "whisper", current, "filesystem_scan", "whisper_models")
        except (OSError, PermissionError):
            continue
    return found


def discover_environment(config: DiscoveryConfig | None = None) -> DiscoveryReport:
    config = config or DiscoveryConfig()
    extra_roots = [Path(item) for item in config.extra_search_roots if item]
    roots = _existing([*_common_roots(), *extra_roots])
    tools = {
        name: _discover_tool(name, candidates, config.tool_overrides.get(name))
        for name, candidates in _TOOL_NAMES.items()
    }
    warnings: list[str] = []
    if not tools["ffmpeg"].available:
        warnings.append("ffmpeg not found; planning works but video rendering is disabled")
    if not tools["ffprobe"].available:
        warnings.append("ffprobe not found; automatic media probing is disabled")
    if not tools["ollama"].available:
        warnings.append("ollama not found; use the built-in rule-based intent fallback or configure another provider")
    return DiscoveryReport(
        platform=f"{platform.system()} {platform.release()}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        tools=tools,
        models=_discover_models(config, roots),
        searched_roots=[str(item) for item in roots],
        warnings=warnings,
    )


def save_discovery_report(report: DiscoveryReport, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return target
