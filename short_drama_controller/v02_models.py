from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal["PASS", "WARN", "BLOCKER"]


@dataclass(frozen=True)
class Issue:
    level: Status
    code: str
    message: str
    repair_action: str = "FLAG 标记"


@dataclass
class Project:
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def characters(self) -> list[dict[str, Any]]:
        return self.data.setdefault("characters 角色列表", [])

    @property
    def scenes(self) -> list[dict[str, Any]]:
        return self.data.setdefault("scenes 场景列表", [])

    @property
    def props(self) -> list[dict[str, Any]]:
        return self.data.setdefault("props 道具列表", [])

    @property
    def shots(self) -> list[dict[str, Any]]:
        return self.data.setdefault("shots 分镜列表", [])

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        return next((s for s in self.scenes if s.get("scene_id 场景编号") == scene_id), None)

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        return next((c for c in self.characters if c.get("character_id 角色编号") == character_id), None)
