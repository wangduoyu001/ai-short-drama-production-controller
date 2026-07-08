from __future__ import annotations

from pathlib import Path
from typing import Any

from .v02_io import write_text
from .v02_models import Project
from .v02_quality import summary, validate


def evaluate(project: Project) -> dict[str, Any]:
    qa = summary(validate(project))
    qa["allow_export 允许导出"] = is_export_allowed(qa)
    return qa


def is_export_allowed(qa: dict[str, Any]) -> bool:
    return qa.get("qa_status 质检状态") != "BLOCKER" and int(qa.get("blocker_count 阻塞问题数", 0)) == 0


def run_qa_gate(project: Project, project_dir: Path, *, block_on_blocker: bool = True) -> dict[str, Any]:
    qa = evaluate(project)
    write_text(project_dir / "qa.md", render_qa(qa))
    if block_on_blocker and not is_export_allowed(qa):
        raise SystemExit("QA BLOCKER: export denied. See qa.md for required fixes.")
    return qa


def render_qa(qa: dict[str, Any]) -> str:
    lines = [
        "# qa_report 质检返修文档",
        f"qa_status 质检状态：{qa['qa_status 质检状态']}",
        f"allow_export 允许导出：{'YES' if is_export_allowed(qa) else 'NO'}",
        f"blocker_count 阻塞问题数：{qa['blocker_count 阻塞问题数']}",
        f"warning_count 警告问题数：{qa['warning_count 警告问题数']}",
    ]
    for issue in qa["issues 问题列表"]:
        lines.append(f"- {issue}")
    lines.append("\n## export_rule 导出规则")
    lines.append("export 前必须自动运行 QA；只要存在 BLOCKER，禁止导出 exports 物料。")
    lines.append("\n## overwrite_rule 覆盖规则")
    lines.append("返修后直接覆盖旧文档，禁止生成 qa_final.md / prompts_v2.md / storyboard_fixed.md。")
    return "\n".join(lines)
