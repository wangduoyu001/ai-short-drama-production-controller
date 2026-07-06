from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_project(path: Path, data: dict[str, Any]) -> None:
    # JSON is valid YAML 1.2. Fewer dependencies, fewer future headaches.
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_project(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
