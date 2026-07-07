from __future__ import annotations

import re
from typing import Any

from .v02_drama_structure import build_drama_adaptation
from .v02_models import Project


def build_preproduction(project: Project) -> None:
    text = project.data.get("source_text 原文", "")
    project.data["chapter_intake 章节解析"] = build_chapter_intake(text, project)
    project.data["story_bible 世界观圣经"] = build_story_bible(text)
    project.data["character_cards 角色卡"] = build_character_cards(project)
    project.data["three_view_prompts 三视图提示词"] = build_three_view_prompts(project)
    project.data["scene_plan 场景计划"] = build_scene_plan(project)
    project.data["asset_lock 资产锁定"] = build_asset_lock(project)
    project.data["event_blocks 事件段落拆分"] = build_event_blocks(text, project)
    build_drama_adaptation(project)


def build_chapter_intake(text: str, project: Project) -> dict[str, Any]:
    return {
        "source_type 输入类型": "novel_or_script 小说章节/剧本/创意",
        "chapter_summary 章节摘要": compact(text, 180),
        "main_characters 主角": character_names(project)[:1] or ["主角"],
        "supporting_characters 配角": character_names(project)[1:],
        "antagonists_or_entities 反派或异物": [],
        "scenes 场景": scene_names(project),
        "key_props 关键道具": prop_names(project),
        "world_rules 世界规则": ["按原文规则处理；未明确规则时需要人工确认"],
        "event_lines 事件线": split_lines(text),
        "conflict_points 冲突点": infer_conflict_points(text),
        "tone_genre 风格类型": "vertical_microdrama 竖屏短剧",
        "risk_points 风险点": ["人物一致性", "场景跳变", "提示词抽象化", "节奏不够短剧化"],
    }


def build_story_bible(text: str) -> dict[str, str]:
    return {
        "era_setting 时代背景": "由原文判定；未明示时保持模糊年代",
        "geographic_setting 地域环境": "由场景线索决定",
        "folk_system 民俗体系": "按原文设定处理，禁止强行加入没有依据的体系",
        "power_system 力量规则": "人物关系、身份压力、事件目标和世界规则共同推动行动",
        "taboo_rules 禁忌规则": "从原文提取；未明示时标记为需要确认",
        "belief_system 信仰体系": "按原文世界观处理",
        "social_order 社会秩序": "身份、资源、秘密和关系决定人物压迫感",
        "visual_style 视觉风格": "电影写实，低饱和色彩，空间稳定，人物表演优先",
        "color_palette 色卡": "冷灰、暖黄、暗棕、低饱和肤色",
        "camera_mood 镜头气质": "克制、少量推进、动作节点硬切、空间清楚",
        "sound_mood 声音气质": "环境底音稳定，关键处留静默，道具声短促清楚",
    }


def build_character_cards(project: Project) -> list[dict[str, str]]:
    cards = []
    for index, char in enumerate(project.characters, 1):
        cards.append({
            "character_id 角色编号": char.get("character_id 角色编号", f"CHAR_{index:02d}"),
            "character_name 角色名": char.get("character_name 角色名", f"角色{index}"),
            "role_type 角色类型": "protagonist 主角" if index == 1 else "supporting 配角",
            "age_feel 年龄感": "按原文年龄感固定",
            "appearance 外貌特征": char.get("face_shape 脸型", "清晰可识别脸型"),
            "body_shape 体型": "按身份设定体型，保持一致",
            "face_shape 脸型": char.get("face_shape 脸型", "固定脸型"),
            "hair_style 发型": char.get("hair_style 发型", "固定发型"),
            "clothing 服装": char.get("clothing_lock 服装锁定", "固定服装"),
            "identity 身份": char.get("role_function 角色功能", "剧情角色"),
            "personality 性格": "用动作、视线和停顿表现",
            "motivation 动机": "围绕本集核心冲突行动",
            "habitual_actions 动作习惯": "停顿、观察、手部收紧，再行动",
            "speaking_style 说话习惯": "短句、服务冲突",
            "visual_keywords 视觉关键词": char.get("clothing_lock 服装锁定", "固定服装"),
            "forbidden_changes 禁改项": char.get("forbidden_changes 禁止变化", "禁止换脸、换发型、换服装、年龄变化"),
        })
    return cards


def build_three_view_prompts(project: Project) -> list[dict[str, str]]:
    out = []
    for card in build_character_cards(project):
        base = f"{card['character_name 角色名']}，{card['role_type 角色类型']}，{card['appearance 外貌特征']}，{card['clothing 服装']}，电影写实概念设计，灰色棚拍背景，比例一致"
        out.append({
            "character_id 角色编号": card["character_id 角色编号"],
            "character_name 角色名": card["character_name 角色名"],
            "front_view_prompt 正视图提示词": base + "，front view 正视图，全身站姿",
            "side_view_prompt 侧视图提示词": base + "，side view 侧视图，全身站姿",
            "back_view_prompt 背视图提示词": base + "，back view 背视图，全身站姿",
            "closeup_prompt 脸部特写提示词": base + "，face close-up 脸部特写，五官清晰",
            "costume_detail_prompt 服装细节提示词": base + "，costume detail 服装细节，材质清楚",
            "material_prompt 材质提示词": "布料、皮革、旧木、铁器、灰尘、低饱和写实材质",
            "negative_prompt 负面提示词": "禁止换脸，禁止换发型，禁止换服装，禁止现代物件，禁止文字水印，禁止卡通化",
        })
    return out


def build_scene_plan(project: Project) -> list[dict[str, str]]:
    return [{
        "scene_id 场景编号": scene.get("scene_id 场景编号", f"SCENE_{index:02d}"),
        "scene_name 场景名": scene.get("scene_name 场景名", "主场景"),
        "scene_type 场景类型": "dialogue_or_action_space 对话/动作空间",
        "narrative_function 叙事功能": "承载事件、压迫和视觉锚点",
        "location 地点": scene.get("scene_name 场景名", "主场景"),
        "time_of_day 时间": scene.get("time_of_day 时间段", "由原文决定"),
        "weather 天气": "由原文决定",
        "lighting 光线": scene.get("lighting_direction 光线方向", "稳定侧光"),
        "space_layout 空间布局": scene.get("layout_map 空间布局", "前中后景清楚"),
        "fixed_props 固定物件": scene.get("fixed_props 固定物件", "门、桌、墙面或场景固定物"),
        "entry_exit 进出路线": "人物从画面边缘或门口进入，避免空间跳变",
        "visual_mood 视觉氛围": scene.get("visual_prompt 视觉提示词", "低饱和写实空间"),
        "sound_bed 环境底音": "风声、远处空响、脚步或场景固有底噪",
    } for index, scene in enumerate(project.scenes, 1)]


def build_asset_lock(project: Project) -> dict[str, Any]:
    return {
        "character_lock 角色锁定": character_names(project),
        "scene_lock 场景锁定": scene_names(project),
        "prop_lock 道具锁定": prop_names(project),
        "entity_lock 异物锁定": [],
        "color_lock 色卡锁定": project.data.get("story_bible 世界观圣经", {}).get("color_palette 色卡", "低饱和冷灰暖黄"),
        "costume_lock 服装锁定": [c.get("clothing_lock 服装锁定", "固定服装") for c in project.characters],
        "continuity_lock 连续性锁定": "同脸、同发型、同服装、同道具归属、同场景固定物、同色卡",
    }


def build_event_blocks(text: str, project: Project) -> list[dict[str, Any]]:
    blocks = []
    for index, line in enumerate(split_lines(text), 1):
        blocks.append({
            "block_id 段落编号": f"BLOCK_{index:02d}",
            "block_name 段落名": "opening_setup 开场设定" if index == 1 else f"event_block_{index:02d} 事件段落{index:02d}",
            "story_function 剧情功能": "建立信息、升级冲突或制造下一段钩子",
            "main_characters 主要人物": character_names(project)[:2],
            "main_scene 主要场景": scene_names(project)[:1] or ["主场景"],
            "key_props 关键道具": prop_names(project)[:2],
            "core_event 核心事件": compact(line, 140),
            "conflict 核心冲突": "关系压力或事件压力",
            "recommended_clip_type 建议片段类型": "dialogue_clip 对白片段",
        })
    return blocks


def build_action_choreography(project: Project) -> None:
    rows = []
    for shot in project.shots:
        if not shot.get("clip_type 片段类型", "").startswith(("fight", "action")):
            continue
        rows.append({
            "action_id 动作编号": f"ACT_{len(rows)+1:03d}",
            "related_shot_id 对应镜头编号": shot.get("shot_id 镜头编号", ""),
            "start_state 起点状态": shot.get("entry_pose 起始姿态", ""),
            "end_state 终点状态": shot.get("exit_pose 结束姿态", ""),
            "attack_line 攻击线": "沿主冲突轴线推进，禁止跳轴",
            "defense_line 防守线": "防守方向与动作方向相反",
            "contact_point 接触点": "优先手部、道具、脚步或身体边缘的单一接触点",
            "impact_result 结果": shot.get("planned_end_state 计划结束状态", "动作结果明确落点"),
            "screen_direction 画面方向": shot.get("screen_direction 画面方向", "保持同侧轴线"),
            "safety_note 安全说明": "只拍一个动作节点，禁止一镜连续复杂动作",
            "fallback_shot 备用镜头": shot.get("fallback_shot 备用镜头", "改手部/道具/反应特写"),
        })
    project.data["action_choreography 动作编排表"] = rows


def split_lines(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"(?<=[。！？!?；;])", " ".join(text.split())) if p.strip()][:12] or ["空输入"]


def compact(text: str, limit: int) -> str:
    return " ".join(str(text).split())[:limit]


def character_names(project: Project) -> list[str]:
    return [c.get("character_name 角色名", "") for c in project.characters if c.get("character_name 角色名")]


def scene_names(project: Project) -> list[str]:
    return [s.get("scene_name 场景名", "") for s in project.scenes if s.get("scene_name 场景名")]


def prop_names(project: Project) -> list[str]:
    return [p.get("prop_name 道具名", "") for p in project.props if p.get("prop_name 道具名")]


def infer_conflict_points(text: str) -> list[str]:
    hits = [word for word in ["求助", "追", "逃", "秘密", "身份", "禁忌", "上门", "守夜"] if word in text]
    return hits or ["核心冲突需要人工确认"]
