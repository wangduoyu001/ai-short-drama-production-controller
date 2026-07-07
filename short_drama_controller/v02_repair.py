from __future__ import annotations

from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_storyboard import (
    ALLOWED_CAMERA,
    build_approval_gates,
    build_camera_arrow,
    build_dialogue_coverage_ascii,
    build_director_read,
    build_layer_depth,
    build_motion_grid_ascii,
    build_movement_arrow,
    build_prop_anchor,
    build_shots,
    build_sketch,
    build_source_evidence,
    build_storyboard_grid_ascii,
    choose_storyboard_layout,
    is_high_risk_purpose,
)


def repair_project(project: Project) -> Project:
    repair_assets(project)
    if not project.data.get("producer_plan 制片执行计划"):
        build_shots(project)
    repair_project_level(project)
    repair_shots(project)
    attach_sound_and_prompts(project)
    return project


def repair_project_level(project: Project) -> None:
    shots = project.shots
    project.data.setdefault("approval_gates 确认闸门", build_approval_gates())
    refresh_director_read(project)
    if shots:
        project.data.setdefault("storyboard_layout 分镜总览布局", choose_storyboard_layout(len(shots)))
        project.data.setdefault("storyboard_grid_ascii 分镜总览简笔图", build_storyboard_grid_ascii(shots))
        project.data.setdefault("dialogue_coverage_ascii 对白覆盖图", build_dialogue_coverage_ascii(shots))


def refresh_director_read(project: Project) -> None:
    current = project.data.get("director_read 导演读本", {})
    required = ["source_basis 原文依据", "conflict_terms 冲突词", "dialogue_basis 对白依据", "scene_function_evidence 场景功能证据", "director_read_confidence 导演读本置信度"]
    if current and all(current.get(field) for field in required):
        return
    if not project.characters or not project.scenes:
        return
    char_a = project.characters[0]
    char_b = project.characters[1] if len(project.characters) > 1 else project.characters[0]
    project.data["director_read 导演读本"] = build_director_read(project.data.get("source_text 原文", ""), project.scenes[0], char_a, char_b)


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
    source_text = project.data.get("source_text 原文", "")
    scene = project.scenes[0] if project.scenes else {"scene_name 场景名": "主场景"}
    focus_character = project.characters[0] if project.characters else {"character_name 角色名": "画面主体"}
    for index, shot in enumerate(project.shots, start=1):
        if shot.get("camera_movement 机位运动") not in ALLOWED_CAMERA:
            shot["camera_movement 机位运动"] = default_camera
        purpose = shot.get("shot_purpose 镜头目的", "")
        camera = shot.get("camera_movement 机位运动", default_camera)
        action = shot.get("action_detail 动作细节", "当前镜头动作")
        dialogue = shot.get("dialogue_line 出口对白", "无")
        os_line = shot.get("os_line 画外音", "无")
        evidence = build_source_evidence(source_text, index, action, dialogue, os_line)

        shot.setdefault("clip_id 单段编号", "CLIP01")
        shot.setdefault("director_intent 导演意图", project.data.get("director_read 导演读本", {}).get("director_intent 导演意图", "让观众明确感到本镜头推动了场景转折"))
        shot.setdefault("this_clip_only 本段只拍", action)
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
        shot.setdefault("aspect_ratio 画幅比例", "16:9 横屏")
        shot.setdefault("character_symbols 人物符号", "A○=主角，B○=对手，P1=关键道具，▣=摄影机")
        shot.setdefault("screen_direction 画面方向", "A在画面左侧，B在画面右侧；A视线->，B视线<-；保持同侧轴线，不跳轴")
        shot.setdefault("layer_depth 前中后景", build_layer_depth(scene))
        shot.setdefault("prop_anchor 道具锚点", build_prop_anchor(project, focus_character, action))
        shot.setdefault("sketch_ascii 简笔手绘图", build_sketch(purpose, shot.get("aspect_ratio 画幅比例", "16:9 横屏")))
        shot.setdefault("movement_arrow 运动箭头", build_movement_arrow(purpose))
        shot.setdefault("camera_arrow 镜头箭头", build_camera_arrow(camera))
        if is_high_risk_purpose(purpose):
            shot.setdefault("motion_grid_ascii 动作拆解六宫格", build_motion_grid_ascii(purpose))
        else:
            shot.setdefault("motion_grid_ascii 动作拆解六宫格", "")
        for key, value in evidence.items():
            shot.setdefault(key, value)
        shot.setdefault("unknown_policy 不确定处理规则", "不确定内容必须标注为导演补足，禁止伪装成原文事实")
        if shot.get("os_line 画外音") != "无":
            shot["mouth_state 嘴型状态"] = "all_closed 全员闭口"
