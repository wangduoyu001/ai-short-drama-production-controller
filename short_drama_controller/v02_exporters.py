from __future__ import annotations

import csv
from pathlib import Path

from .v02_models import Project
from .v02_io import write_text


def export_project(project: Project, out_dir: Path) -> None:
    export_dir = out_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    write_text(export_dir / "v02_video_prompts.md", render_video_prompts(project))
    write_text(export_dir / "v02_grid_prompts.md", render_grid_prompts(project))
    write_shot_csv(project, export_dir / "v02_shot_table.csv")
    write_sound_csv(project, export_dir / "v02_sound_table.csv")


def render_video_prompts(project: Project) -> str:
    lines = ["# v02_video_prompts 视频提示词"]
    for shot in project.shots:
        lines.append(f"\n## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}\n")
        lines.append(shot.get("video_prompt 视频提示词", ""))
    return "\n".join(lines)


def render_grid_prompts(project: Project) -> str:
    lines = ["# v02_grid_prompts 宫格硬切提示词"]
    for shot in project.shots:
        grid = shot.get("grid_prompt 宫格提示词")
        if grid:
            lines.append(f"\n## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}\n")
            lines.append(grid)
    return "\n".join(lines)


def write_shot_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "shot_purpose 镜头目的", "scene_id 场景编号",
        "focus_character 画面主体", "speaker_mode 发声模式", "dialogue_line 出口对白",
        "os_line 画外音", "shot_size 景别", "camera_movement 机位运动",
        "motion_path 运动轨迹", "fallback_shot 备用镜头",
    ]
    write_csv(project, path, fields)


def write_sound_csv(project: Project, path: Path) -> None:
    fields = [
        "shot_id 镜头编号", "ambience_sfx 环境底音", "foley_sfx 拟音",
        "prop_sfx 道具音", "action_sfx 动作音", "music_note 音乐建议", "silence_note 静默说明",
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
