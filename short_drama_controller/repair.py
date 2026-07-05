from __future__ import annotations

from .constants import ALLOWED_CAMERA_MOVEMENTS
from .models import Project


def repair_project(project: Project) -> Project:
    repair_scope(project)
    repair_characters(project)
    repair_scenes(project)
    repair_blocking(project)
    repair_shots(project)
    return project


def repair_scope(project: Project) -> None:
    project.data["production_mode 制作模式"] = "fast_demo 快速样片模式"
    project.data["scope_gate 范围闸门"]["reduced_scope 压缩后范围"] = "60-90秒，8-12镜，2-3人，1个主场景。"


def repair_characters(project: Project) -> None:
    for c in project.characters:
        c.setdefault("face_shape 脸型", "清晰可识别脸型")
        c.setdefault("hair_style 发型", "固定发型")
        c.setdefault("clothing_lock 服装锁定", "固定服装，低饱和颜色")
        c.setdefault("forbidden_changes 禁止变化", "禁止换脸、禁止换发型、禁止换服装、禁止年龄变化")
        c.setdefault("behavior_anchor 行为锚点", "固定小动作")
        cid = c.get("character_id 角色编号", "CHAR_X")
        c.setdefault("reference_image_lock 参考图锁", {"face_reference 脸部参考": f"{cid}_face_ref", "outfit_reference 服装参考": f"{cid}_outfit_ref", "fullbody_reference 全身参考": f"{cid}_fullbody_ref"})


def repair_scenes(project: Project) -> None:
    for s in project.scenes:
        s.setdefault("lighting_direction 光线方向", "稳定侧光")
        s.setdefault("layout_map 空间布局", "A在左，B在右，背景固定")
        s.setdefault("fixed_props 固定物件", "门、桌、墙面")
        s.setdefault("forbidden_elements 禁止元素", "禁止现代错物，禁止空间漂移，禁止风格突变")


def repair_blocking(project: Project) -> None:
    project.data["blocking_plan 人物调度计划"] = {"blocking_id 调度编号": "BLOCK_01", "scene_id 场景编号": "SCENE_01", "character_a_position A角色位置": "画面左侧，面向右", "character_b_position B角色位置": "画面右侧，面向左", "axis_line 轴线": "CHAR_A 与 CHAR_B 的连线", "safe_camera_zone 安全机位区": "摄影机始终在轴线同一侧，禁止越轴", "eyeline_a A视线方向": "A看向画面右侧", "eyeline_b B视线方向": "B看向画面左侧", "distance_between_characters 角色距离": "约三步", "power_relation 权力关系": "B压迫A，A逐渐反击", "blocking_change 调度变化": "A前进一步，B保持不动"}


def repair_shots(project: Project) -> None:
    for shot in project.shots:
        if shot.get("camera_movement 机位运动") not in ALLOWED_CAMERA_MOVEMENTS:
            shot["camera_movement 机位运动"] = "fixed_camera 固定机位"
        shot.setdefault("motion_path 运动轨迹", "固定站位；如有移动，只允许前进一步或后退半步")
        shot.setdefault("fallback_shot 备用镜头", "改为道具特写或反应镜头")
        shot.setdefault("continuity_locks 连续性锁定", "同脸、同发型、同服装、同道具、同站位逻辑")
        if len(shot.get("dialogue_line 对白", "")) > 25:
            shot["dialogue_line 对白"] = shot["dialogue_line 对白"][:24]
