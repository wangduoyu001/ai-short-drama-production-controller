from __future__ import annotations

from typing import Any

from .v02_models import Project


def attach_shot_inference(project: Project) -> None:
    shots = project.shots
    for index, shot in enumerate(shots):
        prev_shot = shots[index - 1] if index > 0 else None
        next_shot = shots[index + 1] if index + 1 < len(shots) else None
        inference = build_shot_inference(project, shot, prev_shot, next_shot)
        shot["shot_inference 单镜推理"] = inference
        shot["first_frame_prompt 首帧提示词"] = inference["first_frame_prompt 首帧提示词"]
        shot["end_frame_prompt 尾帧提示词"] = inference["end_frame_prompt 尾帧提示词"]
        shot["video_prompt 视频提示词"] = inference["video_prompt 生视频提示词"]


def build_shot_inference(project: Project, shot: dict[str, Any], prev_shot: dict[str, Any] | None, next_shot: dict[str, Any] | None) -> dict[str, str]:
    scene = shot.get("scene_id 场景编号", "unknown_scene 未知场景")
    characters = normalize_list(shot.get("on_screen_characters 在场人物", []))
    action = shot.get("action_detail 动作细节", "保持当前动作")
    shot_size = shot.get("shot_size 景别", "中景")
    camera = shot.get("camera_movement 机位运动", "稳定镜头")
    source_quote = shot.get("source_quote 原文节拍证据", "")
    dialogue = shot.get("dialogue_line 出口对白", "")
    speaker = shot.get("speaker_mode 发声模式", "")
    mouth = shot.get("mouth_state 嘴型状态", "")
    style = project.data.get("story_bible 世界观圣经", {}).get("visual_style 视觉风格", "电影写实")
    palette = project.data.get("story_bible 世界观圣经", {}).get("color_palette 色卡", "低饱和色彩")

    return {
        "input_context 输入上下文": build_context(prev_shot, next_shot),
        "first_frame_prompt 首帧提示词": join_parts([
            f"场景：{scene}",
            f"人物：{characters or '按当前镜头人物'}",
            f"动作起点：{shot.get('planned_start_state 计划起始状态', action)}",
            f"构图：{shot_size}，{camera}",
            f"风格：{style}",
            f"色卡：{palette}",
            "要求：画面只呈现当前镜头起点，不提前表现后续动作",
        ]),
        "video_prompt 生视频提示词": join_parts([
            f"当前镜头：{shot.get('shot_id 镜头编号', '')}",
            f"原文依据：{source_quote}",
            f"画面动作：{action}",
            f"机位运动：{camera}",
            f"说话状态：{speaker}；嘴型：{mouth}",
            f"出口对白：{dialogue}" if dialogue else "出口对白：无",
            f"结束状态：{shot.get('planned_end_state 计划结束状态', '')}",
            "只生成当前镜头，不借用前后镜头对白，不添加字幕文字",
        ]),
        "end_frame_prompt 尾帧提示词": join_parts([
            f"场景：{scene}",
            f"人物：{characters or '按当前镜头人物'}",
            f"动作落点：{shot.get('planned_end_state 计划结束状态', action)}",
            f"构图：{shot_size}，保持轴线方向：{shot.get('screen_direction 画面方向', '')}",
            "要求：尾帧只锁定当前镜头结果，为下一镜保留衔接空间",
        ]),
        "negative_prompt 负面提示词": shot.get("negative_prompt 负面提示词", ""),
        "fallback_prompt 备用提示词": shot.get("fallback_shot 备用镜头", ""),
    }


def build_context(prev_shot: dict[str, Any] | None, next_shot: dict[str, Any] | None) -> str:
    prev_id = prev_shot.get("shot_id 镜头编号", "none") if prev_shot else "none"
    next_id = next_shot.get("shot_id 镜头编号", "none") if next_shot else "none"
    return f"previous_shot 前镜头={prev_id}; next_shot 后镜头={next_id}"


def normalize_list(value: Any) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value if item)
    return str(value or "")


def join_parts(parts: list[str]) -> str:
    return "；".join(part for part in parts if part)
