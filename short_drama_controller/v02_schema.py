from __future__ import annotations

from typing import Any


def validate_schema(data: dict[str, Any]) -> list[dict[str, str]]:
    problems: list[dict[str, str]] = []
    required_project = [
        "project_name 项目名",
        "skill_version 技能版本",
        "source_text 原文",
        "characters 角色列表",
        "scenes 场景列表",
        "props 道具列表",
        "shots 分镜列表",
    ]
    for key in required_project:
        if key not in data:
            problems.append(problem("schema.project_missing", f"缺少项目字段：{key}"))
    shots = data.get("shots 分镜列表")
    if not isinstance(shots, list):
        problems.append(problem("schema.shots_invalid", "shots 分镜列表必须是数组"))
        return problems
    required_shot = [
        "shot_id 镜头编号",
        "speaker_spatial_anchor 说话人空间锚点",
        "shot_size 景别",
        "camera_movement 机位运动",
        "motion_path 运动轨迹",
        "fallback_shot 备用镜头",
    ]
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            problems.append(problem("schema.shot_invalid", f"第{index}个镜头必须是对象"))
            continue
        shot_id = shot.get("shot_id 镜头编号", f"SH{index:03d}")
        for key in required_shot:
            if key not in shot:
                problems.append(problem("schema.shot_missing", f"{shot_id} 缺少 {key}"))
    return problems


def problem(code: str, message: str) -> dict[str, str]:
    return {
        "level 等级": "BLOCKER",
        "code 代码": code,
        "message 信息": message,
        "repair_action 返修动作": "ADD 补充",
    }
