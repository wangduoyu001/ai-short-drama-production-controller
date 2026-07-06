from __future__ import annotations

from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_storyboard import ALLOWED_CAMERA


def repair_project(project: Project) -> Project:
    repair_assets(project)
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
        shot.setdefault("motion_path 运动轨迹", "无大位移；只保留起势、特写、结果")
        shot.setdefault("entry_pose 起始姿态", "运动或情绪起点明确")
        shot.setdefault("exit_pose 结束姿态", "运动结果或情绪落点明确")
        shot.setdefault("camera_axis 轴线方向", "A-B连线，摄影机同侧")
        shot.setdefault("fallback_shot 备用镜头", "改为侧脸、背影、手部、道具或反应镜头")
        if shot.get("os_line 画外音") != "无":
            shot["mouth_state 嘴型状态"] = "all_closed 全员闭口"
