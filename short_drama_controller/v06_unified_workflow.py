from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .v02_exporters import export_project
from .v02_io import read_project
from .v02_models import Project

WORKFLOW_ID = "novel-to-drama.v1"
STATE_FILENAME = "workflow.json"
TASKS_FILENAME = "production_tasks.json"
ASSEMBLY_FILENAME = "assembly_plan.json"

STAGE_ORDER = (
    "chapter_intake",
    "director_package",
    "asset_render_plan",
    "storyboard_render_plan",
    "video_render_plan",
    "audio_render_plan",
    "assembly_plan",
    "package_qa_export",
)

STAGE_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "chapter_intake": (),
    "director_package": ("chapter_intake",),
    "asset_render_plan": ("director_package",),
    "storyboard_render_plan": ("asset_render_plan",),
    "video_render_plan": ("storyboard_render_plan",),
    "audio_render_plan": ("director_package",),
    "assembly_plan": ("video_render_plan", "audio_render_plan"),
    "package_qa_export": ("assembly_plan",),
}


@dataclass(frozen=True)
class WorkflowResult:
    workflow_id: str
    status: str
    project_dir: Path
    state_path: Path
    task_count: int
    pending_external_tasks: int


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _new_stage(stage_id: str) -> dict[str, Any]:
    return {
        "stage_id 阶段编号": stage_id,
        "depends_on 依赖阶段": list(STAGE_DEPENDENCIES[stage_id]),
        "status 状态": "pending",
        "attempts 尝试次数": 0,
        "started_at 开始时间": None,
        "completed_at 完成时间": None,
        "error 错误": None,
        "artifacts 产物": [],
    }


def new_workflow_state(source_text: str, source_path: Path, title: str) -> dict[str, Any]:
    return {
        "workflow_id 工作流编号": WORKFLOW_ID,
        "workflow_version 工作流版本": 1,
        "project_name 项目名": title,
        "source_path 原文路径": str(source_path),
        "source_sha256 原文哈希": _sha256_text(source_text),
        "execution_mode 执行模式": "owned_orchestrator 自有编排器",
        "render_execution 渲染执行": "planned_not_submitted 已规划未提交",
        "created_at 创建时间": _now(),
        "updated_at 更新时间": _now(),
        "status 状态": "pending",
        "stages 阶段": {stage_id: _new_stage(stage_id) for stage_id in STAGE_ORDER},
        "external_boundaries 外部边界": {
            "text_pipeline 文本流程": "local_controller 本地控制器",
            "image_video_gateway 图像视频网关": "comfy-cloud-manager 自有生成网关",
            "audio_provider 声音提供方": "not_configured 未配置",
            "assembly 合成": "ffmpeg 本地合成",
        },
        "source_provenance 来源借鉴": [
            "alibaba/lumenx@7a1213a0db73ab90ca976f5c4b4ca680e1ae1d2d MIT",
            "xuanyustudio/LocalMiniDrama@b695284b8288e392a4ce2a63717406f3830966af MIT",
        ],
    }


def load_workflow_state(project_dir: Path) -> dict[str, Any]:
    path = project_dir / STATE_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"workflow state not found: {path}")
    payload = _read_json(path)
    if not isinstance(payload, dict) or payload.get("workflow_id 工作流编号") != WORKFLOW_ID:
        raise ValueError("workflow state is invalid")
    return payload


def _load_project(project_dir: Path) -> Project:
    return Project(read_project(project_dir / "project.yaml"))


def _stage_ready(state: dict[str, Any], stage_id: str) -> bool:
    stages = state["stages 阶段"]
    return all(stages[dependency]["status 状态"] == "completed" for dependency in STAGE_DEPENDENCIES[stage_id])


def _run_stage(
    state: dict[str, Any],
    state_path: Path,
    stage_id: str,
    action: Callable[[], list[str]],
    *,
    resume: bool,
) -> None:
    stage = state["stages 阶段"][stage_id]
    if resume and stage["status 状态"] == "completed":
        return
    if not _stage_ready(state, stage_id):
        missing = [
            dependency
            for dependency in STAGE_DEPENDENCIES[stage_id]
            if state["stages 阶段"][dependency]["status 状态"] != "completed"
        ]
        stage["status 状态"] = "blocked"
        stage["error 错误"] = f"dependency not completed: {', '.join(missing)}"
        state["status 状态"] = "blocked"
        state["updated_at 更新时间"] = _now()
        _write_json(state_path, state)
        raise RuntimeError(stage["error 错误"])

    stage["status 状态"] = "running"
    stage["attempts 尝试次数"] += 1
    stage["started_at 开始时间"] = _now()
    stage["error 错误"] = None
    state["status 状态"] = "running"
    state["updated_at 更新时间"] = _now()
    _write_json(state_path, state)

    try:
        artifacts = action()
    except Exception as exc:
        stage["status 状态"] = "failed"
        stage["error 错误"] = f"{type(exc).__name__}: {exc}"
        state["status 状态"] = "failed"
        state["updated_at 更新时间"] = _now()
        _write_json(state_path, state)
        raise

    stage["status 状态"] = "completed"
    stage["completed_at 完成时间"] = _now()
    stage["artifacts 产物"] = artifacts
    state["updated_at 更新时间"] = _now()
    _write_json(state_path, state)


def _task(
    task_id: str,
    kind: str,
    *,
    depends_on: list[str] | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    provider: str,
    max_attempts: int = 3,
) -> dict[str, Any]:
    return {
        "task_id 任务编号": task_id,
        "task_type 任务类型": kind,
        "status 状态": "pending",
        "depends_on 依赖任务": depends_on or [],
        "provider_route 提供方路由": provider,
        "max_attempts 最大尝试次数": max_attempts,
        "attempts 已尝试次数": 0,
        "inputs 输入": inputs or {},
        "outputs 输出": outputs or {},
        "variants 版本候选": [],
        "selected_variant_id 已选版本编号": None,
        "error 错误": None,
    }


def _character_prompt(character: dict[str, Any]) -> str:
    ordered_fields = (
        "character_name 角色名",
        "role_function 角色功能",
        "face_shape 脸型",
        "hair_style 发型",
        "clothing_lock 服装锁定",
        "prop_lock 道具锁定",
        "forbidden_changes 禁止变化",
    )
    parts = [str(character.get(field, "")).strip() for field in ordered_fields]
    return "，".join(part for part in parts if part)


def _character_asset_tasks(project: Project) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for character in project.characters:
        character_id = character.get("character_id 角色编号", "UNKNOWN")
        base_id = f"ASSET-{character_id}-FULL"
        tasks.append(_task(
            base_id,
            "character_full_body 角色全身图",
            provider="comfy-cloud-manager",
            inputs={
                "character_id 角色编号": character_id,
                "prompt 提示词": _character_prompt(character),
                "background 背景": "pure_white 纯白背景",
            },
            outputs={"asset_role 资产用途": "full_body 全身图"},
        ))
        tasks.append(_task(
            f"ASSET-{character_id}-TURN",
            "character_three_view 角色三视图",
            provider="comfy-cloud-manager",
            depends_on=[base_id],
            inputs={"character_id 角色编号": character_id, "reference_task_id 参考任务": base_id},
            outputs={"asset_role 资产用途": "front_side_back 正侧背三视图"},
        ))
        tasks.append(_task(
            f"ASSET-{character_id}-HEAD",
            "character_headshot 角色头像",
            provider="comfy-cloud-manager",
            depends_on=[base_id],
            inputs={"character_id 角色编号": character_id, "reference_task_id 参考任务": base_id},
            outputs={"asset_role 资产用途": "identity_reference 身份参考"},
        ))
    return tasks


def _scene_prop_tasks(project: Project) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for scene in project.scenes:
        scene_id = scene.get("scene_id 场景编号", "UNKNOWN")
        tasks.append(_task(
            f"ASSET-{scene_id}",
            "scene_reference 场景参考图",
            provider="comfy-cloud-manager",
            inputs={
                "scene_id 场景编号": scene_id,
                "prompt 提示词": scene.get("visual_prompt 视觉提示词", ""),
                "characters 人物": "none 无人物",
            },
            outputs={"asset_role 资产用途": "stable_scene_layout 稳定场景布局"},
        ))
    for prop in project.props:
        prop_id = prop.get("prop_id 道具编号", "UNKNOWN")
        tasks.append(_task(
            f"ASSET-{prop_id}",
            "prop_reference 道具参考图",
            provider="comfy-cloud-manager",
            inputs={
                "prop_id 道具编号": prop_id,
                "prompt 提示词": prop.get("visual_prompt 视觉提示词", ""),
            },
            outputs={"asset_role 资产用途": "locked_prop_shape 锁定道具形状"},
        ))
    return tasks


def _shot_dependencies(shot: dict[str, Any]) -> list[str]:
    dependencies: list[str] = []
    character_id = shot.get("character_id 角色编号")
    scene_id = shot.get("scene_id 场景编号")
    prop_id = shot.get("prop_id 道具编号")
    if character_id:
        dependencies.append(f"ASSET-{character_id}-TURN")
    if scene_id:
        dependencies.append(f"ASSET-{scene_id}")
    if prop_id:
        dependencies.append(f"ASSET-{prop_id}")
    return list(dict.fromkeys(dependencies))


def build_production_tasks(project: Project) -> dict[str, Any]:
    tasks = _character_asset_tasks(project) + _scene_prop_tasks(project)
    for shot in project.shots:
        shot_id = shot.get("shot_id 镜头编号", "UNKNOWN")
        image_task_id = f"SHOT-{shot_id}-IMAGE"
        tasks.append(_task(
            image_task_id,
            "storyboard_image 分镜图",
            provider="comfy-cloud-manager",
            depends_on=_shot_dependencies(shot),
            inputs={
                "shot_id 镜头编号": shot_id,
                "first_frame_prompt 首帧提示词": shot.get("first_frame_prompt 首帧提示词", ""),
                "image_prompt 图片提示词": shot.get("image_prompt 图片提示词", ""),
                "negative_prompt 负面提示词": shot.get("negative_prompt 负面提示词", ""),
            },
            outputs={"asset_role 资产用途": "storyboard_master 分镜主图"},
        ))
        tasks.append(_task(
            f"SHOT-{shot_id}-VIDEO",
            "shot_video 分镜视频",
            provider="comfy-cloud-manager",
            depends_on=[image_task_id],
            inputs={
                "shot_id 镜头编号": shot_id,
                "video_prompt 视频提示词": shot.get("video_prompt 视频提示词", ""),
                "end_frame_prompt 尾帧提示词": shot.get("end_frame_prompt 尾帧提示词", ""),
                "duration_seconds 时长秒数": shot.get("clip_duration_seconds 片段时长秒数", 5),
                "negative_prompt 负面提示词": shot.get("negative_prompt 负面提示词", ""),
            },
            outputs={"asset_role 资产用途": "selected_shot_video 已选分镜视频"},
        ))
        dialogue = shot.get("dialogue_line 出口对白") or shot.get("os_line 画外音")
        if dialogue:
            tasks.append(_task(
                f"SHOT-{shot_id}-TTS",
                "tts_dialogue 对白配音",
                provider="tts-provider",
                inputs={
                    "shot_id 镜头编号": shot_id,
                    "text 文本": dialogue,
                    "speaker_mode 发声模式": shot.get("speaker_mode 发声模式", ""),
                },
                outputs={"asset_role 资产用途": "dialogue_audio 对白音轨"},
            ))

    video_tasks = [task["task_id 任务编号"] for task in tasks if task["task_type 任务类型"] == "shot_video 分镜视频"]
    audio_tasks = [task["task_id 任务编号"] for task in tasks if task["task_type 任务类型"] == "tts_dialogue 对白配音"]
    tasks.append(_task(
        "ASSEMBLY-EPISODE-001",
        "episode_assembly 单集合成",
        provider="ffmpeg",
        depends_on=video_tasks + audio_tasks,
        inputs={
            "video_task_ids 视频任务": video_tasks,
            "audio_task_ids 音频任务": audio_tasks,
            "mode 合成模式": "concat_then_mix 先拼接后混音",
        },
        outputs={"final_video 最终视频": "exports/final_episode.mp4"},
        max_attempts=1,
    ))
    return {
        "schema_version 结构版本": 1,
        "workflow_id 工作流编号": WORKFLOW_ID,
        "selection_policy 版本选择策略": {
            "keep_variants_per_asset 每项保留版本": 10,
            "auto_select 自动选择": "latest_until_human_review 人工审片前使用最新版本",
            "final_take_selection 最终选片": "human_required 人工确认",
        },
        "retry_policy 重试策略": {
            "default_max_attempts 默认最大次数": 3,
            "skip_completed 跳过已完成": True,
            "resume_failed 恢复失败任务": True,
        },
        "tasks 任务": tasks,
    }


def build_assembly_plan(task_manifest: dict[str, Any]) -> dict[str, Any]:
    video_tasks = [
        task["task_id 任务编号"]
        for task in task_manifest["tasks 任务"]
        if task["task_type 任务类型"] == "shot_video 分镜视频"
    ]
    if len(video_tasks) > 100:
        raise ValueError("one episode cannot contain more than 100 video clips in the current concat plan")
    return {
        "schema_version 结构版本": 1,
        "provider 合成器": "ffmpeg",
        "video_task_order 视频顺序": video_tasks,
        "concat_file 拼接清单": "runtime/concat_list.txt",
        "output_file 输出文件": "exports/final_episode.mp4",
        "command 命令": [
            "ffmpeg", "-f", "concat", "-safe", "0", "-i", "runtime/concat_list.txt", "-c", "copy", "-y", "exports/final_episode.mp4",
        ],
        "fallback 失败策略": "BLOCKER 禁止拿首段视频冒充完整成片",
    }


def run_unified_workflow(
    input_path: Path,
    project_dir: Path,
    *,
    title: str | None = None,
    resume: bool = False,
) -> WorkflowResult:
    source_text = input_path.read_text(encoding="utf-8").strip()
    if not source_text:
        raise ValueError("source novel/script is empty")
    project_title = title or input_path.stem
    project_dir.mkdir(parents=True, exist_ok=True)
    state_path = project_dir / STATE_FILENAME

    if resume and state_path.is_file():
        state = load_workflow_state(project_dir)
        if state.get("source_sha256 原文哈希") != _sha256_text(source_text):
            raise ValueError("source text changed; resume refused to protect the original evidence chain")
    else:
        state = new_workflow_state(source_text, input_path, project_title)
        _write_json(state_path, state)

    _run_stage(state, state_path, "chapter_intake", lambda: [str(input_path)], resume=resume)
    _run_stage(
        state,
        state_path,
        "director_package",
        lambda: _build_and_save_director_package(source_text, project_title, project_dir),
        resume=resume,
    )

    project = _load_project(project_dir)
    task_manifest = build_production_tasks(project)
    _run_stage(
        state,
        state_path,
        "asset_render_plan",
        lambda: _write_task_manifest(project_dir, task_manifest, "asset"),
        resume=resume,
    )
    _run_stage(
        state,
        state_path,
        "storyboard_render_plan",
        lambda: _write_task_manifest(project_dir, task_manifest, "storyboard"),
        resume=resume,
    )
    _run_stage(
        state,
        state_path,
        "video_render_plan",
        lambda: _write_task_manifest(project_dir, task_manifest, "video"),
        resume=resume,
    )
    _run_stage(
        state,
        state_path,
        "audio_render_plan",
        lambda: _write_task_manifest(project_dir, task_manifest, "audio"),
        resume=resume,
    )

    assembly_plan = build_assembly_plan(task_manifest)
    _run_stage(
        state,
        state_path,
        "assembly_plan",
        lambda: _save_assembly_plan(project_dir, assembly_plan),
        resume=resume,
    )
    _run_stage(
        state,
        state_path,
        "package_qa_export",
        lambda: _run_package_qa_export(project_dir),
        resume=resume,
    )

    _write_json(project_dir / TASKS_FILENAME, task_manifest)
    state["status 状态"] = "planned"
    state["render_execution 渲染执行"] = "pending_external_tasks 等待自有网关执行"
    state["updated_at 更新时间"] = _now()
    _write_json(state_path, state)
    task_count = len(task_manifest["tasks 任务"])
    return WorkflowResult(
        workflow_id=WORKFLOW_ID,
        status="planned",
        project_dir=project_dir,
        state_path=state_path,
        task_count=task_count,
        pending_external_tasks=task_count,
    )


def _build_and_save_director_package(source_text: str, title: str, project_dir: Path) -> list[str]:
    from .v02_full_cli import build_project, save_project

    save_project(build_project(source_text, title), project_dir)
    return [
        "project.yaml",
        "script.md",
        "assets.md",
        "storyboard.md",
        "sound.md",
        "prompts.md",
        "qa.md",
    ]


def _write_task_manifest(project_dir: Path, task_manifest: dict[str, Any], task_group: str) -> list[str]:
    _write_json(project_dir / TASKS_FILENAME, task_manifest)
    return [f"{TASKS_FILENAME}#{task_group}"]


def _save_assembly_plan(project_dir: Path, assembly_plan: dict[str, Any]) -> list[str]:
    _write_json(project_dir / ASSEMBLY_FILENAME, assembly_plan)
    return [ASSEMBLY_FILENAME]


def _run_package_qa_export(project_dir: Path) -> list[str]:
    export_project(_load_project(project_dir), project_dir)
    return ["qa.md", "exports/"]
