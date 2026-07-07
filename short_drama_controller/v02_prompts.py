from __future__ import annotations

from .v02_models import Project

VISUAL_ONLY_FIELDS = [
    "人物", "服装", "场景", "道具", "构图", "景别", "光线", "色彩", "前中后景", "画幅比例",
]
ABSTRACT_WORDS = ["让观众", "感觉", "潜台词", "权力变化", "导演意图", "观众感受", "证明自己", "退路", "底牌"]


def attach_sound_and_prompts(project: Project) -> None:
    project.data["sound_plan 声音设计计划"] = build_sound_plan(project)
    for shot in project.shots:
        add_sound(shot)
        shot["image_prompt 图片提示词"] = build_image_prompt(project, shot)
        shot["video_prompt 视频提示词"] = build_video_prompt(project, shot)
        shot["grid_prompt 宫格提示词"] = build_grid_prompt(shot) if should_use_grid_prompt(shot) else ""


def build_sound_plan(project: Project) -> dict:
    return {
        "dialogue_map 对白地图": "出口对白只允许当前说话人开口，必须绑定说话人空间锚点",
        "os_voice_map 画外音地图": "OS画外音、内心独白、旁白时画面人物全员闭口",
        "ambience_map 环境音地图": "每镜保留稳定环境底音，避免声音断层",
        "foley_map 拟音地图": "脚步、衣料、手部触碰按镜头补充，不抢对白",
        "action_sfx_map 动作音效地图": "动作镜头才加短促动作音，普通对白镜头不乱加",
        "music_plan 音乐设计": "低频克制，随冲突轻微推进，不压对白",
        "silence_plan 静默设计": "关键反应和转折前后保留短暂停顿",
        "lip_sync_notes 口型同步备注": "出口对白写入视频提示词；旁白写入OS字段并保持闭口",
        "post_audio_notes 后期声音备注": "平台内生成和后期补音都可用本表；最终以可听清对白为第一优先级",
    }


def add_sound(shot: dict) -> None:
    action = shot.get("action_detail 动作细节", "")
    shot["ambience_sfx 环境底音"] = "微风、远处环境空响、稳定场景底噪"
    shot["foley_sfx 拟音"] = "脚步、衣料轻微摩擦"
    shot["prop_sfx 道具音"] = "道具轻触声" if any(x in action for x in ["剑", "刀", "道具", "手", "握", "碗", "门"]) else "无"
    shot["action_sfx 动作音"] = "短促动作音" if should_use_grid_prompt(shot) else "无"
    shot["music_note 音乐建议"] = "低频克制氛围，不压对白"
    shot["silence_note 静默说明"] = "对白前后保留短暂停顿"


def build_image_prompt(project: Project, shot: dict) -> str:
    scene = project.get_scene(shot["scene_id 场景编号"]) or {}
    characters = describe_characters(project, shot)
    parts = [
        scene.get("visual_prompt 视觉提示词", "主场景，固定空间结构"),
        characters,
        f"动作：{shot.get('action_detail 动作细节', '')}",
        f"景别：{shot.get('shot_size 景别', '')}",
        f"构图：{shot.get('screen_direction 画面方向', '')}",
        f"机位：{shot.get('camera_angle 机位角度', '')}",
        f"前中后景：{shot.get('layer_depth 前中后景', '')}",
        f"道具：{shot.get('prop_anchor 道具锚点', '')}",
        f"画幅比例：{shot.get('aspect_ratio 画幅比例', '16:9 横屏')}",
        "无字幕，无水印，人物一致，服装一致，脸部一致，道具不消失",
    ]
    return clean_visual_prompt("，".join(x for x in parts if x))


def describe_characters(project: Project, shot: dict) -> str:
    ids = set(shot.get("on_screen_characters 在场人物", []))
    if not ids:
        return "无人空镜，保留场景固定物件"
    items = []
    for char in project.characters:
        if char.get("character_id 角色编号") in ids:
            items.append("/".join([
                char.get("character_name 角色名", "角色"),
                char.get("face_shape 脸型", "固定脸型"),
                char.get("hair_style 发型", "固定发型"),
                char.get("clothing_lock 服装锁定", "固定服装"),
                char.get("spatial_anchor 空间锚点", "固定站位"),
            ]))
    return "人物：" + "；".join(items) if items else "人物：在场角色保持固定脸和固定服装"


def clean_visual_prompt(prompt: str) -> str:
    cleaned = prompt
    for word in ABSTRACT_WORDS:
        cleaned = cleaned.replace(word, "")
    return cleaned.replace("，，", "，").strip("，")


def build_video_prompt(project: Project, shot: dict) -> str:
    return "\n".join([
        f"shot_id 镜头编号：{shot['shot_id 镜头编号']}",
        f"beat_id 节拍编号：{shot.get('beat_id 节拍编号', '')}",
        f"clip_id 单段编号：{shot.get('clip_id 单段编号', 'CLIP01')}",
        f"source_quote 原文节拍证据：{shot.get('source_quote 原文节拍证据', '')}",
        f"director_intent 导演意图：{shot.get('director_intent 导演意图', '')}",
        f"felt_intent 观众感受目标：{shot.get('felt_intent 观众感受目标', '')}",
        f"this_clip_only 本段只拍：{shot.get('this_clip_only 本段只拍', '')}",
        f"reserved_for_later 后续保留：{shot.get('reserved_for_later 后续保留', '')}",
        f"speaker_mode 发声模式：{shot['speaker_mode 发声模式']}",
        f"speaker_spatial_anchor 说话人空间锚点：{shot['speaker_spatial_anchor 说话人空间锚点']}",
        f"mouth_state 嘴型状态：{shot['mouth_state 嘴型状态']}",
        f"performance_action 表演动作：{shot.get('performance_action 表演动作', shot['action_detail 动作细节'])}",
        f"motion_path 运动轨迹：{shot['motion_path 运动轨迹']}",
        f"camera_description 机位描述：{shot['shot_size 景别']}，{shot['camera_angle 机位角度']}，{shot['camera_movement 机位运动']}，{shot['camera_axis 轴线方向']}",
        f"dialogue_line 出口对白：{shot['dialogue_line 出口对白']}",
        f"os_line 画外音：{shot['os_line 画外音']}",
        f"ambience_sfx 环境底音：{shot['ambience_sfx 环境底音']}",
        f"foley_sfx 拟音：{shot['foley_sfx 拟音']}",
        f"prop_sfx 道具音：{shot['prop_sfx 道具音']}",
        f"action_sfx 动作音：{shot['action_sfx 动作音']}",
        f"music_note 音乐建议：{shot['music_note 音乐建议']}",
        f"planned_end_state 计划结束状态：{shot.get('planned_end_state 计划结束状态', '')}",
        f"observed_end_state 实际生成结尾状态：{shot.get('observed_end_state 实际生成结尾状态', '待用户回填')}",
        f"continuity_locks 连续性锁定：{shot['continuity_locks 连续性锁定']}",
        f"allowed_changes 允许变化：{shot.get('allowed_changes 允许变化', '')}",
        "negative_prompt 负面提示词：禁止换脸，禁止换服装，禁止跳轴，禁止复杂运镜，禁止道具消失，禁止字幕水印，禁止提前演完后续剧情",
        f"fallback_prompt 备用提示词：{shot['fallback_shot 备用镜头']}",
    ])


def should_use_grid_prompt(shot: dict) -> bool:
    action = shot.get("action_detail 动作细节", "")
    purpose = shot.get("shot_purpose 镜头目的", "")
    risk_words = ["movement", "insert", "运动", "result", "动作", "道具", "刀", "剑", "握", "推", "转身", "停下", "冲", "退", "门", "碗"]
    if any(x in purpose for x in risk_words):
        return True
    if any(x in action for x in risk_words):
        return True
    if len(shot.get("on_screen_characters 在场人物", [])) >= 2 and shot.get("speaker_mode 发声模式") == "none 无":
        return True
    return False


def is_high_risk(shot: dict) -> bool:
    return should_use_grid_prompt(shot)


def build_grid_prompt(shot: dict) -> str:
    action = shot.get("this_clip_only 本段只拍", shot.get("action_detail 动作细节", "本镜动作"))
    return f"""【视频总览】grid_cut_mode 宫格硬切模式；启用 black_frame_anchor 黑屏冻结锚；0.15秒纯黑屏后，子格2-6硬切；世界连续，镜头跳变，同侧轴线；本段只拍：{action}。
【子格1-左上(黑屏)】像素级纯黑屏，无画面元素，无音频，0.15秒。
【子格2】中景+斜45度：起始姿态；{shot['ambience_sfx 环境底音']}
【子格3】特写+侧面：承接动作下一阶段，聚焦手部/道具/眼神；{shot['prop_sfx 道具音']}
【子格4】近景+过肩：动作后果或反应；{shot['action_sfx 动作音']}
【子格5】全景+斜45度：展示空间结果，左右关系不变。
【子格6】中近景+侧前方：收束姿态，为下一镜留衔接。"""
