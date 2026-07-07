from __future__ import annotations

from .v02_models import Issue, Project


def validate_mainline_coverage(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    required_project_fields = [
        "chapter_intake 章节解析",
        "story_bible 世界观圣经",
        "character_cards 角色卡",
        "three_view_prompts 三视图提示词",
        "scene_plan 场景计划",
        "asset_lock 资产锁定",
        "event_blocks 事件段落拆分",
    ]
    for field in required_project_fields:
        if not project.data.get(field):
            issues.append(Issue("BLOCKER", "mainline.missing_field", f"缺少导演前置结构：{field}", "REBUILD 重新生成前期导演包"))

    issues += check_story_bible(project)
    issues += check_character_coverage(project)
    issues += check_scene_coverage(project)
    issues += check_prop_coverage(project)
    issues += check_event_coverage(project)
    issues += check_action_coverage(project)
    return issues


def check_story_bible(project: Project) -> list[Issue]:
    bible = project.data.get("story_bible 世界观圣经", {})
    issues = []
    for field in ["power_system 力量规则", "taboo_rules 禁忌规则", "visual_style 视觉风格", "color_palette 色卡"]:
        if not bible.get(field):
            issues.append(Issue("BLOCKER", "mainline.bible_missing", f"世界观圣经缺 {field}", "ADD 补充世界观圣经"))
    return issues


def check_character_coverage(project: Project) -> list[Issue]:
    cards = project.data.get("character_cards 角色卡", [])
    three_views = project.data.get("three_view_prompts 三视图提示词", [])
    shot_text = str(project.shots)
    issues = []
    if not cards:
        return [Issue("BLOCKER", "mainline.characters_missing", "缺角色卡 character_cards", "ADD 补充角色卡")]
    card_ids = {c.get("character_id 角色编号") for c in cards}
    view_ids = {c.get("character_id 角色编号") for c in three_views}
    for cid in card_ids:
        if cid not in view_ids:
            issues.append(Issue("BLOCKER", "mainline.three_view_missing", f"角色 {cid} 缺三视图提示词", "ADD 补充 three_view_prompts"))
        if cid and cid not in shot_text:
            issues.append(Issue("WARN", "mainline.character_not_in_shots", f"角色 {cid} 没进入分镜", "CHECK 人工确认是否为非本段角色"))
    return issues


def check_scene_coverage(project: Project) -> list[Issue]:
    scene_plan = project.data.get("scene_plan 场景计划", [])
    shot_text = str(project.shots)
    issues = []
    if not scene_plan:
        return [Issue("BLOCKER", "mainline.scene_plan_missing", "缺 scene_plan 场景计划", "ADD 补充场景计划")]
    for scene in scene_plan:
        sid = scene.get("scene_id 场景编号")
        if sid and sid not in shot_text:
            issues.append(Issue("WARN", "mainline.scene_not_in_shots", f"场景 {sid} 没进入分镜", "CHECK 人工确认是否为后续场景"))
    if len(project.scenes) <= 1 and source_mentions_multiple_scenes(project.data.get("source_text 原文", "")):
        issues.append(Issue("BLOCKER", "mainline.scene_count_low", "原文疑似多场景，但只生成一个场景", "EXPAND 扩展 scene_plan 和 scenes"))
    return issues


def check_prop_coverage(project: Project) -> list[Issue]:
    locks = project.data.get("asset_lock 资产锁定", {})
    shot_prompt_text = str(project.shots)
    issues = []
    props = [p.get("prop_name 道具名") for p in project.props if p.get("prop_name 道具名")]
    if not locks.get("prop_lock 道具锁定"):
        issues.append(Issue("BLOCKER", "mainline.prop_lock_missing", "asset_lock 缺 prop_lock 道具锁定", "ADD 补充道具锁定"))
    for prop in props:
        if prop and prop not in shot_prompt_text:
            issues.append(Issue("WARN", "mainline.prop_not_in_shots", f"关键道具 {prop} 没进入分镜/提示词", "CHECK 人工确认是否需要本段出现"))
    return issues


def check_event_coverage(project: Project) -> list[Issue]:
    blocks = project.data.get("event_blocks 事件段落拆分", [])
    clip_text = str(project.data.get("clip_plan 片段计划", [])) + str(project.data.get("beat_map 剧情节拍表", []))
    issues = []
    if not blocks:
        return [Issue("BLOCKER", "mainline.event_blocks_missing", "缺 event_blocks 事件段落拆分", "ADD 补充事件段落")]
    for block in blocks:
        core = str(block.get("core_event 核心事件", ""))[:18]
        if core and core not in clip_text:
            issues.append(Issue("WARN", "mainline.event_not_in_clip", f"事件段未明显进入 clip/beat：{block.get('block_id 段落编号')}", "CHECK 人工确认覆盖"))
    return issues


def check_action_coverage(project: Project) -> list[Issue]:
    has_action = any(shot.get("clip_type 片段类型", "").startswith(("fight", "action")) for shot in project.shots)
    table = project.data.get("action_choreography 动作编排表", [])
    if has_action and not table:
        return [Issue("BLOCKER", "mainline.action_choreography_missing", "动作/打戏存在，但缺 action_choreography 动作编排表", "ADD 补充动作编排表")]
    return []


def source_mentions_multiple_scenes(text: str) -> bool:
    markers = ["堂口", "香案", "鸡窝", "院子", "破庙", "客栈", "山路", "树林", "屋内", "门外", "村口"]
    return sum(1 for item in markers if item in text) >= 2
