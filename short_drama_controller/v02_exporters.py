from __future__ import annotations

import csv
from pathlib import Path

from .v02_models import Project
from .v02_io import write_text


def export_project(project: Project, out_dir: Path) -> None:
    export_dir = out_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    write_text(export_dir / "image_prompts.md", render_image_prompts(project))
    write_text(export_dir / "video_prompts.md", render_video_prompts(project))
    write_text(export_dir / "negative_prompts.md", render_negative_prompts(project))
    write_text(export_dir / "fallback_shots.md", render_fallback_shots(project))
    write_text(export_dir / "grid_prompts.md", render_grid_prompts(project))
    write_shot_csv(project, export_dir / "shot_table.csv")
    write_sound_csv(project, export_dir / "sound_table.csv")
    write_producer_csv(project, export_dir / "producer_table.csv")
    write_action_csv(project, export_dir / "action_table.csv")


def render_image_prompts(project: Project) -> str:
    lines = ["# image_prompts 生图提示词导出文档"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot.get('clip_id 单段编号', '')}\n")
        lines.append(shot.get("image_prompt 图片提示词", ""))
    return "\n".join(lines)


def render_video_prompts(project: Project) -> str:
    lines = ["# video_prompts 生视频提示词导出文档"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot.get('clip_id 单段编号', '')} {shot['shot_purpose 镜头目的']}\n")
        lines.append(shot.get("video_prompt 视频提示词", ""))
    return "\n".join(lines)


def render_negative_prompts(project: Project) -> str:
    lines = ["# negative_prompts 负面提示词导出文档"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot.get('clip_id 单段编号', '')}\n")
        lines.append(shot.get("negative_prompt 负面提示词", ""))
    return "\n".join(lines)


def render_fallback_shots(project: Project) -> str:
    lines = ["# fallback_shots 备用镜头导出文档"]
    for shot in project.shots:
        lines.append(f"- {shot.get('shot_id 镜头编号')} / {shot.get('clip_id 单段编号')}：{shot.get('fallback_shot 备用镜头', '')}")
    return "\n".join(lines)


def render_grid_prompts(project: Project) -> str:
    lines = ["# grid_prompts 宫格硬切提示词导出文档"]
    for shot in project.shots:
        grid = shot.get("grid_prompt 宫格提示词")
        if grid:
            lines.append(f"\n## {shot['shot_id 镜头编号']} {shot.get('clip_id 单段编号', '')} {shot['shot_purpose 镜头目的']}\n")
            lines.append(grid)
    return "\n".join(lines)


def write_shot_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "clip_id 单段编号", "clip_type 片段类型", "clip_duration_seconds 片段时长秒数", "model_duration_limit 模型时长限制", "shot_density 镜头密度", "clip_shot_index 片段内镜头序号",
        "beat_id 节拍编号", "shot_purpose 镜头目的", "scene_id 场景编号", "source_quote 原文节拍证据", "focus_character 画面主体", "speaker_mode 发声模式", "dialogue_line 出口对白",
        "shot_size 景别", "camera_movement 机位运动", "screen_direction 画面方向", "movement_arrow 运动箭头", "planned_end_state 计划结束状态", "fallback_shot 备用镜头",
    ]
    write_csv(project, path, fields)


def write_sound_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "clip_id 单段编号", "clip_type 片段类型", "clip_duration_seconds 片段时长秒数", "beat_id 节拍编号", "speaker_mode 发声模式", "mouth_state 嘴型状态",
        "dialogue_line 出口对白", "os_line 画外音", "ambience_sfx 环境底音", "foley_sfx 拟音", "prop_sfx 道具音", "action_sfx 动作音", "music_note 音乐建议",
    ]
    write_csv(project, path, fields)


def write_producer_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "clip_id 单段编号", "clip_type 片段类型", "clip_duration_seconds 片段时长秒数", "beat_id 节拍编号", "this_clip_only 本段只拍", "reserved_for_later 后续保留",
        "planned_start_state 计划起始状态", "planned_end_state 计划结束状态", "observed_end_state 实际生成结尾状态", "continuity_locks 连续性锁定", "allowed_changes 允许变化", "retake_variable 本次返修变量",
    ]
    write_csv(project, path, fields)


def write_action_csv(project: Project, path: Path) -> None:
    fields = ["action_id 动作编号", "related_shot_id 对应镜头编号", "start_state 起点状态", "end_state 终点状态", "attack_line 攻击线", "defense_line 防守线", "contact_point 接触点", "impact_result 结果", "screen_direction 画面方向", "safety_note 安全说明", "fallback_shot 备用镜头"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in project.data.get("action_choreography 动作编排表", []):
            writer.writerow({key: normalize_cell(row.get(key, "")) for key in fields})


def write_csv(project: Project, path: Path, fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for shot in project.shots:
            writer.writerow({key: normalize_cell(shot.get(key, "")) for key in fields})


def normalize_cell(value: object) -> str:
    if isinstance(value, list):
        return " / ".join(str(x) for x in value)
    return str(value)
