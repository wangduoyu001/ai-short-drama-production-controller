from __future__ import annotations

from typing import Any


def validate_source_coverage(project_data: dict[str, Any]) -> list[dict[str, str]]:
    source = project_data.get("source_text 原文", "")
    dialogue_lines = project_data.get("dialogue_lines 对白列表", [])
    issues: list[dict[str, str]] = []

    if not source.strip():
        issues.append(issue("BLOCKER", "source.empty", "source_text 原文为空", "ADD 补充"))
        return issues

    covered_dialogues = 0
    for line in dialogue_lines:
        text = line.get("text 台词", "").strip()
        if text and text in source:
            covered_dialogues += 1
        elif text:
            issues.append(issue("BLOCKER", "source.dialogue_missing", f"对白未能回查原文：{text}", "REWRITE 重写"))

    if dialogue_lines and covered_dialogues < len(dialogue_lines):
        issues.append(issue("BLOCKER", "source.coverage_incomplete", "对白原文覆盖不完整", "REWRITE 重写"))

    if not dialogue_lines and any(mark in source for mark in ["“", "”", '"']):
        issues.append(issue("WARN", "source.dialogue_not_extracted", "原文疑似包含对白但未提取", "REWRITE 重写"))

    return issues


def issue(level: str, code: str, message: str, repair_action: str) -> dict[str, str]:
    return {
        "level 等级": level,
        "code 代码": code,
        "message 信息": message,
        "repair_action 返修动作": repair_action,
    }
