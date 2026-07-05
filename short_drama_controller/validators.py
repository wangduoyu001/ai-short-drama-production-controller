from __future__ import annotations

from typing import Any

from .constants import ALLOWED_CAMERA_MOVEMENTS, WEAK_PROMPT_WORDS
from .models import Issue, Project


def validate_project(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(validate_scope(project))
    issues.extend(validate_characters(project))
    issues.extend(validate_scenes(project))
    issues.extend(validate_blocking(project))
    issues.extend(validate_shots(project))
    issues.extend(validate_prompts_text(project))
    return issues


def validate_scope(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    budget = project.data.get("difficulty_budget 难度预算", {})
    if budget.get("difficulty_status 难度状态") == "BLOCKER":
        issues.append(Issue("BLOCKER", "scope.too_large", "difficulty_budget 难度预算超过上限，必须降级。", "DOWNGRADE 降级"))
    return issues


def validate_characters(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    required = ["face_shape 脸型", "hair_style 发型", "clothing_lock 服装锁定", "forbidden_changes 禁止变化"]
    for character in project.characters:
        cid = character.get("character_id 角色编号", "UNKNOWN")
        for field in required:
            if not character.get(field):
                issues.append(Issue("BLOCKER", "character.missing_lock", f"{cid} 缺少 {field}", "ADD 补充"))
    if len(project.characters) > 4:
        issues.append(Issue("BLOCKER", "character.too_many", "character_count 角色数量超过4，必须合并。", "MERGE 合并"))
    return issues


def validate_scenes(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    required = ["lighting_direction 光线方向", "layout_map 空间布局", "fixed_props 固定物件", "forbidden_elements 禁止元素"]
    for scene in project.scenes:
        sid = scene.get("scene_id 场景编号", "UNKNOWN")
        for field in required:
            if not scene.get(field):
                issues.append(Issue("BLOCKER", "scene.missing_lock", f"{sid} 缺少 {field}", "ADD 补充"))
    if len(project.scenes) > 2:
        issues.append(Issue("WARN", "scene.too_many", "main_scene_count 主场景数量偏多，建议合并。", "MERGE 合并"))
    return issues


def validate_blocking(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    blocking = project.data.get("blocking_plan 人物调度计划", {})
    for field in ["axis_line 轴线", "safe_camera_zone 安全机位区", "eyeline_a A视线方向", "eyeline_b B视线方向"]:
        if not blocking.get(field):
            issues.append(Issue("BLOCKER", "blocking.missing_axis", f"blocking_plan 人物调度计划缺少 {field}", "ADD 补充"))
    return issues


def validate_shots(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    shots = project.shots
    if not 8 <= len(shots) <= 12:
        issues.append(Issue("WARN", "shot.count", f"shot_count 镜头数量为 {len(shots)}，建议控制在8-12。", "SPLIT/MERGE 拆分或合并"))
    required = ["motion_path 运动轨迹", "camera_movement 机位运动", "fallback_shot 备用镜头", "continuity_locks 连续性锁定", "action_detail 动作细节"]
    purposes = {s.get("shot_purpose 镜头目的", "") for s in shots}
    if not any("master" in p or "主镜头" in p for p in purposes):
        issues.append(Issue("BLOCKER", "shot.no_master", "缺少 master_shot 主镜头。", "ADD 补充"))
    if not any("insert" in p or "插入" in p for p in purposes):
        issues.append(Issue("WARN", "shot.no_insert", "缺少 insert_shot 插入镜头。", "ADD 补充"))
    if not any("reaction" in p or "反应" in p for p in purposes):
        issues.append(Issue("WARN", "shot.no_reaction", "缺少 reaction_shot 反应镜头。", "ADD 补充"))
    for shot in shots:
        sid = shot.get("shot_id 镜头编号", "UNKNOWN")
        for field in required:
            if not shot.get(field):
                issues.append(Issue("BLOCKER", "shot.missing_field", f"{sid} 缺少 {field}", "ADD 补充"))
        camera_move = shot.get("camera_movement 机位运动")
        if camera_move and camera_move not in ALLOWED_CAMERA_MOVEMENTS:
            issues.append(Issue("BLOCKER", "camera.forbidden", f"{sid} 使用了不允许的机位运动：{camera_move}", "DOWNGRADE 降级"))
        dialogue = shot.get("dialogue_line 对白", "")
        if len(dialogue) > 25:
            issues.append(Issue("WARN", "dialogue.too_long", f"{sid} 对白过长，建议拆成正反打。", "SPLIT 拆分"))
    return issues


def validate_prompts_text(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    text = str(project.data)
    weak_hits = [w for w in WEAK_PROMPT_WORDS if w in text]
    if weak_hits:
        issues.append(Issue("WARN", "prompt.weak_words", f"发现弱词：{', '.join(weak_hits)}。必须补具体镜头语言。", "REWRITE 重写"))
    return issues


def qa_summary(issues: list[Issue]) -> dict[str, Any]:
    blockers = [i for i in issues if i.level == "BLOCKER"]
    warnings = [i for i in issues if i.level == "WARN"]
    status = "BLOCKER" if blockers else "WARN" if warnings else "PASS"
    return {"qa_status 质检状态": status, "blocker_count 阻塞问题数": len(blockers), "warning_count 警告问题数": len(warnings), "issues 问题列表": [{"level 等级": i.level, "code 代码": i.code, "message 信息": i.message, "repair_action 返修动作": i.repair_action} for i in issues]}
