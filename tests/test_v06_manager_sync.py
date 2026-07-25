from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

import pytest

from short_drama_controller.v06_manager_sync import (
    RECEIPT_FILENAME,
    normalize_manager_url,
    sync_production_plan,
)
from short_drama_controller.v06_unified_workflow import run_unified_workflow


SOURCE = """# 镖局收徒

少年走进镖局，拿起木剑，说：“就凭我还站着。”镖头后退半步。
需要正反打对白，少量动作，一场戏完成。
"""


def build_project(tmp_path: Path) -> Path:
    input_path = tmp_path / "novel.md"
    project_dir = tmp_path / "project"
    input_path.write_text(SOURCE, encoding="utf-8")
    run_unified_workflow(input_path, project_dir, title="镖局收徒")
    return project_dir


def manager_response(*, safe: bool = True) -> bytes:
    return json.dumps({
        "id": "pln_" + "1" * 32,
        "source_sha256": "a" * 64,
        "status": "blocked",
        "summary": {"total": 10, "ready": 0, "blocked": 8, "deferred": 2},
        "imported_at": "2026-07-25T00:00:00+00:00",
        "execution": "not_started",
        "analysis": {
            "safety": {
                "dry_run_only": safe,
                "will_create_batch": False,
                "will_submit_prompt": False,
                "will_start_gpu": False,
                "will_download_models": False,
                "will_call_paid_api": False,
                "will_write_remote_storage": False,
            }
        },
    }, ensure_ascii=False).encode("utf-8")


def test_normalize_manager_url_allows_only_plain_loopback_http():
    assert normalize_manager_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    assert normalize_manager_url("http://localhost:9000") == "http://localhost:9000"
    assert normalize_manager_url("http://[::1]:8000") == "http://[::1]:8000"
    for value in [
        "https://127.0.0.1:8000",
        "http://example.com:8000",
        "http://user:pass@127.0.0.1:8000",
        "http://127.0.0.1:8000/api",
        "http://127.0.0.1:8000?execute=true",
    ]:
        with pytest.raises(ValueError):
            normalize_manager_url(value)


def test_sync_posts_plan_only_to_import_endpoint_and_writes_receipt(tmp_path: Path):
    project_dir = build_project(tmp_path)
    captured: dict[str, object] = {}

    def sender(request: Request, timeout: float) -> bytes:
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return manager_response()

    receipt = sync_production_plan(
        project_dir,
        "http://127.0.0.1:8000",
        manager_project_id="prj_" + "2" * 32,
        timeout_seconds=3.5,
        sender=sender,
    )

    assert captured["url"] == "http://127.0.0.1:8000/api/v1/production-plans/import"
    assert captured["method"] == "POST"
    assert captured["timeout"] == 3.5
    body = captured["body"]
    assert body["name"] == "镖局收徒"
    assert body["project_id"] == "prj_" + "2" * 32
    assert body["manifest"]["workflow_id 工作流编号"] == "novel-to-drama.v1"
    assert "execute" not in body
    assert receipt["manager_plan_id 经理计划编号"].startswith("pln_")
    assert receipt["execution 执行状态"] == "not_started"
    saved = json.loads((project_dir / RECEIPT_FILENAME).read_text(encoding="utf-8"))
    assert saved == receipt


def test_sync_refuses_manager_response_without_dry_run_proof(tmp_path: Path):
    project_dir = build_project(tmp_path)

    def unsafe_sender(_request: Request, _timeout: float) -> bytes:
        return manager_response(safe=False)

    with pytest.raises(RuntimeError, match="dry-run-only"):
        sync_production_plan(
            project_dir,
            "http://127.0.0.1:8000",
            sender=unsafe_sender,
        )
    assert not (project_dir / RECEIPT_FILENAME).exists()


def test_sync_refuses_missing_or_wrong_manifest(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    with pytest.raises(FileNotFoundError):
        sync_production_plan(project_dir, "http://127.0.0.1:8000", sender=lambda _r, _t: manager_response())

    (project_dir / "production_tasks.json").write_text('{"workflow_id 工作流编号":"other"}', encoding="utf-8")
    with pytest.raises(ValueError, match="novel-to-drama.v1"):
        sync_production_plan(project_dir, "http://127.0.0.1:8000", sender=lambda _r, _t: manager_response())
