from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from short_drama_controller.v02_exporters import export_project
from short_drama_controller.v02_full_cli import build_project, load_project, save_project
from short_drama_controller.v02_models import Project
from short_drama_controller.v02_qa_gate import evaluate


def test_pyproject_entrypoint_points_to_full_cli() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.7.0.dev0"' in pyproject
    assert 'short-drama-controller-v02 = "short_drama_controller.v02_full_cli:main"' in pyproject
    assert 'script-driven-mixer = "short_drama_controller.script_mixer.cli:main"' in pyproject
    assert "short_drama_controller.v02_cli:main" not in pyproject


def test_full_flow_exports_only_video_prompts_md(tmp_path: Path) -> None:
    text = "夜里，少年在破庙门口握着木剑。老人递出一盏灯笼，说：“你终于来了。”少年转身，门外黑影停住。"
    project_dir = tmp_path / "project"
    project = build_project(text, "pytest_v02")
    save_project(project, project_dir)

    loaded = load_project(project_dir)
    qa = evaluate(loaded)
    assert qa["qa_status 质检状态"] != "BLOCKER"

    export_project(loaded, project_dir)
    assert (project_dir / "exports" / "video_prompts.md").exists()
    assert not (project_dir / "exports" / "v02_video_prompts.md").exists()
    assert "allow_export 允许导出：YES" in (project_dir / "qa.md").read_text(encoding="utf-8")

    data = load_project(project_dir).data
    for key in [
        "chapter_intake 章节解析",
        "story_events 事件链",
        "characters 角色列表",
        "scenes 场景列表",
        "props 道具列表",
        "world_bible 世界观",
        "style_bible 风格圣经",
        "asset_lock 资产锁定",
        "coverage_qa 关键实体覆盖QA",
        "beat_map 剧情节拍表",
        "shot_plan 分镜计划",
    ]:
        assert data.get(key), key
    for shot in data["shots 分镜列表"]:
        for key in ["source_quote 原文证据", "event_id 事件编号", "beat_id 节拍编号", "scene_id 场景编号", "character_id 角色编号", "prop_id 道具编号"]:
            assert shot.get(key), f"{shot.get('shot_id 镜头编号')} missing {key}"


def test_export_blocks_when_qa_has_blocker(tmp_path: Path) -> None:
    project_dir = tmp_path / "blocked"
    project_dir.mkdir()
    blocker_project = Project({
        "project_name 项目名": "blocked",
        "skill_version 技能版本": "0.5.0",
        "source_text 原文": "",
        "characters 角色列表": [],
        "scenes 场景列表": [],
        "props 道具列表": [],
        "shots 分镜列表": [],
    })
    with pytest.raises(SystemExit):
        export_project(blocker_project, project_dir)
    assert (project_dir / "qa.md").exists()
    assert "allow_export 允许导出：NO" in (project_dir / "qa.md").read_text(encoding="utf-8")
    assert not (project_dir / "exports" / "video_prompts.md").exists()


def test_smoke_uses_explicit_out_without_deleting_repo_dir(tmp_path: Path) -> None:
    out_dir = tmp_path / "smoke_out"
    result = subprocess.run([sys.executable, "scripts/v02_smoke.py", "--out", str(out_dir)], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    assert (out_dir / "exports" / "video_prompts.md").exists()
