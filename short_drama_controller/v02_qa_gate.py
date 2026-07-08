from __future__ import annotations

from pathlib import Path
from typing import Any

from .v02_coverage_qa import validate_coverage_qa
from .v02_io import write_text
from .v02_models import Issue, Project
from .v02_quality import summary, validate

REQUIRED_PREPRODUCTION_FIELDS = [
    "chapter_intake 章节解析",
    "story_events 事件链",
    "characters 角色列表",
    "scenes 场景列表",
    "props 道具列表",
    "world_bible 世界观",
    "style_bible 风格圣经",
    "asset_lock 资产锁定",
    "beat_map 剧情节拍表",
    "shot_plan 分镜计划",
]
REQUIRED_SHOT_FIELDS = [
    "source_quote 原文证据",
    "event_id 事件编号",
    "beat_id 节拍编号",
    "scene_id 场景编号",
    "character_id 角色编号",
    "prop_id 道具编号",
]
ACTION_WORDS = ["追", "攻击", "打击", "打", "杀", "砍", "刺", "妖物", "武器", "受伤", "死亡", "死", "逃", "抓", "推", "撞", "拔", "握", "刀", "剑", "枪"]
ACTION_FIELDS = ["start_state 起始姿态", "end_state 结束姿态", "attack_line 攻击线", "movement_line 移动线", "contact_point 接触点", "speed 速度", "result 结果", "risk_level 风险等级", "backup_shot 备用镜头", "grid_cut_prompt 宫格硬切提示词"]


def evaluate(project: Project) -> dict[str, Any]:
    issues = validate(project)
    issues += validate_required_structures(project)
    issues += validate_shot_contracts(project)
    issues += validate_coverage_qa(project)
    issues += validate_action_choreography(project)
    issues += validate_batch_inference(project)
    qa = summary(issues)
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


def validate_required_structures(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    for field in REQUIRED_PREPRODUCTION_FIELDS:
        if not project.data.get(field):
            issues.append(Issue("BLOCKER", "project.required_structure_missing", f"缺少主流程结构：{field}", "REBUILD 重新运行 full_cli init/repair"))
    return issues


def validate_shot_contracts(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    for shot in project.shots:
        sid = shot.get("shot_id 镜头编号", "UNKNOWN")
        for field in REQUIRED_SHOT_FIELDS:
            if not shot.get(field):
                issues.append(Issue("BLOCKER", "shot.required_binding_missing", f"{sid} 缺少绑定字段：{field}", "REBUILD 先生成事件链、beat_map、shot_plan 再生成分镜"))
    return issues


def validate_action_choreography(project: Project) -> list[Issue]:
    source = project.data.get("source_text 原文", "")
    needs_action = any(word in source for word in ACTION_WORDS)
    rows = project.data.get("action_choreography 动作编排表", [])
    if needs_action and not rows:
        return [Issue("BLOCKER", "action_choreography.missing", "原文包含追逐/攻击/妖物/武器/受伤/死亡等动作风险，但缺 action_choreography 动作编排表", "ADD 补充动作编排表")]
    issues: list[Issue] = []
    for row in rows:
        rid = row.get("action_id 动作编号", "UNKNOWN")
        for field in ACTION_FIELDS:
            if not row.get(field):
                issues.append(Issue("BLOCKER", "action_choreography.field_missing", f"{rid} 缺 {field}", "ADD 补齐动作编排字段"))
    return issues


def validate_batch_inference(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    for batch in project.data.get("batch_inference 批量推理", []):
        bid = batch.get("batch_id 批次编号", "UNKNOWN")
        records = batch.get("records 批量记录", [])
        if batch.get("record_count 记录数") != len(records):
            issues.append(Issue("BLOCKER", "batch_inference.count_mismatch", f"{bid} record_count 与 records 数量不一致", "REBUILD 重建批量推理"))
        check = batch.get("batch_self_check 批量自检", {})
        if check and check.get("count_match 数量匹配") is False:
            issues.append(Issue("BLOCKER", "batch_inference.self_check_failed", f"{bid} 批量自检失败", "REBUILD 重建批量推理"))
    return issues


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
