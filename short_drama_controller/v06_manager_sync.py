from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .v06_unified_workflow import TASKS_FILENAME, load_workflow_state

RECEIPT_FILENAME = "manager_import.json"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def normalize_manager_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "http":
        raise ValueError("Comfy Cloud Manager URL must use local http")
    if parsed.username or parsed.password:
        raise ValueError("Comfy Cloud Manager URL must not contain credentials")
    host = (parsed.hostname or "").lower()
    if host not in LOOPBACK_HOSTS:
        raise ValueError("Comfy Cloud Manager sync only allows loopback hosts")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Comfy Cloud Manager URL must contain only scheme, host and optional port")
    port = parsed.port
    if host == "::1":
        authority = f"[{host}]" + (f":{port}" if port else "")
    else:
        authority = host + (f":{port}" if port else "")
    return f"http://{authority}"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON file: {path}") from exc


def _write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _default_sender(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("Comfy Cloud Manager response is too large")
        return body


def sync_production_plan(
    project_dir: Path,
    manager_url: str,
    *,
    manager_project_id: str | None = None,
    timeout_seconds: float = 10.0,
    sender: Callable[[Request, float], bytes] | None = None,
) -> dict[str, Any]:
    if not 0.1 <= timeout_seconds <= 60:
        raise ValueError("manager timeout must be between 0.1 and 60 seconds")
    base_url = normalize_manager_url(manager_url)
    tasks_path = project_dir / TASKS_FILENAME
    if not tasks_path.is_file():
        raise FileNotFoundError(f"production task manifest not found: {tasks_path}")
    manifest = _read_json(tasks_path)
    if not isinstance(manifest, dict) or manifest.get("workflow_id 工作流编号") != "novel-to-drama.v1":
        raise ValueError("production task manifest is not novel-to-drama.v1")
    state = load_workflow_state(project_dir)
    payload: dict[str, Any] = {
        "name": str(state.get("project_name 项目名") or project_dir.name)[:100],
        "manifest": manifest,
    }
    if manager_project_id:
        payload["project_id"] = manager_project_id
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = Request(
        f"{base_url}/api/v1/production-plans/import",
        data=encoded,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    transmit = sender or _default_sender
    try:
        raw = transmit(request, timeout_seconds)
    except HTTPError as exc:
        detail = ""
        try:
            error_body = exc.read(8192)
            parsed = json.loads(error_body.decode("utf-8"))
            if isinstance(parsed, dict):
                detail = str(parsed.get("detail", ""))[:500]
        except Exception:
            detail = ""
        raise RuntimeError(f"Comfy Cloud Manager rejected plan: HTTP {exc.code}" + (f" {detail}" if detail else "")) from exc
    except (URLError, TimeoutError, socket.timeout) as exc:
        raise ConnectionError(f"cannot reach local Comfy Cloud Manager at {base_url}") from exc

    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Comfy Cloud Manager returned invalid JSON") from exc
    if not isinstance(result, dict) or not str(result.get("id", "")).startswith("pln_"):
        raise RuntimeError("Comfy Cloud Manager response does not contain a valid production plan id")
    analysis = result.get("analysis")
    safety = analysis.get("safety") if isinstance(analysis, dict) else None
    if not isinstance(safety, dict) or safety.get("dry_run_only") is not True:
        raise RuntimeError("Comfy Cloud Manager did not prove dry-run-only import")
    forbidden_true = [
        key for key, value in safety.items()
        if key != "dry_run_only" and value is True
    ]
    if forbidden_true:
        raise RuntimeError("Comfy Cloud Manager import safety proof is invalid")

    receipt = {
        "manager_plan_id 经理计划编号": result["id"],
        "manager_url 管理器地址": base_url,
        "manager_project_id 管理器项目编号": manager_project_id,
        "source_sha256 来源哈希": result.get("source_sha256"),
        "status 状态": result.get("status"),
        "summary 摘要": result.get("summary"),
        "imported_at 导入时间": result.get("imported_at"),
        "execution 执行状态": result.get("execution"),
        "safety 安全证明": safety,
    }
    _write_json(project_dir / RECEIPT_FILENAME, receipt)
    return receipt
