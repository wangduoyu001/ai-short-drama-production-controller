from __future__ import annotations

import csv
from pathlib import Path

from .v02_models import Project
from .v02_io import write_text


def export_project(project: Project, out_dir: Path) -> None:
    export_dir = out_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    write_text(export_dir / "video_prompts.md", render_video_prompts(project))
    write_text(export_dir / "grid_prompts.md", render_grid_prompts(project))
    write_shot_csv(project, export_dir / "shot_table.csv")
    write_sound_csv(project, export_dir / "sound_table.csv")
    write_producer_csv(project, export_dir / "producer_table.csv")


def render_video_prompts(project: Project) -> str:
    lines = ["# video_prompts 视频提示词导出文档"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}\n")
        lines.append(shot.get("video_prompt 视频提示词", ""))
    return "\n".join(lines)


def render_grid_prompts(project: Project) -> str:
    lines = ["# grid_prompts 宫格硬切提示词导出文档"]
    for shot in project.shots:
        grid = shot.get("grid_prompt 宫格提示词")
        if grid:
            lines.append(f"\n## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}\n")
            lines.append(grid)
    return "\n".join(lines)


def write_shot_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "beat_id 节拍编号", "clip_id 单段编号", "shot_purpose 镜头目的", "scene_id 场景编号",
        "source_quote 原文节拍证据", "source_text_ref 原文引用位置", "evidence_quote 原文证据句", "invented_flag 是否AI补充", "source_confidence 原文置信度",
        "director_intent 导演意图", "this_clip_only 本段只拍", "reserved_for_later 后续保留",
        "focus_character 画面主体", "speaker_mode 发声模式", "dialogue_line 出口对白",
        "os_line 画外音", "shot_size 景别", "aspect_ratio 画幅比例", "camera_movement 机位运动",
        "screen_direction 画面方向", "movement_arrow 运动箭头", "camera_arrow 镜头箭头",
        "layer_depth 前中后景", "prop_anchor 道具锚点",
        "motion_path 运动轨迹", "planned_end_state 计划结束状态", "observed_end_state 实际生成结尾状态",
        "fallback_shot 备用镜头",
    ]
    write_csv(project, path, fields)


def write_sound_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "beat_id 节拍编号", "clip_id 单段编号", "speaker_mode 发声模式", "mouth_state 嘴型状态",
        "dialogue_line 出口对白", "os_line 画外音", "ambience_sfx 环境底音", "foley_sfx 拟音",
        "prop_sfx 道具音", "action_sfx 动作音", "music_note 音乐建议", "silence_note 静默说明",
    ]
    write_csv(project, path, fields)


def write_producer_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "beat_id 节拍编号", "clip_id 单段编号", "this_clip_only 本段只拍", "reserved_for_later 后续保留",
        "planned_start_state 计划起始状态", "planned_end_state 计划结束状态", "observed_end_state 实际生成结尾状态",
        "continuity_locks 连续性锁定", "allowed_changes 允许变化", "retake_variable 本次返修变量",
        "adaptation_note 改编说明", "unknown_policy 不确定处理规则",
    ]
    write_csv(project, path, fields)


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
