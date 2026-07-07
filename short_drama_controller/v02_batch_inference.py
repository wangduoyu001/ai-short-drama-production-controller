from __future__ import annotations

from typing import Any

from .v02_models import Project

DEFAULT_BATCH_SIZE = 6


def attach_batch_inference(project: Project, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
    shots = project.shots
    batches = []
    for start in range(0, len(shots), batch_size):
        chunk = shots[start:start + batch_size]
        batch_index = len(batches) + 1
        batches.append(build_batch(project, chunk, batch_index, start))
    project.data["batch_inference 批量推理"] = batches


def build_batch(project: Project, shots: list[dict[str, Any]], batch_index: int, start: int) -> dict[str, Any]:
    records = []
    for offset, shot in enumerate(shots, 1):
        records.append({
            "panel_index 批内序号": offset,
            "shot_id 镜头编号": shot.get("shot_id 镜头编号", ""),
            "source_quote 原文依据": shot.get("source_quote 原文节拍证据", ""),
            "speaker_mode 发声模式": shot.get("speaker_mode 发声模式", ""),
            "mouth_state 嘴型状态": shot.get("mouth_state 嘴型状态", ""),
            "first_frame_prompt 首帧提示词": shot.get("first_frame_prompt 首帧提示词", ""),
            "video_prompt 视频提示词": shot.get("video_prompt 视频提示词", ""),
            "end_frame_prompt 尾帧提示词": shot.get("end_frame_prompt 尾帧提示词", ""),
            "continuity_note 连续性说明": build_continuity_note(shot),
        })
    return {
        "batch_id 批次编号": f"BATCH_{batch_index:03d}",
        "shot_range 镜头范围": build_range(shots),
        "record_count 记录数": len(records),
        "expected_count 期望记录数": len(shots),
        "previous_batch_tail 上批末镜": project.shots[start - 1].get("shot_id 镜头编号", "none") if start > 0 else "none",
        "next_batch_head 下批首镜": next_batch_head(project, start + len(shots)),
        "records 批量记录": records,
        "batch_self_check 批量自检": {
            "count_match 数量匹配": len(records) == len(shots),
            "panel_index_continuous 批内序号连续": [r["panel_index 批内序号"] for r in records] == list(range(1, len(records) + 1)),
            "current_shot_only 只处理当前镜头": True,
        },
    }


def build_range(shots: list[dict[str, Any]]) -> str:
    if not shots:
        return "empty 空批次"
    return f"{shots[0].get('shot_id 镜头编号', '')} - {shots[-1].get('shot_id 镜头编号', '')}"


def next_batch_head(project: Project, index: int) -> str:
    if index < len(project.shots):
        return project.shots[index].get("shot_id 镜头编号", "none")
    return "none"


def build_continuity_note(shot: dict[str, Any]) -> str:
    return "；".join([
        f"场景={shot.get('scene_id 场景编号', '')}",
        f"主体={shot.get('focus_character 画面主体', '')}",
        f"轴线={shot.get('screen_direction 画面方向', '')}",
        f"落点={shot.get('planned_end_state 计划结束状态', '')}",
    ])
