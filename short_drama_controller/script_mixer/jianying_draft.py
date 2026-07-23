from __future__ import annotations

import importlib
import os
import platform
from pathlib import Path
from typing import Any

from .config import RuntimeConfig


class JianyingDraftError(RuntimeError):
    pass


def discover_jianying_draft_roots(configured: str | Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    local_app_data = os.environ.get("LOCALAPPDATA")
    app_data = os.environ.get("APPDATA")
    if local_app_data:
        base = Path(local_app_data)
        candidates.extend(
            [
                base / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft",
                base / "JianyingPro Drafts",
            ]
        )
    if app_data:
        base = Path(app_data)
        candidates.extend(
            [
                base / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft",
                base / "JianyingPro Drafts",
            ]
        )
    home = Path.home()
    candidates.extend(
        [
            home / "Movies" / "JianyingPro Drafts",
            home / "Documents" / "JianyingPro Drafts",
            home / "Library" / "Application Support" / "JianyingPro" / "User Data" / "Projects" / "com.lveditor.draft",
        ]
    )
    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if key in seen or not resolved.is_dir():
            continue
        seen.add(key)
        result.append(resolved)
    return result


def jianying_status(config: RuntimeConfig) -> dict[str, Any]:
    try:
        module = importlib.import_module("pyJianYingDraft")
        dependency_available = True
        dependency_version = str(getattr(module, "__version__", "unknown"))
        dependency_error = ""
    except Exception as exc:
        dependency_available = False
        dependency_version = ""
        dependency_error = f"{type(exc).__name__}: {exc}"
    roots = discover_jianying_draft_roots(config.edit_package.jianying_draft_root)
    return {
        "platform": platform.system(),
        "dependency_available": dependency_available,
        "dependency_version": dependency_version,
        "dependency_error": dependency_error,
        "configured_root": config.edit_package.jianying_draft_root,
        "discovered_roots": [str(path) for path in roots],
        "ready": dependency_available and bool(roots),
        "install_command": 'python -m pip install -e ".[jianying]"',
        "notes": [
            "标准剪映编辑包不依赖pyJianYingDraft，草稿生成失败时仍可手工导入",
            "剪映私有草稿格式可能随版本变化，实际打开后仍需人工确认",
        ],
    }


def _seconds(value: float) -> str:
    return f"{max(0.0, value):.6f}s"


def _unique_draft_name(root: Path, desired: str) -> str:
    safe = "".join(character if character not in '\\/:*?\"<>|' else "_" for character in desired)
    safe = safe.strip().strip(".") or "AI粗剪"
    candidate = safe
    index = 2
    while (root / candidate).exists():
        candidate = f"{safe}_{index}"
        index += 1
    return candidate


def _add_track(script: Any, draft: Any, track_type: Any, name: str, relative_index: int = 0) -> None:
    try:
        script.add_track(track_type, track_name=name, relative_index=relative_index)
    except TypeError:
        try:
            script.add_track(track_type, name, relative_index)
        except TypeError:
            script.add_track(track_type, name)


def _add_segment(script: Any, segment: Any, track_name: str) -> None:
    try:
        script.add_segment(segment, track_name=track_name)
    except TypeError:
        script.add_segment(segment, track_name)


def _set_audio_volume(segment: Any, volume: float) -> None:
    value = max(0.0, float(volume))
    try:
        segment.add_keyframe("0s", value)
    except Exception:
        try:
            setattr(segment, "volume", value)
        except Exception:
            return


def _source_volume(manifest: dict[str, Any], config: RuntimeConfig) -> float:
    mode = str(manifest.get("audio_mode", "mute")).casefold()
    if mode == "source":
        return config.audio.source_volume
    if mode == "mixed":
        return config.audio.mixed_source_volume
    return 0.0


def create_jianying_draft(
    manifest: dict[str, Any],
    config: RuntimeConfig,
    draft_root: str | Path | None = None,
    draft_name: str | None = None,
    draft_module: Any | None = None,
) -> dict[str, Any]:
    draft = draft_module
    if draft is None:
        try:
            draft = importlib.import_module("pyJianYingDraft")
        except Exception as exc:
            raise JianyingDraftError(
                'pyJianYingDraft is unavailable. Run: python -m pip install -e ".[jianying]"'
            ) from exc

    configured_root = draft_root or config.edit_package.jianying_draft_root
    roots = discover_jianying_draft_roots(configured_root)
    if not roots:
        raise JianyingDraftError(
            "剪映草稿目录未找到。请在剪映全局设置中查看草稿位置，并通过 --draft-root 指定。"
        )
    root = roots[0]
    project_id = str(manifest.get("project_id") or "project")
    desired_name = draft_name or f"{config.edit_package.jianying_draft_name_prefix}_{project_id}"
    final_name = _unique_draft_name(root, desired_name)
    timeline = manifest.get("timeline", {})
    width = int(timeline.get("width", config.mixing.target_width))
    height = int(timeline.get("height", config.mixing.target_height))

    try:
        folder = draft.DraftFolder(str(root))
        script = folder.create_draft(final_name, width, height)
        video_track = "AI粗剪视频"
        source_audio_track = "原声"
        narration_track = "配音"
        _add_track(script, draft, draft.TrackType.video, video_track, relative_index=1)
        _add_track(script, draft, draft.TrackType.audio, source_audio_track, relative_index=1)
        _add_track(script, draft, draft.TrackType.audio, narration_track, relative_index=2)

        source_volume = _source_volume(manifest, config)
        for row in manifest.get("segments", []):
            if not isinstance(row, dict):
                continue
            proxy = Path(str(row.get("proxy_video_path", "")))
            if not proxy.is_file():
                raise JianyingDraftError(f"代理镜头不存在: {proxy}")
            target_range = draft.trange(
                _seconds(float(row.get("timeline_start", 0.0))),
                _seconds(float(row.get("timeline_duration", 0.0))),
            )
            source_range = draft.trange(
                _seconds(float(row.get("selected_in", 0.0))),
                _seconds(float(row.get("selected_duration", 0.0))),
            )
            video_segment = draft.VideoSegment(
                str(proxy.resolve()),
                target_range,
                source_timerange=source_range,
            )
            _add_segment(script, video_segment, video_track)

            source_audio = Path(str(row.get("source_audio_path", "")))
            if source_audio.is_file():
                audio_segment = draft.AudioSegment(
                    str(source_audio.resolve()),
                    target_range,
                    source_timerange=source_range,
                )
                _set_audio_volume(audio_segment, source_volume)
                _add_segment(script, audio_segment, source_audio_track)

        narration = manifest.get("narration")
        if isinstance(narration, dict):
            narration_path = Path(str(narration.get("output_path", "")))
            if narration_path.is_file():
                narration_segment = draft.AudioSegment(
                    str(narration_path.resolve()),
                    draft.trange(
                        "0s",
                        _seconds(float(timeline.get("duration", 0.0))),
                    ),
                )
                _set_audio_volume(narration_segment, config.audio.narration_volume)
                _add_segment(script, narration_segment, narration_track)

        subtitles = manifest.get("subtitles", {})
        srt_path = Path(str(subtitles.get("srt", ""))) if isinstance(subtitles, dict) else Path()
        subtitle_imported = False
        if srt_path.is_file():
            try:
                script.import_srt(str(srt_path.resolve()), track_name="字幕")
                subtitle_imported = True
            except TypeError:
                script.import_srt(str(srt_path.resolve()), "字幕")
                subtitle_imported = True

        if hasattr(script, "save"):
            script.save()
        else:
            target_dir = root / final_name
            target_dir.mkdir(parents=True, exist_ok=True)
            script.dump(str(target_dir / "draft_content.json"))
    except JianyingDraftError:
        raise
    except Exception as exc:
        raise JianyingDraftError(f"剪映草稿生成失败: {type(exc).__name__}: {exc}") from exc

    return {
        "created": True,
        "draft_name": final_name,
        "draft_root": str(root),
        "draft_path": str((root / final_name).resolve()),
        "video_segment_count": len(manifest.get("segments", [])),
        "source_audio_track": True,
        "narration_track": bool(manifest.get("narration")),
        "subtitle_imported": subtitle_imported,
        "compatibility_warning": (
            "剪映草稿格式属于私有格式。草稿打不开时，请使用同目录标准编辑包手工导入。"
        ),
    }
