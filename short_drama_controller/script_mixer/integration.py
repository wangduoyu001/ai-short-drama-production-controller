from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from .audio import probe_audio

if TYPE_CHECKING:
    from .pipeline import ScriptMixerPipeline


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(slots=True)
class IntegrationCheckResult:
    check_id: str
    status: str
    message: str
    duration_ms: float
    blocker: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    remediation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class IntegrationReport:
    generated_at: str
    platform: str
    python_version: str
    inputs: dict[str, Any]
    checks: list[IntegrationCheckResult] = field(default_factory=list)
    performance: dict[str, Any] = field(default_factory=dict)
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    environment_ready: bool = False
    ready_for_real_trial: bool = False
    trial_completed: bool = False
    resume_supported: bool = True
    resume_strategy: str = (
        "cheap checks rerun; media scan is incremental; completed project artifacts are reused"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "platform": self.platform,
            "python_version": self.python_version,
            "inputs": self.inputs,
            "checks": [item.to_dict() for item in self.checks],
            "performance": self.performance,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "environment_ready": self.environment_ready,
            "ready_for_real_trial": self.ready_for_real_trial,
            "trial_completed": self.trial_completed,
            "resume_supported": self.resume_supported,
            "resume_strategy": self.resume_strategy,
        }


_FONT_EXTENSIONS = {".ttf", ".ttc", ".otf", ".otc"}
_CJK_FONT_MARKERS = (
    "msyh",
    "yahei",
    "simhei",
    "simsun",
    "notosanscjk",
    "sourcehansans",
    "sourcehanserif",
    "pingfang",
    "heiti",
    "songti",
    "wenquanyi",
    "droidsansfallback",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _normalize_font_name(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.casefold())


def _font_roots() -> list[Path]:
    home = Path.home()
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        home / ".fonts",
        home / ".local" / "share" / "fonts",
        Path("/Library/Fonts"),
        Path("/System/Library/Fonts"),
        home / "Library" / "Fonts",
    ]
    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if key not in seen and resolved.is_dir():
            seen.add(key)
            result.append(resolved)
    return result


def _discover_fonts(configured_name: str, maximum_files: int = 12000) -> dict[str, Any]:
    configured = _normalize_font_name(configured_name)
    configured_markers = {configured}
    if "microsoftyahei" in configured or "微软雅黑" in configured:
        configured_markers.update({"msyh", "yahei", "microsoftyahei"})
    matched: list[str] = []
    cjk: list[str] = []
    scanned = 0
    roots = _font_roots()
    for root in roots:
        try:
            iterator = root.rglob("*")
            for path in iterator:
                if scanned >= maximum_files:
                    break
                try:
                    if not path.is_file() or path.suffix.casefold() not in _FONT_EXTENSIONS:
                        continue
                except OSError:
                    continue
                scanned += 1
                normalized = _normalize_font_name(path.stem)
                if any(marker and marker in normalized for marker in configured_markers):
                    matched.append(str(path))
                if any(marker in normalized for marker in _CJK_FONT_MARKERS):
                    cjk.append(str(path))
            if scanned >= maximum_files:
                break
        except (OSError, PermissionError):
            continue
    return {
        "configured_font": configured_name,
        "configured_matches": matched[:20],
        "cjk_font_matches": cjk[:20],
        "font_roots": [str(item) for item in roots],
        "files_scanned": scanned,
    }


def _escape_filter_path(path: Path) -> str:
    normalized = str(path.expanduser().resolve()).replace("\\", "/")
    normalized = normalized.replace("'", r"\'")
    for character in (":", "[", "]", ",", ";"):
        normalized = normalized.replace(character, f"\\{character}")
    return normalized


def _is_under(path: Path, root: Path) -> bool:
    try:
        return path.resolve().is_relative_to(root.resolve())
    except (OSError, ValueError):
        return False


class IntegrationChecker:
    def __init__(
        self,
        pipeline: ScriptMixerPipeline,
        runner: Runner | None = None,
    ):
        self.pipeline = pipeline
        self.config = pipeline.config
        self.runner = runner or subprocess.run
        self.report_path = Path(self.config.integration.report_path)
        self.work_root = Path(self.config.integration.work_root)
        self.discovery = None
        self.report: IntegrationReport | None = None

    def run(
        self,
        media_root: str | Path | None = None,
        script_path: str | Path | None = None,
        voice_path: str | Path | None = None,
        full_media_scan: bool = False,
        force_media_scan: bool = False,
        run_trial: bool = False,
        trial_duration: float | None = None,
        transcribe_trial: bool = True,
        report_path: str | Path | None = None,
    ) -> IntegrationReport:
        if report_path:
            self.report_path = Path(report_path)
        resolved_media = str(Path(media_root).expanduser().resolve()) if media_root else ""
        resolved_script = str(Path(script_path).expanduser().resolve()) if script_path else ""
        resolved_voice = str(Path(voice_path).expanduser().resolve()) if voice_path else ""
        self.report = IntegrationReport(
            generated_at=_utc_now(),
            platform=f"{platform.system()} {platform.release()}",
            python_version=platform.python_version(),
            inputs={
                "media_root": resolved_media,
                "script_path": resolved_script,
                "voice_path": resolved_voice,
                "full_media_scan": full_media_scan,
                "force_media_scan": force_media_scan,
                "run_trial": run_trial,
                "trial_duration": trial_duration or self.config.integration.trial_duration_seconds,
                "transcribe_trial": transcribe_trial,
                "maximum_source_process_seconds": (
                    self.config.media_scan.maximum_source_process_seconds
                ),
            },
        )
        self._save()

        self._execute("python", self._check_python, default_blocker=True)
        self._execute("storage_database", self._check_storage_and_database, default_blocker=True)
        self._execute("tool_discovery", self._check_tool_discovery, default_blocker=True)
        self._execute("ffmpeg_capabilities", self._check_ffmpeg_capabilities, default_blocker=True)
        self._execute("subtitle_fonts", self._check_subtitle_fonts, default_blocker=True)
        self._execute("gpu", self._check_gpu, default_blocker=False)
        self._execute("local_models", self._check_local_models, default_blocker=False)
        if self.config.integration.synthetic_render_enabled:
            self._execute("synthetic_render", self._check_synthetic_render, default_blocker=True)
        else:
            self._append(
                IntegrationCheckResult(
                    check_id="synthetic_render",
                    status="skip",
                    message="synthetic render is disabled by local configuration",
                    duration_ms=0.0,
                )
            )
        self._execute(
            "media_library",
            lambda: self._check_media_library(
                resolved_media,
                full_scan=full_media_scan,
                force=force_media_scan,
            ),
            default_blocker=bool(resolved_media),
        )
        self._execute(
            "script_input",
            lambda: self._check_script(resolved_script),
            default_blocker=bool(resolved_script),
        )
        self._execute(
            "voice_input",
            lambda: self._check_voice(resolved_voice),
            default_blocker=bool(resolved_voice),
        )
        if run_trial:
            self._execute(
                "real_trial",
                lambda: self._run_real_trial(
                    media_root=resolved_media,
                    script_path=resolved_script,
                    voice_path=resolved_voice,
                    duration=trial_duration or self.config.integration.trial_duration_seconds,
                    transcribe=transcribe_trial,
                ),
                default_blocker=True,
            )
        else:
            self._append(
                IntegrationCheckResult(
                    check_id="real_trial",
                    status="skip",
                    message="real trial was not requested; pass --run-trial after providing media and script",
                    duration_ms=0.0,
                    remediation=[
                        "Provide --media-root and --script, then add --run-trial for a real preview export"
                    ],
                )
            )
        self._refresh_summary()
        self._save()
        return self.report

    def _execute(
        self,
        check_id: str,
        function: Callable[[], IntegrationCheckResult],
        default_blocker: bool,
    ) -> None:
        started = time.perf_counter()
        try:
            result = function()
        except Exception as exc:  # Integration reports should preserve the next action.
            result = IntegrationCheckResult(
                check_id=check_id,
                status="fail",
                message=f"{type(exc).__name__}: {exc}",
                duration_ms=0.0,
                blocker=default_blocker,
                details={"exception_type": type(exc).__name__},
                remediation=["Inspect this check, correct the local dependency or path, then rerun integration-check"],
            )
        result.duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
        self._append(result)

    def _append(self, result: IntegrationCheckResult) -> None:
        assert self.report is not None
        self.report.checks.append(result)
        self.report.performance[f"{result.check_id}_duration_ms"] = result.duration_ms
        self._refresh_summary()
        self._save()

    def _refresh_summary(self) -> None:
        assert self.report is not None
        blockers = [item.message for item in self.report.checks if item.blocker and item.status == "fail"]
        warnings = [
            item.message
            for item in self.report.checks
            if item.status == "warn" or (item.status == "fail" and not item.blocker)
        ]
        environment_ids = {
            "python",
            "storage_database",
            "tool_discovery",
            "ffmpeg_capabilities",
            "subtitle_fonts",
            "gpu",
            "local_models",
            "synthetic_render",
        }
        environment_blockers = [
            item
            for item in self.report.checks
            if item.check_id in environment_ids and item.blocker and item.status == "fail"
        ]
        media_ok = any(
            item.check_id == "media_library" and item.status in {"pass", "warn"}
            for item in self.report.checks
        )
        script_ok = any(
            item.check_id == "script_input" and item.status == "pass"
            for item in self.report.checks
        )
        self.report.blockers = list(dict.fromkeys(blockers))
        self.report.warnings = list(dict.fromkeys(warnings))
        self.report.environment_ready = not environment_blockers
        self.report.ready_for_real_trial = self.report.environment_ready and media_ok and script_ok
        self.report.trial_completed = any(
            item.check_id == "real_trial" and item.status == "pass"
            for item in self.report.checks
        )

    def _save(self) -> None:
        if self.report is not None:
            _atomic_write_json(self.report_path, self.report.to_dict())

    def _completed(
        self,
        check_id: str,
        status: str,
        message: str,
        blocker: bool = False,
        details: dict[str, Any] | None = None,
        remediation: list[str] | None = None,
    ) -> IntegrationCheckResult:
        return IntegrationCheckResult(
            check_id=check_id,
            status=status,
            message=message,
            duration_ms=0.0,
            blocker=blocker,
            details=details or {},
            remediation=remediation or [],
        )

    def _run_command(
        self,
        command: list[str],
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.runner(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout or self.config.integration.command_timeout_seconds,
        )

    def _check_python(self) -> IntegrationCheckResult:
        supported = sys.version_info >= (3, 10)
        return self._completed(
            "python",
            "pass" if supported else "fail",
            f"Python {platform.python_version()} {'is supported' if supported else 'is below 3.10'}",
            blocker=not supported,
            details={"executable": sys.executable, "version_info": list(sys.version_info[:3])},
            remediation=[] if supported else ["Install Python 3.10 or newer and recreate the environment"],
        )

    def _check_storage_and_database(self) -> IntegrationCheckResult:
        paths = [
            Path(self.config.database_path).parent,
            Path(self.config.output_root),
            self.work_root,
            self.report_path.parent,
        ]
        writable: dict[str, bool] = {}
        free_space: dict[str, int] = {}
        failures: list[str] = []
        for path in paths:
            path.mkdir(parents=True, exist_ok=True)
            marker = path / ".script_mixer_write_test"
            try:
                marker.write_text("ok", encoding="utf-8")
                marker.unlink(missing_ok=True)
                writable[str(path.resolve())] = True
            except OSError as exc:
                writable[str(path.resolve())] = False
                failures.append(f"{path}: {exc}")
            try:
                free_space[str(path.resolve())] = shutil.disk_usage(path).free
            except OSError:
                free_space[str(path.resolve())] = 0
        self.pipeline.catalog.initialize()
        insufficient = [
            path
            for path, free in free_space.items()
            if free and free < self.config.integration.minimum_free_space_bytes
        ]
        if failures:
            return self._completed(
                "storage_database",
                "fail",
                "one or more runtime directories are not writable",
                blocker=True,
                details={"writable": writable, "free_space_bytes": free_space, "errors": failures},
                remediation=["Grant write permission or move runtime/output paths to a writable local directory"],
            )
        if insufficient:
            return self._completed(
                "storage_database",
                "fail",
                "free disk space is below the configured integration threshold",
                blocker=True,
                details={"writable": writable, "free_space_bytes": free_space, "low_space_paths": insufficient},
                remediation=["Free disk space before scanning or rendering media"],
            )
        return self._completed(
            "storage_database",
            "pass",
            "runtime directories are writable and the SQLite schema initialized",
            details={"writable": writable, "free_space_bytes": free_space},
        )

    def _check_tool_discovery(self) -> IntegrationCheckResult:
        self.discovery = self.pipeline.doctor()
        tools = {
            name: {
                "available": item.available,
                "executable": item.executable,
                "source": item.source,
                "version": item.version,
            }
            for name, item in self.discovery.tools.items()
        }
        missing_required = [name for name in ("ffmpeg", "ffprobe") if not tools.get(name, {}).get("available")]
        missing_optional = [name for name in ("ollama", "whisper", "nvidia_smi") if not tools.get(name, {}).get("available")]
        if missing_required:
            return self._completed(
                "tool_discovery",
                "fail",
                f"required local tools are missing: {', '.join(missing_required)}",
                blocker=True,
                details={"tools": tools, "missing_optional": missing_optional},
                remediation=["Install FFmpeg with FFprobe or set discovery.tool_overrides in the local config"],
            )
        status = "warn" if missing_optional else "pass"
        message = (
            f"required tools found; optional tools missing: {', '.join(missing_optional)}"
            if missing_optional
            else "required and optional local tools were discovered"
        )
        return self._completed(
            "tool_discovery",
            status,
            message,
            details={"tools": tools, "missing_optional": missing_optional},
            remediation=(
                ["Install or configure optional local tools to enable GPU, visual-model, and Whisper checks"]
                if missing_optional
                else []
            ),
        )

    def _tool(self, name: str) -> str | None:
        if self.discovery is None:
            self.discovery = self.pipeline.doctor()
        item = self.discovery.tools.get(name)
        return item.executable if item and item.available else None

    def _check_ffmpeg_capabilities(self) -> IntegrationCheckResult:
        ffmpeg = self._tool("ffmpeg")
        if not ffmpeg:
            return self._completed(
                "ffmpeg_capabilities",
                "fail",
                "FFmpeg is unavailable",
                blocker=True,
                remediation=["Install FFmpeg or configure its executable path"],
            )
        filters = self._run_command([ffmpeg, "-hide_banner", "-filters"])
        encoders = self._run_command([ffmpeg, "-hide_banner", "-encoders"])
        filter_text = f"{filters.stdout}\n{filters.stderr}".casefold()
        encoder_text = f"{encoders.stdout}\n{encoders.stderr}".casefold()
        capabilities = {
            "subtitles_libass": " subtitles " in filter_text or "subtitles" in filter_text,
            "scale": " scale " in filter_text or "scale" in filter_text,
            "crop": " crop " in filter_text or "crop" in filter_text,
            "concat": " concat " in filter_text or "concat" in filter_text,
            "loudnorm": "loudnorm" in filter_text,
            "sidechaincompress": "sidechaincompress" in filter_text,
            "libx264": "libx264" in encoder_text,
            "aac": bool(re.search(r"\baac\b", encoder_text)),
        }
        required = ("subtitles_libass", "scale", "crop", "concat", "libx264", "aac")
        missing = [name for name in required if not capabilities[name]]
        if filters.returncode != 0 or encoders.returncode != 0 or missing:
            return self._completed(
                "ffmpeg_capabilities",
                "fail",
                f"FFmpeg lacks required rendering capabilities: {', '.join(missing) or 'command failure'}",
                blocker=True,
                details={
                    "capabilities": capabilities,
                    "filters_returncode": filters.returncode,
                    "encoders_returncode": encoders.returncode,
                },
                remediation=["Install a full FFmpeg build with libass, libx264, AAC, scale, crop, and concat support"],
            )
        optional_missing = [name for name in ("loudnorm", "sidechaincompress") if not capabilities[name]]
        return self._completed(
            "ffmpeg_capabilities",
            "warn" if optional_missing else "pass",
            (
                f"core rendering capabilities found; optional audio filters missing: {', '.join(optional_missing)}"
                if optional_missing
                else "FFmpeg supports video encoding, AAC, subtitles, scaling, cropping, concatenation, and audio mastering filters"
            ),
            details={"capabilities": capabilities},
            remediation=(
                ["Use a fuller FFmpeg build to enable loudness normalization and automatic source-audio ducking"]
                if optional_missing
                else []
            ),
        )

    def _check_subtitle_fonts(self) -> IntegrationCheckResult:
        details = _discover_fonts(self.config.subtitles.font_name)
        if details["configured_matches"]:
            return self._completed(
                "subtitle_fonts",
                "pass",
                f"configured subtitle font was found: {self.config.subtitles.font_name}",
                details=details,
            )
        if details["cjk_font_matches"]:
            return self._completed(
                "subtitle_fonts",
                "warn",
                f"configured font was not found, but another CJK font is available for fallback",
                details=details,
                remediation=["Install the configured font or change subtitles.font_name to an available CJK font"],
            )
        return self._completed(
            "subtitle_fonts",
            "fail",
            "no usable Chinese/CJK subtitle font was found",
            blocker=True,
            details=details,
            remediation=["Install Microsoft YaHei, Noto Sans CJK, Source Han Sans, or another CJK font"],
        )

    def _query_gpu(self) -> tuple[list[dict[str, Any]], str]:
        executable = self._tool("nvidia_smi")
        if not executable:
            return [], "nvidia-smi was not discovered"
        command = [
            executable,
            "--query-gpu=name,driver_version,memory.total,memory.used,memory.free",
            "--format=csv,noheader,nounits",
        ]
        completed = self._run_command(command, timeout=15.0)
        if completed.returncode != 0:
            return [], (completed.stderr or completed.stdout or "nvidia-smi failed").strip()
        rows: list[dict[str, Any]] = []
        for line in completed.stdout.splitlines():
            parts = [item.strip() for item in line.split(",")]
            if len(parts) < 5:
                continue
            rows.append(
                {
                    "name": parts[0],
                    "driver_version": parts[1],
                    "memory_total_mib": _safe_number(parts[2]),
                    "memory_used_mib": _safe_number(parts[3]),
                    "memory_free_mib": _safe_number(parts[4]),
                }
            )
        return rows, ""

    def _check_gpu(self) -> IntegrationCheckResult:
        rows, error = self._query_gpu()
        if not rows:
            return self._completed(
                "gpu",
                "warn",
                error or "no NVIDIA GPU was reported",
                details={"gpus": rows},
                remediation=["GPU acceleration is optional; install the NVIDIA driver if this computer has a supported GPU"],
            )
        return self._completed(
            "gpu",
            "pass",
            f"detected {len(rows)} NVIDIA GPU(s)",
            details={"gpus": rows},
        )

    def _check_local_models(self) -> IntegrationCheckResult:
        status = self.pipeline.model_status()
        selected = status.get("selected", {})
        missing = [
            key
            for key in ("text_model", "vision_model", "embedding_model")
            if not selected.get(key)
        ]
        whisper = status.get("whisper", {})
        if not whisper.get("available") or not selected.get("speech_model"):
            missing.append("speech_model")
        if missing:
            return self._completed(
                "local_models",
                "warn",
                f"local model capabilities are incomplete: {', '.join(missing)}",
                details=status,
                remediation=["Start Ollama and install or configure the missing local models; planning fallbacks remain available"],
            )
        return self._completed(
            "local_models",
            "pass",
            "text, vision, embedding, and speech model paths are available",
            details=status,
        )

    def _check_synthetic_render(self) -> IntegrationCheckResult:
        ffmpeg = self._tool("ffmpeg")
        ffprobe = self._tool("ffprobe")
        if not ffmpeg or not ffprobe:
            return self._completed(
                "synthetic_render",
                "fail",
                "FFmpeg and FFprobe are required for the synthetic render test",
                blocker=True,
            )
        work = self.work_root / "synthetic_render"
        work.mkdir(parents=True, exist_ok=True)
        subtitle = work / "integration.ass"
        output = work / "integration.mp4"
        output.unlink(missing_ok=True)
        seconds = max(0.5, float(self.config.integration.synthetic_render_seconds))
        subtitle.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 640",
                    "PlayResY: 360",
                    "",
                    "[V4+ Styles]",
                    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
                    f"Style: Default,{self.config.subtitles.font_name},32,&H00FFFFFF,&H0000FFFF,&H00101010,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,30,30,40,1",
                    "",
                    "[Events]",
                    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
                    f"Dialogue: 0,0:00:00.00,0:00:{seconds:05.2f},Default,,0,0,0,,集成测试",
                ]
            ),
            encoding="utf-8-sig",
        )
        escaped = _escape_filter_path(subtitle)
        command = [
            ffmpeg,
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=640x360:r=30:d={seconds:.3f}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=440:sample_rate=48000:duration={seconds:.3f}",
            "-vf",
            f"subtitles=filename='{escaped}'",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output),
        ]
        completed = self._run_command(command)
        if completed.returncode != 0 or not output.is_file() or output.stat().st_size <= 0:
            return self._completed(
                "synthetic_render",
                "fail",
                "synthetic H.264/AAC render with Chinese ASS subtitles failed",
                blocker=True,
                details={
                    "command": command,
                    "returncode": completed.returncode,
                    "stderr_tail": (completed.stderr or "")[-2000:],
                    "output": str(output),
                },
                remediation=["Verify the FFmpeg build, libass support, font installation, and output-directory permissions"],
            )
        probe = self._run_command(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,codec_name,width,height",
                "-of",
                "json",
                str(output),
            ]
        )
        try:
            payload = json.loads(probe.stdout or "{}")
        except json.JSONDecodeError:
            payload = {}
        streams = payload.get("streams") if isinstance(payload, dict) else []
        stream_types = {item.get("codec_type") for item in streams or [] if isinstance(item, dict)}
        valid = probe.returncode == 0 and {"video", "audio"}.issubset(stream_types)
        return self._completed(
            "synthetic_render",
            "pass" if valid else "fail",
            (
                "synthetic H.264/AAC video with Chinese ASS subtitles rendered and probed successfully"
                if valid
                else "synthetic render exists but FFprobe did not confirm both video and audio streams"
            ),
            blocker=not valid,
            details={
                "output": str(output.resolve()),
                "output_size_bytes": output.stat().st_size,
                "probe": payload,
                "command": command,
            },
            remediation=[] if valid else ["Inspect FFprobe output and the local FFmpeg codecs"],
        )

    def _check_media_library(
        self,
        media_root: str,
        full_scan: bool,
        force: bool,
    ) -> IntegrationCheckResult:
        if not media_root:
            return self._completed(
                "media_library",
                "skip",
                "no media root was provided",
                remediation=["Pass --media-root to validate real local media and the 40-second processing window"],
            )
        root = Path(media_root)
        if not root.is_dir():
            return self._completed(
                "media_library",
                "fail",
                f"media root does not exist or is not a directory: {root}",
                blocker=True,
            )
        started = time.perf_counter()
        summary = self.pipeline.scan_media(
            root=root,
            fast=not full_scan,
            force=force,
            prune_missing=False,
        )
        scan_seconds = time.perf_counter() - started
        assert self.report is not None
        self.report.performance["media_scan_seconds"] = round(scan_seconds, 3)
        sources = [item for item in self.pipeline.catalog.list_sources() if _is_under(Path(item.source_path), root)]
        source_ids = {item.source_id for item in sources}
        clips = [item for item in self.pipeline.catalog.list_clips(usable_only=False) if item.source_id in source_ids]
        cap = self.config.media_scan.maximum_source_process_seconds
        violations = [
            {
                "clip_id": clip.clip_id,
                "source_end": clip.source_end,
                "source_path": clip.source_path,
            }
            for clip in clips
            if cap > 0 and clip.source_end > cap + 0.001
        ]
        categories = {
            "horizontal": sum(item.display_dimensions[0] >= item.display_dimensions[1] for item in sources),
            "vertical": sum(item.display_dimensions[1] > item.display_dimensions[0] for item in sources),
            "with_audio": sum(item.has_audio for item in sources),
            "without_audio": sum(not item.has_audio for item in sources),
            "short_10s_or_less": sum(0 < item.duration <= 10.0 for item in sources),
            "longer_than_processing_window": sum(cap > 0 and item.duration > cap for item in sources),
        }
        details = {
            "scan_summary": summary.to_dict(),
            "source_count": len(sources),
            "clip_count": len(clips),
            "categories": categories,
            "processing_window_seconds": cap,
            "violations": violations[:50],
            "incremental_resume": {
                "unchanged_files": summary.unchanged_files,
                "changed_files": summary.changed_files,
                "new_files": summary.new_files,
            },
        }
        if not sources or not clips:
            return self._completed(
                "media_library",
                "fail",
                "the media scan produced no usable sources or clips",
                blocker=True,
                details=details,
                remediation=["Check the media directory, supported extensions, FFprobe availability, and file permissions"],
            )
        if violations:
            return self._completed(
                "media_library",
                "fail",
                "one or more indexed clips exceed the configured source-processing window",
                blocker=True,
                details=details,
                remediation=["Rerun scan-media --force and inspect the database migration if violations remain"],
            )
        missing_categories = [name for name, count in categories.items() if count == 0]
        if summary.failed_files or missing_categories:
            return self._completed(
                "media_library",
                "warn",
                (
                    f"media library passed the 40-second boundary but the real-trial fixture is incomplete: "
                    f"{', '.join(missing_categories) or f'{summary.failed_files} failed files'}"
                ),
                details=details,
                remediation=["Add the missing fixture categories before the final Windows acceptance run"],
            )
        return self._completed(
            "media_library",
            "pass",
            f"indexed {len(sources)} sources and {len(clips)} clips; all clips obey the processing window",
            details=details,
        )

    def _check_script(self, script_path: str) -> IntegrationCheckResult:
        if not script_path:
            return self._completed(
                "script_input",
                "skip",
                "no trial script was provided",
                remediation=["Pass --script with a UTF-8 narration file before running the real trial"],
            )
        path = Path(script_path)
        if not path.is_file():
            return self._completed(
                "script_input",
                "fail",
                f"trial script does not exist: {path}",
                blocker=True,
            )
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return self._completed(
                "script_input",
                "fail",
                "trial script is empty",
                blocker=True,
            )
        return self._completed(
            "script_input",
            "pass",
            f"trial script is readable and contains {len(text)} characters",
            details={"path": str(path.resolve()), "characters": len(text)},
        )

    def _check_voice(self, voice_path: str) -> IntegrationCheckResult:
        if not voice_path:
            return self._completed(
                "voice_input",
                "skip",
                "no real narration file was provided; source-audio trial remains available",
            )
        ffprobe = self._tool("ffprobe")
        info = probe_audio(voice_path, ffprobe)
        if info.duration <= 0:
            return self._completed(
                "voice_input",
                "fail",
                "narration duration is zero or unavailable",
                blocker=True,
            )
        return self._completed(
            "voice_input",
            "pass",
            f"real narration is readable: {info.duration:.3f}s",
            details=asdict(info),
        )

    def _run_real_trial(
        self,
        media_root: str,
        script_path: str,
        voice_path: str,
        duration: float,
        transcribe: bool,
    ) -> IntegrationCheckResult:
        if not media_root or not script_path:
            return self._completed(
                "real_trial",
                "fail",
                "real trial requires both --media-root and --script",
                blocker=True,
                remediation=["Provide local media and a narration script, then rerun with --run-trial"],
            )
        script = Path(script_path).read_text(encoding="utf-8").strip()
        project_id = datetime.now().strftime("integration_%Y%m%d_%H%M%S")
        previous_missing_setting = self.config.mixing.allow_missing_media_files_during_planning
        self.config.mixing.allow_missing_media_files_during_planning = False
        gpu_before, _ = self._query_gpu()
        try:
            plan_started = time.perf_counter()
            timeline, project_dir = self.pipeline.plan(
                script_text=script,
                project_id=project_id,
                target_duration=None if voice_path else max(3.0, duration),
                narration_path=voice_path or None,
                audio_mode="mixed" if voice_path else "source",
                transcribe_narration=transcribe if voice_path else None,
            )
            plan_seconds = time.perf_counter() - plan_started
            cap = self.config.media_scan.maximum_source_process_seconds
            violations = [
                segment.segment_id
                for segment in timeline.segments
                if cap > 0 and segment.source_end > cap + 0.001
            ]
            if violations:
                return self._completed(
                    "real_trial",
                    "fail",
                    "planned timeline references media after the configured source-processing window",
                    blocker=True,
                    details={"violating_segments": violations, "project_dir": str(project_dir)},
                )
            render_started = time.perf_counter()
            output = self.pipeline.render(
                timeline,
                project_dir,
                burn_subtitles=True,
                dry_run=False,
            )
            render_seconds = time.perf_counter() - render_started
        finally:
            self.config.mixing.allow_missing_media_files_during_planning = previous_missing_setting
        gpu_after, _ = self._query_gpu()
        assert self.report is not None
        self.report.performance.update(
            {
                "trial_plan_seconds": round(plan_seconds, 3),
                "trial_render_seconds": round(render_seconds, 3),
                "trial_render_realtime_factor": round(render_seconds / max(0.001, timeline.duration), 4),
                "gpu_before": gpu_before,
                "gpu_after": gpu_after,
            }
        )
        output_path = Path(output)
        if not output_path.is_file() or output_path.stat().st_size <= 0:
            return self._completed(
                "real_trial",
                "fail",
                "the real trial render did not produce a usable MP4",
                blocker=True,
                details={"project_dir": str(project_dir), "output": str(output_path)},
            )
        return self._completed(
            "real_trial",
            "pass",
            f"real trial rendered {timeline.duration:.3f}s from {len(timeline.segments)} segments",
            details={
                "project_id": project_id,
                "project_dir": str(Path(project_dir).resolve()),
                "output": str(output_path.resolve()),
                "output_size_bytes": output_path.stat().st_size,
                "timeline_duration": timeline.duration,
                "segment_count": len(timeline.segments),
                "unique_source_count": len({segment.source_id for segment in timeline.segments}),
                "timing_source": timeline.audio.timing_source,
                "alignment_coverage": timeline.audio.alignment_coverage,
                "subtitle_path": (
                    timeline.audio.subtitle_karaoke_ass_path
                    or timeline.audio.subtitle_ass_path
                    or timeline.audio.subtitle_srt_path
                ),
                "source_window_verified": True,
            },
        )


def _safe_number(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
