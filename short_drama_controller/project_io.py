from __future__ import annotations

import re
from pathlib import Path

from .core import create_project_from_input
from .models import Project


def load_project(project_dir: Path) -> Project:
    yaml_path = project_dir / "project.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Missing project.yaml: {yaml_path}")
    text = yaml_path.read_text(encoding="utf-8")
    script_text = (project_dir / "script.md").read_text(encoding="utf-8") if (project_dir / "script.md").exists() else text
    return create_project_from_input(script_text, title=extract_title(text) or project_dir.name)


def extract_title(text: str) -> str | None:
    match = re.search(r"project_name 项目名:\s*(.+)", text)
    if match:
        return match.group(1).strip().strip('"')
    return None
