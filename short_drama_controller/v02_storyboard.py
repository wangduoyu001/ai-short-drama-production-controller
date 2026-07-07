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
    director_read = build_director_read(project.data.get("source_text 原文", ""), scene, char_a, char_b)
    project.data["director_read 导演读本"] = director_read
    project.data["project_state_capsule 项目状态胶囊"] = build_state_capsule(project, director_read)
    project.data["producer_plan 制片执行计划"] = build_producer_plan(project)

    units = force_reverse_shot_units(project.data.get("dialogue_lines 对白列表", []))
    shots = [make_shot("SH001", "master_shot 主镜头", scene, [char_a, char_b], "建立空间和轴线", "无", "无", 1, director_read)]

    for unit in units[:5]:
        speaker = char_a if unit["speaker_name 说话人"] in [char_a["character_name 角色名"], "主角"] else char_b
        purpose = "shot_a A正打" if speaker == char_a else "shot_b B反打"
        shots.append(make_shot(
            f"SH{len(shots)+1:03d}", purpose, scene, [speaker],
            f"{speaker['character_name 角色名']}发声或保持闭口",
            unit["dialogue_line 出口对白"], unit["os_line 画外音"], len(shots)+1, director_read,
        ))
        if len(shots) == 4:
            shots.append(make_shot("SH005", "insert_shot 插入镜头", scene, [char_a], "手部或道具特写", "无", "无", 5, director_read))

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
        shots.append(make_shot(f"SH{len(shots)+1:03d}", purpose, scene, chars, "情绪或动作推进", "无", "无", len(shots)+1, director_read))

    project.data["blocking_plan 人物调度计划"] = {
        "axis_line 轴线": "CHAR_A与CHAR_B连线",
        "safe_camera_zone 安全机位区": "摄影机保持在轴线同侧",
        "eyeline_a A视线方向": "A看向画面右",
        "eyeline_b B视线方向": "B看向画面左",
    }
    project.data["shots 分镜列表"] = shots[:12]


def build_director_read(text: str, scene: dict[str, Any], char_a: dict[str, Any], char_b: dict[str, Any]) -> dict[str, str]:
    return {
        "scene_function 场景功能": "建立人物关系并推动一次明确转折",
        "scene_turn 场景转折": "从试探或压迫，转为角色立场被看见",
        "pov_empathy 观众视角与共情位置": f"观众站在{char_a['character_name 角色名']}附近，感受其压力和选择",
        "power_shift 权力变化": f"{char_b['character_name 角色名']}起初占据压迫位，随后{char_a['character_name 角色名']}用行动或台词夺回主动",
        "subtext 潜台词": "人物表面说话，真实冲突在沉默、停顿、手部动作和视线里发生",
        "director_intent 导演意图": "让观众感觉主角不是在解释自己，而是在用可见动作证明自己还有退路或底牌",
        "directorial_voice 导演声音": "克制写实、少运镜、重表演动作、重环境声，不堆空泛电影感",
    }


def build_state_capsule(project: Project, director_read: dict[str, str]) -> dict[str, Any]:
    return {
        "accepted_clip 已接受片段": "none 尚未生成",
        "observed_start_state 实际起始状态": "待用户回填",
        "observed_end_state 实际结束状态": "待用户回填",
        "character_state 角色状态": [c.get("character_name 角色名", "") for c in project.characters],
        "scene_state 场景状态": [s.get("scene_name 场景名", "") for s in project.scenes],
        "prop_state 道具状态": [p.get("prop_name 道具名", "") for p in project.props],
        "director_intent 导演意图": director_read["director_intent 导演意图"],
        "next_clip_task 下一段任务": "先生成本段，用户确认实际结尾后再写下一段",
    }


def build_producer_plan(project: Project) -> dict[str, Any]:
    return {
        "production_scope 制作范围": "60-90秒，8-12镜，2-3个主要角色，1个主场景，先跑通样片流程",
        "episode_goal 本集目标": "把原文拆成可生成视频的导演物料包，不直接交付成片",
        "duration_plan 时长计划": "每镜约4-8秒，复杂动作拆成插入镜头或宫格硬切",
        "clip_plan 分段计划": "默认先做CLIP01；下一段必须基于用户确认的实际结尾继续",
        "asset_checklist 素材清单": ["角色三视图或脸部参考", "主场景概念图", "关键道具图", "首帧图或上一段末帧"],
        "platform_plan 平台生成计划": "先输出通用提示词，再按即梦、可灵、LibTV、ComfyUI等平台适配",
        "risk_log 风险记录": ["人物一致性", "口型误开", "动作崩坏", "场景跳变", "声音与对白冲突"],
        "approval_gates 审批节点": ["确认原文覆盖", "确认资产锁", "确认分镜", "确认提示词", "确认实际生成结尾"],
        "retake_budget 返修预算": "每个关键镜头优先2-3次；每次只改一个变量",
        "cost_note 成本备注": "高风险动作镜头先低成本测试，不直接批量生成",
    }


def make_shot(shot_id: str, purpose: str, scene: dict[str, Any], chars: list[dict[str, Any]], action: str, dialogue: str, os_line: str, index: int, director_read: dict[str, str]) -> dict[str, Any]:
    camera = "slow_push_in 缓慢推进" if "shot_" in purpose else "slight_lateral_move 轻微横移" if "movement" in purpose else "fixed_camera 固定机位"
    if camera not in ALLOWED_CAMERA:
        camera = "fixed_camera 固定机位"
    speaker_mode = "spoken_dialogue 出口对白" if dialogue != "无" else "os_voice OS画外音" if os_line != "无" else "none 无"
    shot_sizes = ["全景 WS", "近景 CU", "近景 CU", "特写 ECU", "中近景 MCU", "近景 CU", "中景 MS", "中近景 MCU"]
    entry_pose = "运动或情绪起点明确"
    exit_pose = "运动结果或情绪落点明确"
    return {
        "shot_id 镜头编号": shot_id,
        "clip_id 单段编号": "CLIP01",
        "shot_purpose 镜头目的": purpose,
        "scene_id 场景编号": scene["scene_id 场景编号"],
        "location_name 场景名称": scene["scene_name 场景名"],
        "scene_function 场景功能": director_read["scene_function 场景功能"],
        "scene_turn 场景转折": director_read["scene_turn 场景转折"],
        "pov_empathy 观众视角与共情位置": director_read["pov_empathy 观众视角与共情位置"],
        "power_shift 权力变化": director_read["power_shift 权力变化"],
        "subtext 潜台词": director_read["subtext 潜台词"],
        "director_intent 导演意图": director_read["director_intent 导演意图"],
        "felt_intent 观众感受目标": "观众能明确感到本镜头推进了压力、选择或立场变化",
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
        "sketch_ascii 简笔手绘图": build_sketch(purpose),
        "movement_arrow 运动箭头": build_movement_arrow(purpose),
        "camera_arrow 镜头箭头": build_camera_arrow(camera),
        "screen_direction 画面方向": "A在画面左侧，B在画面右侧；保持同侧轴线，不跳轴",
        "motion_path 运动轨迹": "无大位移；如有运动，只保留起势、特写、结果",
        "entry_pose 起始姿态": entry_pose,
        "exit_pose 结束姿态": exit_pose,
        "action_detail 动作细节": action,
        "performance_action 表演动作": f"用一个可见动作承载潜台词：{action}",
        "this_clip_only 本段只拍": action,
        "reserved_for_later 后续保留": "后续反转、升级冲突或新场景，不在本镜提前完成",
        "planned_start_state 计划起始状态": entry_pose,
        "planned_end_state 计划结束状态": exit_pose,
        "observed_end_state 实际生成结尾状态": "待用户回填",
        "continuity_locks 连续性锁定": "同脸、同发型、同服装、同道具、同站位逻辑",
        "allowed_changes 允许变化": "只允许表情、手部小动作、光线轻微变化",
        "retake_variable 本次返修变量": "none 未返修；返修时一次只改一个变量",
        "fallback_shot 备用镜头": "改为侧脸、背影、手部、道具或反应镜头",
    }


def build_sketch(purpose: str) -> str:
    if "master" in purpose:
        return """┌──────────── 画面构图 ────────────┐
│ A○ 左侧三分之一       右侧三分之一 ○B │
│    视线 →──────────────← 视线        │
│                                      │
│              ▣ 摄影机                │
└──────────────────────────────────────┘"""
    if "shot_a" in purpose:
        return """┌──────────── 画面构图 ────────────┐
│ A○ 近景占画面左/中                  │
│  视线 → 向画面右，B保持画外方向       │
│                                      │
│          ▣ 摄影机：侧前方30度         │
└──────────────────────────────────────┘"""
    if "shot_b" in purpose:
        return """┌──────────── 画面构图 ────────────┐
│                  B○ 近景占画面右/中  │
│       A保持画外方向，← 视线           │
│                                      │
│          ▣ 摄影机：侧前方30度         │
└──────────────────────────────────────┘"""
    if "insert" in purpose:
        return """┌──────────── 画面构图 ────────────┐
│          手部/道具 特写 ECU          │
│              ○───▶ 触碰/握紧/停顿     │
│                                      │
│              ▣ 固定特写              │
└──────────────────────────────────────┘"""
    if "movement" in purpose:
        return """┌──────────── 画面构图 ────────────┐
│ A○ 起点 ───────▶ 结果位置        ○B │
│       动作方向保持左 → 右             │
│                                      │
│          ▣ 摄影机轻微横移跟随         │
└──────────────────────────────────────┘"""
    if "reaction" in purpose:
        return """┌──────────── 画面构图 ────────────┐
│                  B○ 反应近景         │
│       ← 视线回看画面左侧事件          │
│                                      │
│              ▣ 固定机位              │
└──────────────────────────────────────┘"""
    return """┌──────────── 画面构图 ────────────┐
│ A○ 前景/中景                         │
│       视线或身体朝向 → 未知威胁/下一镜 │
│                                      │
│              ▣ 固定机位              │
└──────────────────────────────────────┘"""


def build_movement_arrow(purpose: str) -> str:
    if "movement" in purpose:
        return "A 左侧起点 → 画面中部结果位；只保留动作结果，不做复杂连续打斗"
    if "insert" in purpose:
        return "手部/道具：静止 → 轻触/握紧 → 停顿"
    if "shot_b" in purpose:
        return "视线方向：B → 画面左侧"
    return "视线方向：A → 画面右侧；人物大位置不变"


def build_camera_arrow(camera: str) -> str:
    if camera == "slow_push_in 缓慢推进":
        return "摄影机：▣ → 轻微向前推进"
    if camera == "slight_lateral_move 轻微横移":
        return "摄影机：▣ 左右轻微横移，不跨轴线"
    if camera == "subtle_handheld 轻微手持":
        return "摄影机：▣ 轻微手持晃动，保持主体稳定"
    return "摄影机：▣ 固定不动"
