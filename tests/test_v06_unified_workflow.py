from __future__ import annotations

import hashlib
import json
from pathlib import Path

from short_drama_controller.v02_models import Project
from short_drama_controller.v06_unified_workflow import (
    ASSEMBLY_FILENAME,
    STAGE_ORDER,
    TASKS_FILENAME,
    WORKFLOW_ID,
    build_assembly_plan,
    build_production_tasks,
    load_workflow_state,
    run_unified_workflow,
)


def sample_project() -> Project:
    return Project({
        "characters 角色列表": [
            {
                "character_id 角色编号": "CHAR_A",
                "character_name 角色名": "少年",
                "role_function 角色功能": "主角",
                "face_shape 脸型": "瘦削长脸",
                "hair_style 发型": "黑色束发",
                "clothing_lock 服装锁定": "灰蓝布衣",
                "prop_lock 道具锁定": "木剑",
                "forbidden_changes 禁止变化": "禁止换脸换服装",
            }
        ],
        "scenes 场景列表": [
            {
                "scene_id 场景编号": "SCENE_01",
                "visual_prompt 视觉提示词": "古代镖局院子，傍晚，空间稳定，无人物",
            }
        ],
        "props 道具列表": [
            {
                "prop_id 道具编号": "PROP_01",
                "visual_prompt 视觉提示词": "木剑，道具图，中性背景",
            }
        ],
        "shots 分镜列表": [
            {
                "shot_id 镜头编号": "SH001",
                "character_id 角色编号": "CHAR_A",
                "scene_id 场景编号": "SCENE_01",
                "prop_id 道具编号": "PROP_01",
                "first_frame_prompt 首帧提示词": "少年站在镖局院中",
                "image_prompt 图片提示词": "中景，少年握木剑",
                "video_prompt 视频提示词": "少年缓慢抬起木剑",
                "end_frame_prompt 尾帧提示词": "木剑指向前方",
                "negative_prompt 负面提示词": "禁止换脸，禁止跳轴",
                "clip_duration_seconds 片段时长秒数": 8,
                "dialogue_line 出口对白": "就凭我还站着。",
                "speaker_mode 发声模式": "on_screen 画内对白",
            }
        ],
    })


def test_task_graph_contains_assets_shots_audio_and_assembly():
    manifest = build_production_tasks(sample_project())
    tasks = {task["task_id 任务编号"]: task for task in manifest["tasks 任务"]}

    assert manifest["workflow_id 工作流编号"] == WORKFLOW_ID
    assert len(tasks) == 9
    assert tasks["ASSET-CHAR_A-TURN"]["depends_on 依赖任务"] == ["ASSET-CHAR_A-FULL"]
    assert set(tasks["SHOT-SH001-IMAGE"]["depends_on 依赖任务"]) == {
        "ASSET-CHAR_A-TURN",
        "ASSET-SCENE_01",
        "ASSET-PROP_01",
    }
    assert tasks["SHOT-SH001-VIDEO"]["depends_on 依赖任务"] == ["SHOT-SH001-IMAGE"]
    assert "SHOT-SH001-VIDEO" in tasks["ASSEMBLY-EPISODE-001"]["depends_on 依赖任务"]
    assert "SHOT-SH001-TTS" in tasks["ASSEMBLY-EPISODE-001"]["depends_on 依赖任务"]
    assert tasks["SHOT-SH001-VIDEO"]["max_attempts 最大尝试次数"] == 3
    assert tasks["ASSEMBLY-EPISODE-001"]["max_attempts 最大尝试次数"] == 1


def test_assembly_plan_refuses_fake_first_clip_fallback():
    plan = build_assembly_plan(build_production_tasks(sample_project()))
    assert plan["provider 合成器"] == "ffmpeg"
    assert plan["video_task_order 视频顺序"] == ["SHOT-SH001-VIDEO"]
    assert plan["fallback 失败策略"].startswith("BLOCKER")
    assert plan["command 命令"][:4] == ["ffmpeg", "-f", "concat", "-safe"]


def test_run_all_creates_resumable_single_workflow(tmp_path: Path):
    source = """# 镖局收徒

一个落魄少年来到镖局门口，想拜入镖局学武。镖头让他拿起木剑。
少年握住木剑，说：\"就凭我还站着。\"镖头后退半步，答应让他明日押镖。
需要正反打对白，少量动作，一场戏完成。
"""
    input_path = tmp_path / "novel.md"
    project_dir = tmp_path / "project"
    input_path.write_text(source, encoding="utf-8")

    result = run_unified_workflow(input_path, project_dir, title="镖局收徒")

    assert result.status == "planned"
    assert result.task_count > 0
    assert result.pending_external_tasks == result.task_count
    assert (project_dir / "workflow.json").is_file()
    assert (project_dir / TASKS_FILENAME).is_file()
    assert (project_dir / ASSEMBLY_FILENAME).is_file()
    assert (project_dir / "exports" / "video_prompts.md").is_file()

    state = load_workflow_state(project_dir)
    assert state["source_sha256 原文哈希"] == hashlib.sha256(source.strip().encode("utf-8")).hexdigest()
    assert state["status 状态"] == "planned"
    assert state["render_execution 渲染执行"].startswith("pending_external_tasks")
    assert list(state["stages 阶段"]) == list(STAGE_ORDER)
    assert all(stage["status 状态"] == "completed" for stage in state["stages 阶段"].values())

    attempts_before = {
        stage_id: stage["attempts 尝试次数"]
        for stage_id, stage in state["stages 阶段"].items()
    }
    resumed = run_unified_workflow(input_path, project_dir, title="镖局收徒", resume=True)
    state_after = load_workflow_state(project_dir)
    assert resumed.status == "planned"
    assert attempts_before == {
        stage_id: stage["attempts 尝试次数"]
        for stage_id, stage in state_after["stages 阶段"].items()
    }

    tasks = json.loads((project_dir / TASKS_FILENAME).read_text(encoding="utf-8"))
    assert tasks["selection_policy 版本选择策略"]["keep_variants_per_asset 每项保留版本"] == 10
    assert tasks["retry_policy 重试策略"]["skip_completed 跳过已完成"] is True


def test_resume_refuses_changed_source(tmp_path: Path):
    input_path = tmp_path / "novel.md"
    project_dir = tmp_path / "project"
    input_path.write_text("少年走进镖局，拿起木剑。", encoding="utf-8")
    run_unified_workflow(input_path, project_dir)

    input_path.write_text("原文已被修改。", encoding="utf-8")
    try:
        run_unified_workflow(input_path, project_dir, resume=True)
    except ValueError as exc:
        assert "source text changed" in str(exc)
    else:
        raise AssertionError("resume must reject changed source")
