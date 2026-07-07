from __future__ import annotations

from typing import Any

MIN_CLIP_SECONDS = 4
MAX_CLIP_SECONDS = 15
DEFAULT_MODEL_LIMIT = "4-15秒，按当前主流视频生成模型短片段限制处理"

FIGHT_WORDS = ["打", "杀", "砍", "劈", "刺", "挡", "格", "拳", "掌", "踢", "摔", "冲", "退", "闪", "刀", "剑", "枪", "血"]
ACTION_WORDS = ["追", "逃", "跑", "推", "拉", "转身", "拔", "握", "撞", "倒", "护送", "冲进", "闯入"]
TRANSITION_WORDS = ["来到", "走进", "离开", "门外", "转场", "次日", "夜色", "雨夜", "山路", "街", "客栈", "城门"]
EMOTION_WORDS = ["沉默", "低声", "冷笑", "盯着", "看着", "颤", "咬牙", "停顿", "没有回头"]

CLIP_PROFILES: dict[str, dict[str, Any]] = {
    "dialogue_clip 对白片段": {"duration_seconds": 12, "shot_min": 3, "shot_target": 5, "shot_max": 6, "density": "3-6镜/10-15秒"},
    "action_clip 动作片段": {"duration_seconds": 12, "shot_min": 6, "shot_target": 8, "shot_max": 12, "density": "6-12镜/10-15秒"},
    "fight_clip 打戏片段": {"duration_seconds": 15, "shot_min": 10, "shot_target": 14, "shot_max": 24, "density": "10-24镜/10-15秒"},
    "transition_clip 转场片段": {"duration_seconds": 6, "shot_min": 1, "shot_target": 3, "shot_max": 4, "density": "1-4镜/4-8秒"},
    "emotion_clip 情绪片段": {"duration_seconds": 10, "shot_min": 2, "shot_target": 4, "shot_max": 5, "density": "2-5镜/8-12秒"},
    "establishing_clip 建立空间片段": {"duration_seconds": 6, "shot_min": 1, "shot_target": 3, "shot_max": 4, "density": "1-4镜/4-8秒"},
}

VALID_CLIP_TYPES = set(CLIP_PROFILES)


def classify_clip_type(text: str, dialogue: str = "", action: str = "") -> str:
    combined = f"{text} {dialogue} {action}"
    if any(word in combined for word in FIGHT_WORDS):
        return "fight_clip 打戏片段"
    if any(word in combined for word in ACTION_WORDS):
        return "action_clip 动作片段"
    if dialogue and dialogue != "无":
        return "dialogue_clip 对白片段"
    if any(word in combined for word in TRANSITION_WORDS):
        return "transition_clip 转场片段"
    if any(word in combined for word in EMOTION_WORDS):
        return "emotion_clip 情绪片段"
    return "establishing_clip 建立空间片段"


def get_clip_profile(clip_type: str) -> dict[str, Any]:
    return CLIP_PROFILES.get(clip_type, CLIP_PROFILES["establishing_clip 建立空间片段"])


def build_clip_plan_and_beats(source_beats: list[dict[str, str]], max_episode_shots: int = 48) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    clip_plan: list[dict[str, Any]] = []
    expanded: list[dict[str, str]] = []
    if not source_beats:
        return clip_plan, expanded

    for source_index, source_beat in enumerate(source_beats, start=1):
        clip_id = f"CLIP{source_index:03d}"
        clip_type = classify_clip_type(
            source_beat.get("source_quote 原文证据", ""),
            source_beat.get("dialogue 对白", ""),
            source_beat.get("visible_action 可见动作", ""),
        )
        profile = get_clip_profile(clip_type)
        target = int(profile["shot_target"])
        start_global = len(expanded) + 1

        for local_index in range(1, target + 1):
            if len(expanded) >= max_episode_shots:
                break
            if local_index == 1:
                beat = dict(source_beat)
                beat["coverage_role 覆盖功能"] = "source 源节拍"
            else:
                beat = make_clip_coverage_beat(source_beat, clip_type, local_index)
            beat["clip_id 片段编号"] = clip_id
            beat["clip_type 片段类型"] = clip_type
            beat["clip_duration_seconds 片段时长秒数"] = str(profile["duration_seconds"])
            beat["model_duration_limit 模型时长限制"] = DEFAULT_MODEL_LIMIT
            beat["shot_density 镜头密度"] = profile["density"]
            beat["clip_shot_index 片段内镜头序号"] = str(local_index)
            beat["beat_id 节拍编号"] = f"B{len(expanded) + 1:03d}"
            expanded.append(beat)

        end_global = len(expanded)
        clip_plan.append({
            "clip_id 片段编号": clip_id,
            "clip_type 片段类型": clip_type,
            "duration_seconds 时长秒数": profile["duration_seconds"],
            "model_duration_limit 模型时长限制": DEFAULT_MODEL_LIMIT,
            "scene_hint 场景建议": source_beat.get("scene_hint 场景建议", ""),
            "characters 相关角色": source_beat.get("characters 相关角色", ""),
            "beat_range 节拍范围": f"B{start_global:03d}-B{end_global:03d}",
            "shot_density 镜头密度": profile["density"],
            "shot_count_target 目标镜头数": end_global - start_global + 1,
        })

        if len(expanded) >= max_episode_shots:
            break

    return clip_plan, expanded


def make_clip_coverage_beat(base: dict[str, str], clip_type: str, local_index: int) -> dict[str, str]:
    visible = base.get("visible_action 可见动作", "")
    focus = base.get("characters 相关角色", "主角")
    scene_hint = base.get("scene_hint 场景建议", "")
    source_quote = base.get("source_quote 原文证据", "")

    role, action, hint = coverage_role_action_hint(clip_type, local_index, visible, focus)
    return {
        **base,
        "source_quote 原文证据": source_quote,
        "visible_action 可见动作": action,
        "dialogue 对白": "无",
        "emotion_shift 情绪变化": base.get("emotion_shift 情绪变化", "情绪继续推进"),
        "power_shift 权力变化": base.get("power_shift 权力变化", "权力关系继续变化"),
        "subtext 潜台词": base.get("subtext 潜台词", "动作背后保留未说破的态度"),
        "shot_hint 镜头建议": hint,
        "scene_hint 场景建议": scene_hint,
        "characters 相关角色": focus,
        "coverage_role 覆盖功能": role,
    }


def coverage_role_action_hint(clip_type: str, local_index: int, visible: str, focus: str) -> tuple[str, str, str]:
    if clip_type == "fight_clip 打戏片段":
        steps = [
            ("attack_setup 起势", f"{focus}压低重心，兵器或拳脚进入起势位置", "movement_result 运动结果"),
            ("footwork 接近", f"{focus}用一步快速接近，身体方向保持清楚", "movement_result 运动结果"),
            ("weapon_detail 兵器特写", f"兵器、手腕或脚步特写承接动作：{visible}", "insert_shot 插入镜头"),
            ("contact 接触", "攻击与格挡发生接触，动作只表现一个清楚节点", "movement_result 运动结果"),
            ("block 格挡", "防守方挡住冲击，身体被迫后移半步", "movement_result 运动结果"),
            ("counter 反击", "反击从侧面切入，动作短促，不连续乱打", "movement_result 运动结果"),
            ("off_balance 失衡", "一方重心被打乱，衣摆或道具产生反馈", "reaction_shot 反应镜头"),
            ("reaction 反应", f"{focus}停顿半秒，眼神确认下一次攻击方向", "reaction_shot 反应镜头"),
            ("environment_feedback 环境反馈", "脚步、灰尘、门帘或道具反馈刚才冲击", "insert_shot 插入镜头"),
            ("reset_position 重置站位", "双方重新拉开距离，回到可继续打的站位", "master_shot 主镜头"),
        ]
        return steps[(local_index - 2) % len(steps)]

    if clip_type == "action_clip 动作片段":
        steps = [
            ("action_start 动作起点", f"{focus}从当前姿态启动动作：{visible}", "movement_result 运动结果"),
            ("approach 接近", "角色向目标方向推进一步，空间方向保持明确", "movement_result 运动结果"),
            ("detail 插入", "手部、脚步或道具特写承接动作", "insert_shot 插入镜头"),
            ("result 结果", "动作结果落在站位变化或对方反应上", "reaction_shot 反应镜头"),
            ("hold 收束", "角色在结果位置停住，为下一镜留接口", "hook_shot 结尾钩子"),
        ]
        return steps[(local_index - 2) % len(steps)]

    if clip_type == "dialogue_clip 对白片段":
        steps = [
            ("reverse 反打", "对方听完后停顿，视线压回说话方向", "shot_b B反打"),
            ("reaction 反应", f"{focus}在对白后的半秒里收住表情", "reaction_shot 反应镜头"),
            ("insert 插入", "手部或道具细节暴露人物态度", "insert_shot 插入镜头"),
            ("master 回主镜", "回到双人空间，保持轴线和距离", "master_shot 主镜头"),
        ]
        return steps[(local_index - 2) % len(steps)]

    if clip_type == "transition_clip 转场片段":
        steps = [
            ("establish 建立", f"建立新场景空间和方向：{visible}", "master_shot 主镜头"),
            ("detail 环境细节", "场景固定物件或光线细节作为转场锚点", "insert_shot 插入镜头"),
            ("arrival 到达", f"{focus}进入或离开场景，方向清楚", "movement_result 运动结果"),
        ]
        return steps[(local_index - 2) % len(steps)]

    if clip_type == "emotion_clip 情绪片段":
        steps = [
            ("face 表情", f"{focus}眼神停住，表情只变化一次", "reaction_shot 反应镜头"),
            ("hand 手部", "手部轻微收紧或放松，承载潜台词", "insert_shot 插入镜头"),
            ("silence 静默", f"{focus}保持沉默，环境声顶上来", "hook_shot 结尾钩子"),
        ]
        return steps[(local_index - 2) % len(steps)]

    steps = [
        ("space 建立空间", f"建立场景空间，明确人物和道具位置：{visible}", "master_shot 主镜头"),
        ("detail 空间细节", "固定物件或光线细节作为空间锚点", "insert_shot 插入镜头"),
    ]
    return steps[(local_index - 2) % len(steps)]
