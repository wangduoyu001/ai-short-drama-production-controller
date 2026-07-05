from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Issue:
    level: str
    code: str
    message: str
    repair_action: str = "FLAG 标记"


@dataclass
class Project:
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def shots(self) -> list[dict[str, Any]]:
        return self.data.setdefault("shots 分镜列表", [])

    @property
    def characters(self) -> list[dict[str, Any]]:
        return self.data.setdefault("characters 角色列表", [])

    @property
    def scenes(self) -> list[dict[str, Any]]:
        return self.data.setdefault("scenes 场景列表", [])

    @property
    def props(self) -> list[dict[str, Any]]:
        return self.data.setdefault("props 道具列表", [])
