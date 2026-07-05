from __future__ import annotations

import csv
from pathlib import Path

from .models import Project
from .yaml_io import write_text


def export_project(project: Project, project_dir: Path) -> None:
    exports = project_dir / "exports"
    exports.mkdir(exist_ok=True)
    write_text(exports / "libtv_prompts.md", render_platform_prompts(project, "LibTV"))
    write_text(exports / "lovart_prompts.md", render_platform_prompts(project, "Lovart"))
    write_shot_table(project, exports / "shot_table.csv")
    write_edit_list(project, exports / "edit_list.csv")


def render_platform_prompts(project: Project, platform: str) -> str:
    lines = [f"# {platform.lower()}_prompts {platform}提示词\n"]
    for shot in project.shots:
        chars = ", ".join(shot["character_ids 角色编号"])
        lines.append(f"""
## {shot['shot_id 镜头编号']} {shot['shot_purpose 镜头目的']}

platform 目标平台：{platform}
character_reference 角色参考：{chars}
scene_reference 场景参考：{shot['scene_id 场景编号']}
action_description 动作描述：{shot['action_detail 动作细节']}
motion_path 运动轨迹：{shot['motion_path 运动轨迹']}
camera_description 机位描述：{shot['shot_size 景别']}，{shot['camera_angle 机位角度']}，{shot['camera_height 机位高度']}，{shot['camera_movement 机位运动']}
continuity_locks 连续性锁定：{shot['continuity_locks 连续性锁定']}
negative_prompt 负面提示词：禁止换脸，禁止换服装，禁止发型变化，禁止跳轴，禁止复杂运镜，禁止道具消失，禁止现代错误物件
fallback_prompt 备用提示词：{shot['fallback_shot 备用镜头']}
""")
    return "\n".join(lines)


def write_shot_table(project: Project, path: Path) -> None:
    fields = ["shot_id 镜头编号", "shot_purpose 镜头目的", "duration_seconds 时长秒数", "scene_id 场景编号", "character_ids 角色编号", "shot_size 景别", "camera_movement 机位运动", "action_detail 动作细节", "dialogue_line 对白", "fallback_shot 备用镜头"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for shot in project.shots:
            row = {k: shot.get(k, "") for k in fields}
            if isinstance(row["character_ids 角色编号"], list):
                row["character_ids 角色编号"] = " / ".join(row["character_ids 角色编号"])
            writer.writerow(row)


def write_edit_list(project: Project, path: Path) -> None:
    fields = ["shot_id 镜头编号", "duration_seconds 时长秒数", "sound_design 声音设计", "dialogue_line 对白", "cut_reason 剪辑原因"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for shot in project.shots:
            writer.writerow({"shot_id 镜头编号": shot.get("shot_id 镜头编号", ""), "duration_seconds 时长秒数": shot.get("duration_seconds 时长秒数", ""), "sound_design 声音设计": shot.get("sound_design 声音设计", ""), "dialogue_line 对白": shot.get("dialogue_line 对白", ""), "cut_reason 剪辑原因": "按视线、反应或动作结果剪切"})
