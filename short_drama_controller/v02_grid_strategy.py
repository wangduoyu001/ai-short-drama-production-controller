from __future__ import annotations

from typing import Any

from .v02_models import Project


def attach_grid_strategy(project: Project) -> None:
    for shot in project.shots:
        strategy = choose_grid_strategy(shot)
        shot["grid_strategy 宫格策略"] = strategy


def choose_grid_strategy(shot: dict[str, Any]) -> dict[str, Any]:
    character_count = count_characters(shot.get("on_screen_characters 在场人物", []))
    clip_type = str(shot.get("clip_type 片段类型", ""))
    dialogue = str(shot.get("dialogue_line 出口对白", ""))
    action = str(shot.get("action_detail 动作细节", ""))
    speaker = str(shot.get("speaker_mode 发声模式", ""))
    risk_score = score_risk(character_count, clip_type, dialogue, action, speaker)

    if risk_score >= 5:
        mode = "six_grid 六宫格"
    elif risk_score >= 3:
        mode = "first_end_frame 首尾帧"
    else:
        mode = "single_video 单镜视频"

    return {
        "strategy_mode 策略模式": mode,
        "risk_score 风险分": risk_score,
        "character_count 人物数": character_count,
        "reason 选择理由": build_reason(character_count, clip_type, dialogue, action, speaker),
        "usage_note 使用说明": "仅在高风险镜头启用宫格；普通镜头保持单镜提示词",
    }


def count_characters(value: Any) -> int:
    if isinstance(value, list):
        return len([item for item in value if item])
    if not value:
        return 0
    return 1


def score_risk(character_count: int, clip_type: str, dialogue: str, action: str, speaker: str) -> int:
    score = 0
    if character_count >= 3:
        score += 2
    elif character_count == 2:
        score += 1
    if "fight" in clip_type or "action" in clip_type:
        score += 2
    if dialogue:
        score += 1
    if "OS" in speaker or "画外" in speaker:
        score += 1
    if any(word in action for word in ["抓", "推", "碰", "递", "拿", "撞", "转身"]):
        score += 1
    return score


def build_reason(character_count: int, clip_type: str, dialogue: str, action: str, speaker: str) -> str:
    reasons = []
    if character_count >= 2:
        reasons.append("多人物需要空间锚点")
    if "fight" in clip_type or "action" in clip_type:
        reasons.append("动作镜头需要拆节点")
    if dialogue:
        reasons.append("对白需要说话人和嘴型控制")
    if "OS" in speaker or "画外" in speaker:
        reasons.append("画外音需要闭口控制")
    if any(word in action for word in ["抓", "推", "碰", "递", "拿", "撞", "转身"]):
        reasons.append("道具或肢体接触风险")
    return "；".join(reasons) if reasons else "低风险镜头"
