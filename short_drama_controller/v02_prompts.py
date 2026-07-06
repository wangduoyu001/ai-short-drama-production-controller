from __future__ import annotations

from .v02_models import Project


def attach_sound_and_prompts(project: Project) -> None:
    for shot in project.shots:
        add_sound(shot)
        shot["image_prompt 图片提示词"] = build_image_prompt(project, shot)
        shot["video_prompt 视频提示词"] = build_video_prompt(project, shot)
        shot["grid_prompt 宫格提示词"] = build_grid_prompt(shot) if is_high_risk(shot) else ""


def add_sound(shot: dict) -> None:
    shot["ambience_sfx 环境底音"] = "微风、远处环境空响、稳定场景底噪"
    shot["foley_sfx 拟音"] = "脚步、衣料轻微摩擦"
    shot["prop_sfx 道具音"] = "道具轻触声" if any(x in shot["action_detail 动作细节"] for x in ["剑", "刀", "道具", "手部"]) else "无"
    shot["action_sfx 动作音"] = "短促动作音" if any(x in shot["shot_purpose 镜头目的"] for x in ["insert", "movement", "运动"]) else "无"
    shot["music_note 音乐建议"] = "低频克制氛围，不压对白"
    shot["silence_note 静默说明"] = "对白前后保留短暂停顿"


def build_image_prompt(project: Project, shot: dict) -> str:
    scene = project.get_scene(shot["scene_id 场景编号"]) or {}
    return f"{scene.get('visual_prompt 视觉提示词', '')}，{shot['action_detail 动作细节']}，{shot['shot_size 景别']}，{shot['camera_angle 机位角度']}，无字幕，无水印，人物一致，服装一致"


def build_video_prompt(project: Project, shot: dict) -> str:
    return "\n".join([
        f"shot_id 镜头编号：{shot['shot_id 镜头编号']}",
        f"speaker_mode 发声模式：{shot['speaker_mode 发声模式']}",
        f"speaker_spatial_anchor 说话人空间锚点：{shot['speaker_spatial_anchor 说话人空间锚点']}",
        f"mouth_state 嘴型状态：{shot['mouth_state 嘴型状态']}",
        f"action_description 动作描述：{shot['action_detail 动作细节']}",
        f"motion_path 运动轨迹：{shot['motion_path 运动轨迹']}",
        f"camera_description 机位描述：{shot['shot_size 景别']}，{shot['camera_angle 机位角度']}，{shot['camera_movement 机位运动']}，{shot['camera_axis 轴线方向']}",
        f"dialogue_line 出口对白：{shot['dialogue_line 出口对白']}",
        f"os_line 画外音：{shot['os_line 画外音']}",
        f"ambience_sfx 环境底音：{shot['ambience_sfx 环境底音']}",
        f"foley_sfx 拟音：{shot['foley_sfx 拟音']}",
        f"prop_sfx 道具音：{shot['prop_sfx 道具音']}",
        f"action_sfx 动作音：{shot['action_sfx 动作音']}",
        f"music_note 音乐建议：{shot['music_note 音乐建议']}",
        f"continuity_locks 连续性锁定：{shot['continuity_locks 连续性锁定']}",
        "negative_prompt 负面提示词：禁止换脸，禁止换服装，禁止跳轴，禁止复杂运镜，禁止道具消失，禁止字幕水印",
        f"fallback_prompt 备用提示词：{shot['fallback_shot 备用镜头']}",
    ])


def is_high_risk(shot: dict) -> bool:
    return any(x in shot["shot_purpose 镜头目的"] for x in ["movement", "insert", "运动", "result"])


def build_grid_prompt(shot: dict) -> str:
    return f"""【视频总览】grid_cut_mode 宫格硬切模式；启用 black_frame_anchor 黑屏冻结锚；0.15秒纯黑屏后，子格2-6硬切；世界连续，镜头跳变，同侧轴线。
【子格1-左上(黑屏)】像素级纯黑屏，无画面元素，无音频，0.15秒。
【子格2】中景+斜45度：{shot['action_detail 动作细节']}起势；{shot['ambience_sfx 环境底音']}
【子格3】特写+侧面：承接动作下一阶段，聚焦手部/道具/眼神；{shot['prop_sfx 道具音']}
【子格4】近景+过肩：动作后果或反应；{shot['action_sfx 动作音']}
【子格5】全景+斜45度：展示空间结果，左右关系不变。
【子格6】中近景+侧前方：收束姿态，为下一镜留衔接。"""
