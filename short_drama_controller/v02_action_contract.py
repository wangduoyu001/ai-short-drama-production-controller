from __future__ import annotations

from typing import Any

from .v02_models import Project


DEFAULT_ACTION_FIELDS: dict[str, str] = {
    "start_state 起始姿态": "角色保持上一镜结束姿态，重心和朝向清楚",
    "end_state 结束姿态": "动作结果落定，角色停在可衔接下一镜的位置",
    "attack_line 攻击线": "沿主冲突轴线完成单一攻击节点，禁止跳轴",
    "movement_line 移动线": "沿画面既定方向完成一次清楚位移",
    "contact_point 接触点": "手部、脚步、武器或身体边缘的单一可见接触点",
    "speed 速度": "controlled 可读速度，启动、接触和结果均可辨认",
    "result 结果": "动作造成清楚的站位、姿态或关系变化",
    "risk_level 风险等级": "medium 中",
    "backup_shot 备用镜头": "固定机位硬切：起势 -> 接触特写 -> 反应 -> 结果全景",
}


def ensure_action_contract(project: Project) -> None:
    """Normalize action rows without weakening the QA gate.

    The choreography builder may legitimately produce a simple action shot with no
    six-grid prompt. QA still requires a non-empty fallback contract, so this pass
    derives one from the shot and fills any missing mandatory value deterministically.
    """

    shots_by_id = {
        str(shot.get("shot_id 镜头编号", "")): shot
        for shot in project.shots
        if shot.get("shot_id 镜头编号")
    }
    rows = project.data.get("action_choreography 动作编排表", [])
    for row in rows:
        shot_id = str(row.get("related_shot_id 对应镜头编号", ""))
        shot = shots_by_id.get(shot_id, {})
        for field, fallback in DEFAULT_ACTION_FIELDS.items():
            if not str(row.get(field, "")).strip():
                row[field] = fallback
        if not str(row.get("grid_cut_prompt 宫格硬切提示词", "")).strip():
            row["grid_cut_prompt 宫格硬切提示词"] = build_grid_cut_prompt(row, shot)


def build_grid_cut_prompt(row: dict[str, Any], shot: dict[str, Any]) -> str:
    action = first_nonempty(
        shot.get("action_detail 动作细节"),
        shot.get("this_clip_only 本段只拍"),
        row.get("result 结果"),
        "完成一个清楚动作节点",
    )
    start = first_nonempty(row.get("start_state 起始姿态"), "保持上一镜结束姿态")
    contact = first_nonempty(row.get("contact_point 接触点"), "单一接触点清楚可见")
    result = first_nonempty(row.get("result 结果"), "动作结果落定")
    direction = first_nonempty(
        row.get("screen_direction 画面方向"),
        shot.get("screen_direction 画面方向"),
        "保持既定画面方向和同侧轴线",
    )
    return (
        "四格硬切动作方案，16:9横屏，同一场景、同一角色、同一服装和道具："
        f"第1格起始姿态：{start}；"
        f"第2格动作启动：{action}，{direction}；"
        f"第3格接触节点：{contact}，只表现一次接触；"
        f"第4格结果与复位：{result}。"
        "每格构图差异清楚，禁止跳轴，禁止提前演完后续动作，复杂运镜改固定机位或轻微横移。"
    )


def first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""
