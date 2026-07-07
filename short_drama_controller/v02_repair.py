from __future__ import annotations

from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_storyboard import ALLOWED_CAMERA, build_shots


def repair_project(project: Project) -> Project:
    repair_assets(project)
    if not project.data.get("director_read 导演读本") or not project.data.get("producer_plan 制片执行计划"):
        build_shots(project)
    repair_shots(project)
    attach_sound_and_prompts(project)
    return project


def repair_assets(project: Project) -> None:
    for character in project.characters:
        character.setdefault("face_shape 脸型", "清晰可识别脸型")
        character.setdefault("hair_style 发型", "固定黑色发型")
        character.setdefault("clothing_lock 服装锁定", "固定低饱和服装")
        character.setdefault("forbidden_changes 禁止变化", "禁止换脸、换发型、换服装、年龄变化")
        character.setdefault("spatial_anchor 空间锚点", "画面左侧")
    for scene in project.scenes:
        scene.setdefault("lighting_direction 光线方向", "稳定侧光")
        scene.setdefault("layout_map 空间布局", "A左B右，背景固定")
        scene.setdefault("fixed_props 固定物件", "门、墙面、地面")


def repair_shots(project: Project) -> None:
    default_camera = "fixed_camera 固定机位"
    for shot in project.shots:
        if shot.get("camera_movement 机位运动") not in ALLOWED_CAMERA:
            shot["camera_movement 机位运动"] = default_camera
        shot.setdefault("clip_id 单段编号", "CLIP01")
        shot.setdefault("director_intent 导演意图", project.data.get("director_read 导演读本", {}).get("director_intent 导演意图", "让观众明确感到本镜头推动了场景转折"))
        shot.setdefault("this_clip_only 本段只拍", shot.get("action_detail 动作细节", "当前镜头动作"))
        shot.setdefault("reserved_for_later 后续保留", "后续反转、升级冲突或新场景，不在本镜提前完成")
        shot.setdefault("planned_start_state 计划起始状态", "运动或情绪起点明确")
        shot.setdefault("planned_end_state 计划结束状态", "运动结果或情绪落点明确")
        shot.setdefault("observed_end_state 实际生成结尾状态", "待用户回填")
        shot.setdefault("allowed_changes 允许变化", "只允许表情、手部小动作、光线轻微变化")
        shot.setdefault("retake_variable 本次返修变量", "none 未返修；返修时一次只改一个变量")
        shot.setdefault("motion_path 运动轨迹", "无大位移；只保留起势、特写、结果")
        shot.setdefault("entry_pose 起始姿态", "运动或情绪起点明确")
        shot.setdefault("exit_pose 结束姿态", "运动结果或情绪落点明确")
        shot.setdefault("camera_axis 轴线方向", "A-B连线，摄影机同侧")
        shot.setdefault("fallback_shot 备用镜头", "改为侧脸、背影、手部、道具或反应镜头")
        if shot.get("os_line 画外音") != "无":
            shot["mouth_state 嘴型状态"] = "all_closed 全员闭口"
