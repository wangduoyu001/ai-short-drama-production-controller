from __future__ import annotations

from .v02_models import Project
from .v02_prompts import attach_sound_and_prompts
from .v02_storyboard import (
    ALLOWED_CAMERA,
    BANNED_PLACEHOLDERS,
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
    size_group,
)


def repair_project(project: Project, target_shot_id: str | None = None) -> Project:
    repair_assets(project)
    if target_shot_id and not needs_rebuild_from_beats(project):
        repair_project_level(project)
        repair_shots(project, target_shot_id)
        repair_shot_sizes(project, target_shot_id)
    elif needs_rebuild_from_beats(project):
        build_shots(project)
    else:
        repair_project_level(project)
        repair_shots(project)
        repair_shot_sizes(project)
    attach_sound_and_prompts(project)
    return project


def needs_rebuild_from_beats(project: Project) -> bool:
    if not project.data.get("clip_plan 片段计划"):
        return True
    if not project.data.get("beat_map 剧情节拍表"):
        return True
    if not project.shots:
        return True
    return contains_placeholder(project.data)


def contains_placeholder(data: object) -> bool:
    text = str(data)
    return any(word in text for word in BANNED_PLACEHOLDERS)


def repair_project_level(project: Project) -> None:
    shots = project.shots
    project.data.setdefault("approval_gates 确认闸门", build_approval_gates())
    refresh_director_read(project)
    if shots:
        project.data["storyboard_layout 分镜总览布局"] = choose_storyboard_layout(len(shots))
        project.data["storyboard_grid_ascii 分镜总览简笔图"] = build_storyboard_grid_ascii(shots)
        project.data["dialogue_coverage_ascii 对白覆盖图"] = build_dialogue_coverage_ascii(shots)


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


def repair_shots(project: Project, target_shot_id: str | None = None) -> None:
    default_camera = "fixed_camera 固定机位"
    source_text = project.data.get("source_text 原文", "")
    scene = project.scenes[0] if project.scenes else {"scene_name 场景名": "主场景"}
    focus_character = project.characters[0] if project.characters else {"character_name 角色名": "画面主体"}
    beats = project.data.get("beat_map 剧情节拍表", [])
    clip_plan = {clip.get("clip_id 片段编号"): clip for clip in project.data.get("clip_plan 片段计划", [])}
    for index, shot in enumerate(project.shots, start=1):
        if target_shot_id and shot.get("shot_id 镜头编号") != target_shot_id:
            continue
        beat = find_beat_for_shot(beats, shot, index)
        clip_id = beat.get("clip_id 片段编号", shot.get("clip_id 单段编号", "CLIP001"))
        clip = clip_plan.get(clip_id, {})
        if shot.get("camera_movement 机位运动") not in ALLOWED_CAMERA:
            shot["camera_movement 机位运动"] = default_camera
        purpose = shot.get("shot_purpose 镜头目的", beat.get("shot_hint 镜头建议", "reaction_shot 反应镜头"))
        camera = shot.get("camera_movement 机位运动", default_camera)
        action = beat.get("visible_action 可见动作") or shot.get("action_detail 动作细节") or beat.get("source_quote 原文证据", "角色保持可见动作")[:60]
        dialogue = shot.get("dialogue_line 出口对白", beat.get("dialogue 对白", "无"))
        os_line = shot.get("os_line 画外音", "无")
        evidence = build_source_evidence(source_text, index, action, dialogue, os_line, beat)

        shot.setdefault("beat_id 节拍编号", beat.get("beat_id 节拍编号", f"B{index:03d}"))
        shot.setdefault("source_quote 原文节拍证据", beat.get("source_quote 原文证据", evidence.get("evidence_quote 原文证据句", "")))
        shot.setdefault("clip_id 单段编号", clip_id)
        shot.setdefault("clip_type 片段类型", beat.get("clip_type 片段类型", clip.get("clip_type 片段类型", "establishing_clip 建立空间片段")))
        shot.setdefault("clip_duration_seconds 片段时长秒数", beat.get("clip_duration_seconds 片段时长秒数", str(clip.get("duration_seconds 时长秒数", "10"))))
        shot.setdefault("model_duration_limit 模型时长限制", beat.get("model_duration_limit 模型时长限制", clip.get("model_duration_limit 模型时长限制", "4-15秒")))
        shot.setdefault("shot_density 镜头密度", beat.get("shot_density 镜头密度", clip.get("shot_density 镜头密度", "")))
        shot.setdefault("clip_shot_index 片段内镜头序号", beat.get("clip_shot_index 片段内镜头序号", ""))
        shot.setdefault("director_intent 导演意图", project.data.get("director_read 导演读本", {}).get("director_intent 导演意图", "本镜服务原文节拍的可见变化"))
        shot["action_detail 动作细节"] = action
        shot.setdefault("performance_action 表演动作", action)
        shot.setdefault("this_clip_only 本段只拍", action)
        shot.setdefault("reserved_for_later 后续保留", "后续反转、升级冲突或新场景，不在本镜提前完成")
        shot.setdefault("planned_start_state 计划起始状态", f"承接原文节拍：{beat.get('source_quote 原文证据', '')[:50]}")
        shot.setdefault("planned_end_state 计划结束状态", f"停在情绪变化后：{beat.get('emotion_shift 情绪变化', '')[:50]}")
        shot.setdefault("observed_end_state 实际生成结尾状态", "待用户回填")
        shot.setdefault("allowed_changes 允许变化", "只允许表情、手部小动作、光线轻微变化")
        shot.setdefault("retake_variable 本次返修变量", "none 未返修；返修时一次只改一个变量")
        shot.setdefault("motion_path 运动轨迹", build_movement_arrow(purpose))
        shot.setdefault("entry_pose 起始姿态", shot.get("planned_start_state 计划起始状态"))
        shot.setdefault("exit_pose 结束姿态", shot.get("planned_end_state 计划结束状态"))
        shot.setdefault("camera_axis 轴线方向", "A-B连线，摄影机同侧")
        shot.setdefault("fallback_shot 备用镜头", "改为反应镜头或手部道具特写，保留原文节拍")
        shot.setdefault("aspect_ratio 画幅比例", "16:9 横屏")
        shot.setdefault("character_symbols 人物符号", "A○=主角，B○=对手，P1=关键道具，▣=摄影机")
        shot.setdefault("screen_direction 画面方向", "A在画面左侧，B在画面右侧；A视线->，B视线<-；保持同侧轴线，不跳轴")
        shot.setdefault("layer_depth 前中后景", build_layer_depth(scene))
        shot.setdefault("prop_anchor 道具锚点", build_prop_anchor(project, focus_character, action))
        shot.setdefault("movement_arrow 运动箭头", build_movement_arrow(purpose))
        shot.setdefault("camera_arrow 镜头箭头", build_camera_arrow(camera))
        for key, value in evidence.items():
            shot.setdefault(key, value)
        shot.setdefault("unknown_policy 不确定处理规则", "不确定内容必须标注为导演补足，禁止伪装成原文事实")
        if is_high_risk_purpose(purpose):
            shot["motion_grid_ascii 动作拆解六宫格"] = shot.get("motion_grid_ascii 动作拆解六宫格") or build_motion_grid_ascii(shot)
        else:
            shot.setdefault("motion_grid_ascii 动作拆解六宫格", "")
        if shot.get("os_line 画外音") != "无":
            shot["mouth_state 嘴型状态"] = "all_closed 全员闭口"
        shot["sketch_ascii 简笔手绘图"] = build_sketch(shot)


def find_beat_for_shot(beats: list[dict], shot: dict, index: int) -> dict:
    beat_id = shot.get("beat_id 节拍编号")
    for beat in beats:
        if beat.get("beat_id 节拍编号") == beat_id:
            return beat
    return beats[index - 1] if index - 1 < len(beats) else {}


def repair_shot_sizes(project: Project, target_shot_id: str | None = None) -> None:
    alternates = ["全景 WS", "中景 MS", "中近景 MCU", "近景 CU", "特写 ECU"]
    last = ""
    repeat = 0
    for shot in project.shots:
        if target_shot_id and shot.get("shot_id 镜头编号") != target_shot_id:
            group = size_group(shot.get("shot_size 景别", ""))
            last = group
            repeat = 1
            continue
        group = size_group(shot.get("shot_size 景别", ""))
        if group == last:
            repeat += 1
        else:
            repeat = 1
            last = group
        if repeat >= 3 or target_shot_id:
            for candidate in alternates:
                if size_group(candidate) != group:
                    shot["shot_size 景别"] = candidate
                    shot["sketch_ascii 简笔手绘图"] = build_sketch(shot)
                    last = size_group(candidate)
                    repeat = 1
                    break
