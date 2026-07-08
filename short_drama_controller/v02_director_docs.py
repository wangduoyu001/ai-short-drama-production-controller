from __future__ import annotations

from pathlib import Path
from typing import Any

from .v02_io import write_text
from .v02_models import Project

DOC_MAP = [
    ("chapter_intake.md", "chapter_intake 章节解析文档", "chapter_intake 章节解析"),
    ("story_events.md", "story_events 事件链文档", "story_events 事件链"),
    ("bible.md", "story_bible 世界观圣经", "story_bible 世界观圣经"),
    ("world_bible.md", "world_bible 世界观文档", "world_bible 世界观"),
    ("style_bible.md", "style_bible 风格圣经文档", "style_bible 风格圣经"),
    ("characters.md", "character_cards 角色卡文档", "character_cards 角色卡"),
    ("three_views.md", "three_view_prompts 三视图提示词文档", "three_view_prompts 三视图提示词"),
    ("style.md", "style_and_palette 风格与色卡文档", "style_bible 风格圣经"),
    ("scene_plan.md", "scene_plan 场景计划文档", "scene_plan 场景计划"),
    ("action.md", "action_choreography 动作编排文档", "action_choreography 动作编排表"),
    ("coverage_qa.md", "coverage_qa 关键实体覆盖QA文档", "coverage_qa 关键实体覆盖QA"),
]


def write_director_docs(project: Project, out_dir: Path) -> None:
    for filename, title, data_key in DOC_MAP:
        write_text(out_dir / filename, render_doc(title, project.data.get(data_key)))


def render_doc(title: str, data: Any) -> str:
    return f"# {title}\n\n" + render_value(data)


def render_value(value: Any, level: int = 0) -> str:
    pad = "  " * level
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}- {key}：")
                lines.append(render_value(item, level + 1))
            else:
                lines.append(f"{pad}- {key}：{item}")
        return "\n".join(lines) if lines else f"{pad}- none 无"
    if isinstance(value, list):
        lines = []
        for idx, item in enumerate(value, 1):
            lines.append(f"{pad}- item_{idx:02d} 条目{idx:02d}：")
            lines.append(render_value(item, level + 1))
        return "\n".join(lines) if lines else f"{pad}- none 无"
    return f"{pad}- {value if value is not None else 'none 无'}"
