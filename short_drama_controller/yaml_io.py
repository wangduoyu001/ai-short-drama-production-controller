from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def dump_yaml_like(data: dict[str, Any]) -> str:
    return _dump(data, 0).rstrip() + "\n"


def _dump(value: Any, indent: int) -> str:
    space = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.append(_dump(item, indent + 1))
            else:
                lines.append(f"{space}{key}: {format_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{space}-")
                lines.append(_dump(item, indent + 1))
            else:
                lines.append(f"{space}- {format_scalar(item)}")
        return "\n".join(lines)
    return f"{space}{format_scalar(value)}"


def format_scalar(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if any(ch in text for ch in [":", "#", "{", "}", "[", "]", "\n", '"']):
        return json.dumps(text, ensure_ascii=False)
    return text


def write_project_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(dump_yaml_like(data), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
