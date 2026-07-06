from __future__ import annotations

from typing import Any

from .v02_dialogue import force_reverse_shot_units
from .v02_models import Project

ALLOWED_CAMERA = {
    "fixed_camera 固定机位",
    "slow_push_in 缓慢推进",
    "slight_lateral_move 轻微横移",
    "subtle_handheld 轻微手持",
}


def build_shots(project: Project) -> None:
    scene = project.scenes[0]
    char_a = project.characters[0]
    char_b = project.characters[1] if len(project.characters) > 1 else project.characters[0]
    units = force_reverse_shot_units(project.data.get("dialogue_lines 对白列表", []))
    shots = [make_shot("SH001", "master_shot 主镜头", scene, [char_a, char_b], "建立空间和轴线", "无", "无", 1)]

    for unit in units[:5]:
        speaker = char_a if unit["speaker_name 说话人"] in [char_a["character_name 角色名"], "主角"] else char_b
        purpose = "shot_a A正打" if speaker == char_a else "shot_b B反打"
        shots.append(make_shot(
            f"SH{len(shots)+1:03d}", purpose, scene, [speaker],
            f"{speaker['character_name 角色名']}发声或保持闭口",
            unit["dialogue_line 出口对白"], unit["os_line 画外音"], len(shots)+1,
        ))
        if len(shots) == 4:
            shots.append(make_shot("SH005", "insert_shot 插入镜头", scene, [char_a], "手部或道具特写", "无", "无", 5))

    while len(shots) < 8:
        if len(shots) == 6:
            purpose = "movement_result 运动结果"
            chars = [char_a, char_b]
        elif len(shots) < 7:
            purpose = "reaction_shot 反应镜头"
            chars = [char_b]
        else:
            purpose = "hook_shot 结尾钩子"
            chars = [char_a]
        shots.append(make_shot(f"SH{len(shots)+1:03d}", purpose, scene, chars, "情绪或动作推进", "无", "无", len(shots)+1))

    project.data["blocking_plan 人物调度计划"] = {
        "axis_line 轴线": "CHAR_A与CHAR_B连线",
        "safe_camera_zone 安全机位区": "摄影机保持在轴线同侧",
        "eyeline_a A视线方向": "A看向画面右",
        "eyeline_b B视线方向": "B看向画面左",
    }
    project.data["shots 分镜列表"] = shots[:12]


def make_shot(shot_id: str, purpose: str, scene: dict[str, Any], chars: list[dict[str, Any]], action: str, dialogue: str, os_line: str, index: int) -> dict[str, Any]:
    camera = "slow_push_in 缓慢推进" if "shot_" in purpose else "slight_lateral_move 轻微横移" if "movement" in purpose else "fixed_camera 固定机位"
    if camera not in ALLOWED_CAMERA:
        camera = "fixed_camera 固定机位"
    speaker_mode = "spoken_dialogue 出口对白" if dialogue != "无" else "os_voice OS画外音" if os_line != "无" else "none 无"
    shot_sizes = ["全景 WS", "近景 CU", "近景 CU", "特写 ECU", "中近景 MCU", "近景 CU", "中景 MS", "中近景 MCU"]
    return {
        "shot_id 镜头编号": shot_id,
        "shot_purpose 镜头目的": purpose,
        "scene_id 场景编号": scene["scene_id 场景编号"],
        "location_name 场景名称": scene["scene_name 场景名"],
        "on_screen_characters 在场人物": [c["character_id 角色编号"] for c in chars],
        "focus_character 画面主体": chars[0]["character_id 角色编号"],
        "speaker_mode 发声模式": speaker_mode,
        "speaker_spatial_anchor 说话人空间锚点": chars[0]["spatial_anchor 空间锚点"] + "，" + chars[0]["clothing_lock 服装锁定"],
        "mouth_state 嘴型状态": "speaker_open 说话人开口" if dialogue != "无" else "all_closed 全员闭口",
        "dialogue_line 出口对白": dialogue,
        "os_line 画外音": os_line,
        "shot_size 景别": shot_sizes[min(index - 1, len(shot_sizes) - 1)],
        "camera_angle 机位角度": "轴线同侧，侧前方约30度",
        "camera_movement 机位运动": camera,
        "camera_axis 轴线方向": "A-B连线，摄影机在同侧",
        "motion_path 运动轨迹": "无大位移；如有运动，只保留起势、特写、结果",
        "entry_pose 起始姿态": "运动或情绪起点明确",
        "exit_pose 结束姿态": "运动结果或情绪落点明确",
        "action_detail 动作细节": action,
        "continuity_locks 连续性锁定": "同脸、同发型、同服装、同道具、同站位逻辑",
        "fallback_shot 备用镜头": "改为侧脸、背影、手部、道具或反应镜头",
    }
