from __future__ import annotations

import re
from typing import Any

from .v02_models import Project

ROLE_KEYWORDS = {
    "protagonist 主角": ["主角", "男主", "女主", "少年", "姑娘", "镖人", "师傅", "我"],
    "supporting 配角": ["配角", "村民", "徒弟", "师兄", "师弟", "老人", "妇人", "孩子", "客户", "香客"],
    "antagonist 反派": ["反派", "仇人", "恶人", "镖头", "杀手", "官差", "土匪"],
    "creature 异物": ["黄皮子", "狐仙", "蛇", "常仙", "灰仙", "白仙", "怪物", "异物", "妖", "鬼"],
    "immortal_or_spirit 仙家/灵体": ["仙家", "狐仙", "黄仙", "常仙", "清风", "鬼魂", "灵体", "堂口"],
}

SCENE_KEYWORDS = ["堂口", "香案", "破庙", "鸡窝", "院子", "村口", "山路", "树林", "客栈", "镖局", "街巷", "城门", "屋内", "门外", "坟地", "河边"]
PROP_KEYWORDS = ["香", "香炉", "供桌", "牌位", "鸡", "鸡窝", "黄纸", "符", "刀", "剑", "枪", "令牌", "信", "灯笼", "酒碗", "木箱", "镖旗"]
WORLD_RULE_KEYWORDS = ["禁忌", "不能", "不许", "犯忌", "上香", "供奉", "出马", "堂口", "仙家", "报应", "附身", "看事", "规矩"]
ACTION_WORDS = ["打", "杀", "砍", "刺", "扑", "撞", "摔", "追", "逃", "拔", "挡", "格", "推", "踢", "咬", "冲"]


def build_preproduction(project: Project) -> None:
    text = project.data.get("source_text 原文", "")
    project.data["chapter_intake 章节解析"] = build_chapter_intake(text, project)
    project.data["story_bible 世界观圣经"] = build_story_bible(text)
    project.data["character_cards 角色卡"] = build_character_cards(project)
    project.data["three_view_prompts 三视图提示词"] = build_three_view_prompts(project)
    project.data["scene_plan 场景计划"] = build_scene_plan(project)
    project.data["asset_lock 资产锁定"] = build_asset_lock(project)
    project.data["event_blocks 事件段落拆分"] = build_event_blocks(text, project)


def build_chapter_intake(text: str, project: Project) -> dict[str, Any]:
    characters = [c.get("character_name 角色名", "") for c in project.characters]
    props = [p.get("prop_name 道具名", "") for p in project.props]
    scenes = [s.get("scene_name 场景名", "") for s in project.scenes]
    return {
        "source_type 输入类型": infer_source_type(text),
        "chapter_summary 章节摘要": summarize_text(text),
        "main_characters 主角": choose_main_characters(project),
        "supporting_characters 配角": [c for c in characters[1:] if c],
        "antagonists_or_entities 反派或异物": detect_terms(text, ROLE_KEYWORDS["antagonist 反派"] + ROLE_KEYWORDS["creature 异物"] + ROLE_KEYWORDS["immortal_or_spirit 仙家/灵体"]),
        "scenes 场景": scenes or detect_terms(text, SCENE_KEYWORDS),
        "key_props 关键道具": props or detect_terms(text, PROP_KEYWORDS),
        "world_rules 世界规则": detect_terms(text, WORLD_RULE_KEYWORDS) or ["未明确写出规则，需人工确认世界观限制"],
        "event_lines 事件线": split_event_lines(text),
        "conflict_points 冲突点": detect_conflicts(text),
        "tone_genre 风格类型": infer_genre(text),
        "risk_points 风险点": infer_risk_points(text),
    }


def build_story_bible(text: str) -> dict[str, Any]:
    folk = any(word in text for word in ["出马", "堂口", "仙家", "黄皮子", "狐仙", "上香"])
    wuxia = any(word in text for word in ["镖", "刀", "剑", "江湖", "武林", "掌门"])
    if folk:
        visual = "东北民俗悬疑写实，旧木屋、香火、冷灰夜色、土黄灯光、压抑空间"
        palette = "冷灰、旧木棕、香火红、土黄、煤黑"
        power = "出马仙/堂口/供奉规则；人与异物通过禁忌、因果和仪式发生联系"
        taboo = "不乱许愿、不轻慢供奉、不在夜里挑衅异物、不破坏堂口规矩"
    elif wuxia:
        visual = "古装武侠写实，低饱和布料、旧木、铁器冷光、风尘感"
        palette = "灰蓝、旧木棕、铁黑、暗红、尘土黄"
        power = "武功、兵器、身份压迫和江湖规矩推动冲突"
        taboo = "不可跳轴、不可现代物件、不可魔法化发光特效"
    else:
        visual = "电影写实，低饱和色彩，空间稳定，人物表演优先"
        palette = "冷灰、暖黄、暗棕、低饱和肤色"
        power = "现实压力、人际关系和场景限制推动行动"
        taboo = "不加入原文没有的超自然规则，不乱加现代物件"
    return {
        "era_setting 时代背景": "由原文判定；未明示时保持模糊年代，避免乱加现代元素",
        "geographic_setting 地域环境": "由场景线索决定；民俗题材优先乡村/屯子/堂口空间，武侠题材优先江湖/院落/山路",
        "folk_system 民俗体系": "堂口、上香、供奉、仙家、禁忌" if folk else "未明确民俗体系，禁止强行加入",
        "power_system 力量规则": power,
        "taboo_rules 禁忌规则": taboo,
        "belief_system 信仰体系": "民俗信仰与因果秩序" if folk else "按原文世界观处理",
        "social_order 社会秩序": "身份、辈分、行业规矩和恐惧关系决定人物压迫感",
        "visual_style 视觉风格": visual,
        "color_palette 色卡": palette,
        "camera_mood 镜头气质": "克制、低机位少量推进、动作节点硬切、空间关系清楚",
        "sound_mood 声音气质": "环境底音稳定，关键处留静默，动作/道具声短促清楚",
    }


def build_character_cards(project: Project) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for index, char in enumerate(project.characters, start=1):
        name = char.get("character_name 角色名", f"角色{index}")
        role_type = infer_role_type(name, index)
        cards.append({
            "character_id 角色编号": char.get("character_id 角色编号", f"CHAR_{index:02d}"),
            "character_name 角色名": name,
            "role_type 角色类型": role_type,
            "age_feel 年龄感": "约18-25岁" if index == 1 else "约30-45岁或按原文调整",
            "appearance 外貌特征": char.get("face_shape 脸型", "清晰可识别脸型") + "，五官稳定",
            "body_shape 体型": "偏瘦但动作敏捷" if index == 1 else "结实或压迫感更强",
            "face_shape 脸型": char.get("face_shape 脸型", "固定脸型"),
            "hair_style 发型": char.get("hair_style 发型", "固定发型"),
            "clothing 服装": char.get("clothing_lock 服装锁定", "固定服装"),
            "identity 身份": char.get("role_function 角色功能", role_type),
            "personality 性格": "隐忍、警觉、带目标感" if index == 1 else "压迫、试探或推动冲突",
            "motivation 动机": "推动核心事件并承受主要冲突" if index == 1 else "制造压力或提供信息",
            "habitual_actions 动作习惯": "先停顿、看向对方、手部收紧，再行动",
            "speaking_style 说话习惯": "短句、压低声音、少解释" if index == 1 else "语气更强势或更试探",
            "visual_keywords 视觉关键词": char.get("clothing_lock 服装锁定", "固定服装") + "，" + char.get("hair_style 发型", "固定发型"),
            "forbidden_changes 禁改项": char.get("forbidden_changes 禁止变化", "禁止换脸、换发型、换服装、年龄变化"),
        })
    return cards


def build_three_view_prompts(project: Project) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for card in build_character_cards(project):
        base = f"{card['character_name 角色名']}，{card['role_type 角色类型']}，{card['appearance 外貌特征']}，{card['clothing 服装']}，{card['visual_keywords 视觉关键词']}，电影写实概念设计，灰色棚拍背景，比例一致"
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


def build_scene_plan(project: Project) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for scene in project.scenes:
        out.append({
            "scene_id 场景编号": scene.get("scene_id 场景编号", "SCENE_01"),
            "scene_name 场景名": scene.get("scene_name 场景名", "主场景"),
            "scene_type 场景类型": infer_scene_type(scene.get("scene_name 场景名", "")),
            "narrative_function 叙事功能": "承载事件发生、人物压迫和视觉锚点",
            "location 地点": scene.get("scene_name 场景名", "主场景"),
            "time_of_day 时间": scene.get("time_of_day 时间段", "由原文决定"),
            "weather 天气": "由原文决定；未明示时保持稳定天气",
            "lighting 光线": scene.get("lighting_direction 光线方向", "稳定侧光"),
            "space_layout 空间布局": scene.get("layout_map 空间布局", "A左B右，前中后景清楚"),
            "fixed_props 固定物件": scene.get("fixed_props 固定物件", "门、桌、墙面或场景固定物"),
            "entry_exit 进出路线": "人物从画面边缘或门口进入，避免空间跳变",
            "visual_mood 视觉氛围": scene.get("visual_prompt 视觉提示词", "低饱和写实空间"),
            "sound_bed 环境底音": "风声、远处空响、脚步或场景固有底噪",
        })
    return out


def build_asset_lock(project: Project) -> dict[str, Any]:
    return {
        "character_lock 角色锁定": [c.get("character_name 角色名", "") + " / " + c.get("clothing_lock 服装锁定", "固定服装") for c in project.characters],
        "scene_lock 场景锁定": [s.get("scene_name 场景名", "") + " / " + s.get("fixed_props 固定物件", "固定物件") for s in project.scenes],
        "prop_lock 道具锁定": [p.get("prop_name 道具名", "") for p in project.props],
        "entity_lock 异物锁定": detect_terms(project.data.get("source_text 原文", ""), ROLE_KEYWORDS["creature 异物"] + ROLE_KEYWORDS["immortal_or_spirit 仙家/灵体"]),
        "color_lock 色卡锁定": project.data.get("story_bible 世界观圣经", {}).get("color_palette 色卡", "低饱和冷灰暖黄"),
        "costume_lock 服装锁定": [c.get("clothing_lock 服装锁定", "固定服装") for c in project.characters],
        "continuity_lock 连续性锁定": "同脸、同发型、同服装、同道具归属、同场景固定物、同色卡，不随镜头漂移",
    }


def build_event_blocks(text: str, project: Project) -> list[dict[str, Any]]:
    lines = split_event_lines(text)
    blocks: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        blocks.append({
            "block_id 段落编号": f"BLOCK_{index:02d}",
            "block_name 段落名": infer_event_block_name(line, index),
            "story_function 剧情功能": infer_event_function(line),
            "main_characters 主要人物": detect_beat_people(line, project) or choose_main_characters(project),
            "main_scene 主要场景": detect_terms(line, SCENE_KEYWORDS) or [project.scenes[0].get("scene_name 场景名", "主场景") if project.scenes else "主场景"],
            "key_props 关键道具": detect_terms(line, PROP_KEYWORDS) or [p.get("prop_name 道具名", "关键道具") for p in project.props[:2]],
            "core_event 核心事件": line[:120],
            "conflict 核心冲突": "、".join(detect_conflicts(line)) or "低强度关系压力",
            "recommended_clip_type 建议片段类型": infer_clip_type_cn(line),
        })
    return blocks


def build_action_choreography(project: Project) -> None:
    rows: list[dict[str, Any]] = []
    for shot in project.shots:
        action = shot.get("action_detail 动作细节", "")
        clip_type = shot.get("clip_type 片段类型", "")
        if not (clip_type.startswith(("fight", "action")) or any(word in action for word in ACTION_WORDS)):
            continue
        rows.append({
            "action_id 动作编号": f"ACT_{len(rows)+1:03d}",
            "related_shot_id 对应镜头编号": shot.get("shot_id 镜头编号", ""),
            "start_state 起点状态": shot.get("entry_pose 起始姿态", shot.get("planned_start_state 计划起始状态", "")),
            "end_state 终点状态": shot.get("exit_pose 结束姿态", shot.get("planned_end_state 计划结束状态", "")),
            "attack_line 攻击线": "沿画面左到右或主冲突轴线推进，禁止跳轴",
            "defense_line 防守线": "防守方向与攻击线相反，身体后退或侧让半步",
            "contact_point 接触点": infer_contact_point(action),
            "impact_result 结果": shot.get("planned_end_state 计划结束状态", "动作结果明确落点"),
            "screen_direction 画面方向": shot.get("screen_direction 画面方向", "保持同侧轴线"),
            "safety_note 安全说明": "只拍一个动作节点，禁止一镜连续复杂打斗",
            "fallback_shot 备用镜头": shot.get("fallback_shot 备用镜头", "改手部/兵器/反应特写"),
        })
    project.data["action_choreography 动作编排表"] = rows


def infer_source_type(text: str) -> str:
    if "镜头" in text or "场景" in text or "对白" in text:
        return "script 剧本"
    if len(text) > 300:
        return "novel_chapter 小说章节"
    return "creative_seed 创意梗概"


def summarize_text(text: str) -> str:
    cleaned = " ".join(text.split())
    return cleaned[:180] if cleaned else "空输入，需要补充原文"


def split_event_lines(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    parts = re.split(r"(?<=[。！？!?；;])", cleaned)
    out = [p.strip() for p in parts if p.strip()]
    return out[:12] or ([cleaned[:160]] if cleaned else ["空输入"])


def choose_main_characters(project: Project) -> list[str]:
    return [c.get("character_name 角色名", "主角") for c in project.characters[:1]] or ["主角"]


def detect_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def detect_conflicts(text: str) -> list[str]:
    words = ["求助", "失踪", "被打死", "追", "逃", "杀", "禁忌", "报仇", "上门", "闯入", "威胁", "守夜", "异物"]
    return detect_terms(text, words)


def infer_genre(text: str) -> str:
    if any(word in text for word in ["堂口", "黄皮子", "仙家", "出马"]):
        return "folk_suspense 民俗悬疑"
    if any(word in text for word in ["刀", "剑", "镖", "江湖"]):
        return "wuxia_action 武侠动作"
    return "cinematic_drama 电影写实剧情"


def infer_risk_points(text: str) -> list[str]:
    risks = ["人物一致性", "场景跳变", "提示词抽象化"]
    if any(word in text for word in ACTION_WORDS):
        risks.append("动作崩坏")
    if any(word in text for word in ["仙家", "黄皮子", "怪物", "异物"]):
        risks.append("异物形象不稳定")
    return risks


def infer_role_type(name: str, index: int) -> str:
    for role, terms in ROLE_KEYWORDS.items():
        if any(term in name for term in terms):
            return role
    return "protagonist 主角" if index == 1 else "supporting 配角"


def infer_scene_type(name: str) -> str:
    if any(word in name for word in ["堂口", "香案"]):
        return "ritual_space 仪式空间"
    if any(word in name for word in ["鸡窝", "院子", "树林", "山路"]):
        return "exterior_action_space 外景动作空间"
    return "dialogue_or_action_space 对话/动作空间"


def infer_event_block_name(line: str, index: int) -> str:
    if "上香" in line or "堂口" in line:
        return "ritual_incense 堂口上香"
    if "求助" in line or "上门" in line:
        return "client_arrival 求助上门"
    if "鸡窝" in line or "守" in line:
        return "night_watch 夜守鸡窝"
    if "打死" in line or "杀" in line or "黄皮子" in line:
        return "entity_incident 异物事件爆发"
    if index == 1:
        return "opening_setup 开场设定"
    return f"event_block_{index:02d} 事件段落{index:02d}"


def infer_event_function(line: str) -> str:
    if any(word in line for word in ["求助", "讲述", "说"]):
        return "交代信息并建立请求"
    if any(word in line for word in ACTION_WORDS):
        return "推动动作冲突并改变权力关系"
    if any(word in line for word in ["上香", "堂口", "禁忌"]):
        return "建立世界观规则和禁忌"
    return "推进事件并建立下一段悬念"


def infer_clip_type_cn(line: str) -> str:
    if any(word in line for word in ["打", "杀", "砍", "刺", "扑", "挡", "格"]):
        return "fight_clip 打戏片段"
    if any(word in line for word in ACTION_WORDS):
        return "action_clip 动作片段"
    if any(word in line for word in ["说", "问", "求助", "讲述"]):
        return "dialogue_clip 对白片段"
    if any(word in line for word in ["上香", "堂口", "供奉"]):
        return "ritual_clip 仪式片段"
    return "suspense_clip 悬疑片段"


def detect_beat_people(line: str, project: Project) -> list[str]:
    names = []
    for char in project.characters:
        name = char.get("character_name 角色名", "")
        if name and name in line:
            names.append(name)
    return names


def infer_contact_point(action: str) -> str:
    if "剑" in action or "刀" in action:
        return "兵器接触点：刀剑/手腕/格挡位置"
    if "扑" in action or "撞" in action:
        return "身体接触点：肩、胸口或侧身冲击"
    if "咬" in action:
        return "异物接触点：手臂、衣摆或道具边缘"
    return "接触点按本镜动作节点确认，优先手部/道具/脚步特写"
