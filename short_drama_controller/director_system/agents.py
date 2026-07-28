from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AgentRole(str, Enum):
    DIRECTOR = "director"
    WRITER = "writer"
    ASSET = "asset"
    STORYBOARD = "storyboard"
    PRODUCTION = "production"
    REVIEWER = "reviewer"


@dataclass(frozen=True)
class AgentSpec:
    role: AgentRole
    objective: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    can_block: bool = False


def default_agent_team() -> tuple[AgentSpec, ...]:
    return (
        AgentSpec(
            AgentRole.DIRECTOR,
            "统筹叙事、视觉、节奏和生产决策",
            ("source", "constraints"),
            ("director_brief", "approval_rules"),
            True,
        ),
        AgentSpec(
            AgentRole.WRITER,
            "把原始内容整理成事件链、节拍和可拍摄剧本",
            ("source", "director_brief"),
            ("story_graph", "script", "beat_map"),
        ),
        AgentSpec(
            AgentRole.ASSET,
            "锁定人物、场景、道具和风格一致性",
            ("script", "story_graph"),
            ("asset_manifest", "asset_prompts"),
        ),
        AgentSpec(
            AgentRole.STORYBOARD,
            "生成镜头、机位、调度、动作和连续性方案",
            ("script", "asset_manifest", "beat_map"),
            ("shot_plan", "storyboard_prompts"),
        ),
        AgentSpec(
            AgentRole.PRODUCTION,
            "生成图片、视频、声音和合成任务图",
            ("shot_plan", "asset_manifest"),
            ("production_tasks", "assembly_plan"),
        ),
        AgentSpec(
            AgentRole.REVIEWER,
            "检查叙事、资产、镜头、媒体和合成质量",
            ("all_artifacts",),
            ("qa_report", "repair_actions"),
            True,
        ),
    )
