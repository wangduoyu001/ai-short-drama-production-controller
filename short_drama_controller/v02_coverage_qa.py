from __future__ import annotations

import re
from typing import Any

from .v02_models import Issue, Project

ROLE_WORDS = ["少年", "少女", "老人", "老头", "妇人", "女子", "男人", "村民", "弟子", "师父", "师兄", "镖头", "长老", "求助人", "黄皮子", "狐仙", "仙家", "妖物", "黑影", "对手", "反派"]
SCENE_WORDS = ["破庙", "堂口", "香案", "鸡窝", "院子", "山路", "客栈", "大殿", "树林", "村口", "祠堂", "坟地", "桥", "河边", "城门", "码头", "街", "巷"]
PROP_WORDS = ["木剑", "短刀", "长剑", "刀", "剑", "枪", "符", "黄纸", "香炉", "供桌", "牌位", "灯笼", "酒碗", "令牌", "信", "木箱", "镖旗", "鸡", "酒杯"]
EVENT_WORDS = ["追", "逃", "攻击", "打", "杀", "砍", "刺", "受伤", "死亡", "死", "妖物", "武器", "求助", "上门", "递", "跪", "抓", "推", "撞", "转身", "拔", "握"]
GENERIC_SCENES = {"简洁对话场景", "主场景", "对话场景"}


def attach_coverage_qa(project: Project) -> None:
    project.data["coverage_qa 关键实体覆盖QA"] = build_coverage_qa(project)


def build_coverage_qa(project: Project) -> dict[str, Any]:
    source = str(project.data.get("source_text 原文", ""))
    expected_characters = detect_terms(source, ROLE_WORDS)
    expected_scenes = detect_terms(source, SCENE_WORDS)
    expected_props = detect_terms(source, PROP_WORDS)
    expected_events = detect_events(source)

    character_names = [str(c.get("character_name 角色名", "")) for c in project.characters]
    scene_names = [str(s.get("scene_name 场景名", "")) for s in project.scenes]
    prop_names = [str(p.get("prop_name 道具名", "")) for p in project.props]
    event_text = " ".join(str(x) for x in project.data.get("story_events 事件链", project.data.get("event_blocks 事件段落拆分", [])))

    checks = [
        check_missing("characters 主要人物", expected_characters, character_names),
        check_missing("scenes 主要场景", expected_scenes, scene_names),
        check_missing("props 关键道具", expected_props, prop_names),
        check_missing("events 核心事件", expected_events, [event_text]),
        check_generic_scene(expected_scenes, scene_names),
        check_multi_character_interaction(source, character_names),
    ]
    blockers = [check for check in checks if check["level 等级"] == "BLOCKER"]
    return {
        "qa_status 质检状态": "BLOCKER" if blockers else "PASS",
        "allow_export 允许导出": not blockers,
        "expected_characters 原文主要人物候选": expected_characters,
        "expected_scenes 原文主要场景候选": expected_scenes,
        "expected_props 原文关键道具候选": expected_props,
        "expected_events 原文核心事件候选": expected_events,
        "checks 检查项": checks,
    }


def validate_coverage_qa(project: Project) -> list[Issue]:
    qa = project.data.get("coverage_qa 关键实体覆盖QA") or build_coverage_qa(project)
    issues: list[Issue] = []
    if qa.get("qa_status 质检状态") == "BLOCKER":
        for check in qa.get("checks 检查项", []):
            if check.get("level 等级") == "BLOCKER":
                issues.append(Issue("BLOCKER", check.get("code 代码", "coverage.blocker"), check.get("message 信息", "关键实体覆盖失败"), check.get("repair_action 返修动作", "REBUILD 重新解析章节")))
    return issues


def detect_terms(source: str, terms: list[str]) -> list[str]:
    found = [term for term in terms if term in source]
    return unique(found)


def detect_events(source: str) -> list[str]:
    found = [term for term in EVENT_WORDS if term in source]
    if not found and len(split_sentences(source)) >= 2:
        found = ["多事件段落"]
    return unique(found)


def check_missing(label: str, expected: list[str], actual: list[str]) -> dict[str, Any]:
    missing = [item for item in expected if not any(item in value or value in item for value in actual if value)]
    return {
        "check 检查": label,
        "level 等级": "BLOCKER" if missing else "PASS",
        "code 代码": f"coverage.{label.split()[0]}.missing",
        "message 信息": f"{label}缺失：{missing}" if missing else f"{label}覆盖通过",
        "missing 缺失": missing,
        "repair_action 返修动作": "REBUILD 重新解析章节并补齐资产库",
    }


def check_generic_scene(expected_scenes: list[str], scene_names: list[str]) -> dict[str, Any]:
    only_generic = bool(scene_names) and all(name in GENERIC_SCENES or "简洁对话" in name for name in scene_names)
    blocker = bool(expected_scenes) and only_generic
    return {
        "check 检查": "generic_scene 泛化场景",
        "level 等级": "BLOCKER" if blocker else "PASS",
        "code 代码": "coverage.scene.generic",
        "message 信息": "原文存在明确场景，但只生成了泛化场景" if blocker else "场景具体性通过",
        "repair_action 返修动作": "REBUILD 提取原文明示场景，禁止只写简洁对话场景",
    }


def check_multi_character_interaction(source: str, character_names: list[str]) -> dict[str, Any]:
    actual_count = len([name for name in character_names if name])
    interaction = source_suggests_multi_character_interaction(source)
    blocker = interaction and actual_count <= 1
    return {
        "check 检查": "multi_character 多人互动",
        "level 等级": "BLOCKER" if blocker else "PASS",
        "code 代码": "coverage.character.only_one",
        "message 信息": "原文明显有多人互动，但只识别 1 个角色" if blocker else "多人互动覆盖通过",
        "repair_action 返修动作": "REBUILD 补齐对话双方和事件参与者",
    }


def source_suggests_multi_character_interaction(source: str) -> bool:
    role_hits = len(detect_terms(source, ROLE_WORDS)) >= 2
    dialogue = bool(re.search(r"[“\"].{1,60}[”\"]", source))
    pronouns = any(word in source for word in ["他们", "二人", "众人", "对方", "他对", "她对"])
    return role_hits or (dialogue and pronouns)


def split_sentences(source: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？!?；;])", " ".join(source.split())) if part.strip()]


def unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
