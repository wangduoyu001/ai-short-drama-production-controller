from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .constants import DEFAULT_LIMITS
from .models import Project
from .yaml_io import write_project_yaml, write_text


def detect_input_type(text: str) -> str:
    lowered = text.lower()
    if "http" in lowered or "参考片" in text or "原片" in text:
        return "reference_video 参考片"
    if any(mark in text for mark in ["INT.", "EXT.", "对白", "台词", "旁白", "镜头", "场景"]):
        return "script 剧本"
    if len(text) > 500 and any(x in text for x in ["他说", "她说", "忽然", "少年", "男人", "女人"]):
        return "novel_excerpt 小说片段"
    if "CHAR_" in text or "SCENE_" in text or "SH" in text:
        return "partial_work 半成品"
    return "story_idea 口述创意"


def infer_genre(text: str) -> str:
    genre_words = [
        ("武侠", "wuxia 武侠"),
        ("修仙", "xianxia 修仙"),
        ("玄幻", "fantasy 玄幻"),
        ("镖局", "wuxia 武侠"),
        ("宗门", "xianxia 修仙"),
        ("山村", "folk_horror 民俗悬疑"),
        ("怪谈", "folk_horror 民俗悬疑"),
        ("都市", "urban 都市"),
        ("神医", "urban_medical 神医都市"),
    ]
    for word, genre in genre_words:
        if word in text:
            return genre
    return "drama_dialogue 对话短剧"


def estimate_complexity(text: str) -> dict[str, Any]:
    character_markers = len(set(re.findall(r"(少年|男人|女人|师兄|师父|长老|镖头|母亲|父亲|反派|弟子|老板|女主|男主)", text)))
    scene_markers = len(set(re.findall(r"(院子|山路|破庙|房间|大殿|宗门|镖局|街道|树林|屋内|门口)", text)))
    action_hits = len(re.findall(r"(打斗|大战|冲|追|跑|飞|砍|刺|爆炸|法术|群战|围攻)", text))
    dialogue_hits = len(re.findall(r"[“\"].+?[”\"]", text))
    return {
        "estimated_character_count 估算角色数": max(character_markers, 2),
        "estimated_scene_count 估算场景数": max(scene_markers, 1),
        "estimated_action_hits 估算动作词数量": action_hits,
        "estimated_dialogue_lines 估算对白句数": dialogue_hits,
    }


def create_project_from_input(text: str, title: str | None = None) -> Project:
    project = Project()
    input_type = detect_input_type(text)
    genre = infer_genre(text)
    complexity = estimate_complexity(text)
    project.data.update({
        "project_name 项目名": title or "untitled_short_drama 未命名短剧",
        "skill_version 技能版本": "0.1.0",
        "input_type 输入类型": input_type,
        "genre 类型": genre,
        "production_mode 制作模式": DEFAULT_LIMITS["production_mode 制作模式"],
        "target_platform 目标平台": "LibTV / Lovart",
        "scope_gate 范围闸门": run_scope_gate(complexity),
        "input_summary 输入摘要": summarize_text(text),
        "core_conflict 核心冲突": infer_core_conflict(text),
        "difficulty_budget 难度预算": build_difficulty_budget(complexity),
    })
    project.data["characters 角色列表"] = build_default_characters(text)
    project.data["scenes 场景列表"] = build_default_scenes(text)
    project.data["props 道具列表"] = build_default_props(text)
    project.data["asset_reuse_plan 资产复用计划"] = build_asset_reuse_plan(project)
    project.data["blocking_plan 人物调度计划"] = build_blocking_plan()
    project.data["shots 分镜列表"] = build_shots(project)
    project.data["continuity_map 连续性地图"] = build_continuity_map()
    return project


def summarize_text(text: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    return clean[:limit] + ("..." if len(clean) > limit else "")


def infer_core_conflict(text: str) -> str:
    if "镖局" in text:
        return "新人想进入镖局，被老镖师或师兄质疑，用一次试招证明自己。"
    if "宗门" in text or "修仙" in text:
        return "低阶弟子被质疑天赋，在试炼中暴露异常能力。"
    if "怪谈" in text or "山村" in text:
        return "主角遇到违反常理的事件，被迫面对隐藏真相。"
    return "主角提出目标，对手质疑或阻拦，双方通过正反打对白升级冲突。"


def run_scope_gate(complexity: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    blockers = []
    if complexity["estimated_character_count 估算角色数"] > 4:
        blockers.append("character_count 角色数量过多，必须合并到2-3人。")
    if complexity["estimated_scene_count 估算场景数"] > 2:
        blockers.append("main_scene_count 主场景过多，必须合并为1个主场景。")
    if complexity["estimated_action_hits 估算动作词数量"] > 8:
        warnings.append("action_level 动作等级偏高，必须拆成插入镜头和结果镜头。")
    status = "BLOCKER" if blockers else ("WARN" if warnings else "PASS")
    return {
        "scope_status 范围状态": status,
        "default_limits 默认限制": DEFAULT_LIMITS,
        "warnings 警告": warnings,
        "blockers 阻塞": blockers,
        "reduced_scope 压缩后范围": "60-90秒，8-12镜，2-3人，1个主场景，正反打对白优先，少量动作。",
        "production_boundary 制作边界": "本轮只做一个可生产样片，不做长剧、多场景、大群戏、长打斗。",
    }


def build_difficulty_budget(complexity: dict[str, Any]) -> dict[str, Any]:
    score = 0
    score += min(complexity["estimated_character_count 估算角色数"], 4)
    score += min(complexity["estimated_scene_count 估算场景数"], 3)
    score += min(complexity["estimated_action_hits 估算动作词数量"] // 2, 4)
    score += 2
    status = "PASS" if score <= 7 else "WARN" if score <= 10 else "BLOCKER"
    return {"difficulty_score 难度分": score, "difficulty_status 难度状态": status, "budget_limit 预算上限": 10, "repair_hint 修复建议": "超过10分时，压缩角色、场景、动作和复杂机位。"}


def build_default_characters(text: str) -> list[dict[str, Any]]:
    if "镖局" in text or "武侠" in text:
        return [
            character("CHAR_A", "少年", "主角", "20岁", "瘦削长脸", "黑色束发", "灰蓝布衣，黑色腰带", "木剑", "说话前先垂眼"),
            character("CHAR_B", "镖头", "对手/考官", "45岁", "方脸短须", "黑发束起", "深褐短打，旧皮护腕", "短刀", "说话时手按刀柄"),
        ]
    return [
        character("CHAR_A", "男主", "主角", "30岁", "瘦削疲惫脸", "短黑发", "灰色夹克，黑裤", "手机", "紧张时握紧手机"),
        character("CHAR_B", "对手", "阻碍者", "40岁", "方脸锐眼", "整齐黑发", "深色外套", "无", "说话时身体不动，只转眼"),
    ]


def character(cid: str, name: str, role: str, age: str, face: str, hair: str, clothing: str, prop: str, behavior: str) -> dict[str, Any]:
    return {"character_id 角色编号": cid, "character_name 角色名": name, "role_function 角色功能": role, "age 年龄": age, "face_shape 脸型": face, "facial_anchor 脸部锚点": face, "hair_style 发型": hair, "body_type 体型": "中等体型", "clothing_lock 服装锁定": clothing, "color_lock 色彩锁定": "低饱和、暗色系、避免鲜艳跳色", "prop_lock 道具锁定": prop, "behavior_anchor 行为锚点": behavior, "forbidden_changes 禁止变化": "禁止换脸、禁止换发型、禁止换服装、禁止年龄变化、禁止现代不相关物件", "reference_image_lock 参考图锁": {"face_reference 脸部参考": f"{cid}_face_ref", "outfit_reference 服装参考": f"{cid}_outfit_ref", "fullbody_reference 全身参考": f"{cid}_fullbody_ref"}}


def build_default_scenes(text: str) -> list[dict[str, Any]]:
    if "镖局" in text or "武侠" in text:
        return [scene("SCENE_01", "镖局院子", "古代架空", "傍晚", "左侧暖黄侧光", "土黄、暗红、灰黑", "左侧大门，右侧兵器架，后方院墙，中央空地", "木门、兵器架、旧旗、石砖地")]
    return [scene("SCENE_01", "简洁对话场景", "现代或架空", "夜晚", "稳定侧光", "灰黑、暗蓝", "A在左，B在右，中间有桌子或空地", "桌子、门、墙面")]


def scene(sid: str, name: str, era: str, time: str, lighting: str, palette: str, layout: str, props: str) -> dict[str, Any]:
    return {"scene_id 场景编号": sid, "scene_name 场景名": name, "era 时代": era, "time_of_day 时间": time, "lighting_direction 光线方向": lighting, "color_palette 色卡": palette, "layout_map 空间布局": layout, "fixed_props 固定物件": props, "forbidden_elements 禁止元素": "禁止风格漂移，禁止出现与时代不符的现代物件，禁止突然改变空间方位", "scene_reference 场景参考": f"{sid}_ref"}


def build_default_props(text: str) -> list[dict[str, Any]]:
    if "镖局" in text or "武侠" in text:
        return [{"prop_id 道具编号": "PROP_01", "prop_name 道具名": "木剑", "prop_lock 道具锁定": "旧木剑，深棕色，始终在CHAR_A右手或腰侧"}, {"prop_id 道具编号": "PROP_02", "prop_name 道具名": "短刀", "prop_lock 道具锁定": "短刀黑柄，始终在CHAR_B腰侧"}]
    return [{"prop_id 道具编号": "PROP_01", "prop_name 道具名": "手机", "prop_lock 道具锁定": "黑色手机，始终在CHAR_A右手"}]


def build_asset_reuse_plan(project: Project) -> dict[str, Any]:
    score = 8 if len(project.characters) <= 3 and len(project.scenes) == 1 else 6
    recommended = 5 if score >= 8 else 3 if score >= 6 else 1
    return {"asset_reuse_score 资产复用评分": score, "recommended_episode_count 建议制作集数": recommended, "reusable_characters 可复用角色": [c["character_id 角色编号"] for c in project.characters], "reusable_scenes 可复用场景": [s["scene_id 场景编号"] for s in project.scenes], "reusable_props 可复用道具": [p["prop_id 道具编号"] for p in project.props], "expansion_risk 扩展风险": "low 低" if recommended >= 5 else "medium 中", "next_episode_strategy 下一集策略": "先完成1集样片；如果角色脸和服装稳定，再扩展到3-5集。"}


def build_blocking_plan() -> dict[str, Any]:
    return {"blocking_id 调度编号": "BLOCK_01", "scene_id 场景编号": "SCENE_01", "character_a_position A角色位置": "画面左侧，面向右", "character_b_position B角色位置": "画面右侧，面向左", "axis_line 轴线": "CHAR_A 与 CHAR_B 的连线", "safe_camera_zone 安全机位区": "摄影机始终在轴线同一侧，禁止越轴", "eyeline_a A视线方向": "A看向画面右侧", "eyeline_b B视线方向": "B看向画面左侧", "distance_between_characters 角色距离": "约三步", "power_relation 权力关系": "B压迫A，A逐渐反击", "blocking_change 调度变化": "A从左侧前进一步，B保持不动形成压迫"}


def build_shots(project: Project) -> list[dict[str, Any]]:
    scene_id = project.scenes[0]["scene_id 场景编号"]
    return [
        shot("SH001", "master_shot 主镜头", 5, scene_id, ["CHAR_A", "CHAR_B"], "A左B右，建立空间", "无", "fixed_camera 固定机位", "全景 WS", "建立空间和人物距离", "如果空间崩，改为空镜+脚步声"),
        shot("SH002", "shot_a A正打", 5, scene_id, ["CHAR_A"], "A在画面左侧，看向右", "我只问一句，我能不能留下？", "slow_push_in 缓慢推进", "近景 CU", "A克制开口", "如果脸崩，改为侧脸低头"),
        shot("SH003", "shot_b B反打", 5, scene_id, ["CHAR_B"], "B在画面右侧，看向左", "凭什么？", "fixed_camera 固定机位", "近景 CU", "B冷声质疑", "如果表情失败，改为手按刀柄特写"),
        shot("SH004", "insert_shot 插入镜头", 3, scene_id, ["CHAR_A"], "A右手握紧木剑", "无", "fixed_camera 固定机位", "特写 ECU", "手部和道具特写", "如果手崩，改为木剑落地特写"),
        shot("SH005", "shot_a A正打", 5, scene_id, ["CHAR_A"], "A前进一步，仍在轴线左侧", "就凭我还站着。", "slow_push_in 缓慢推进", "中近景 MCU", "A向前半步，情绪上升", "如果前进失败，改为衣摆动+脚步声"),
        shot("SH006", "reaction_shot 反应镜头", 4, scene_id, ["CHAR_B"], "B不动，眼神变化", "无", "fixed_camera 固定机位", "近景 CU", "B沉默半秒", "如果眼神失败，改为短刀护腕特写"),
        shot("SH007", "movement_result 动作结果", 5, scene_id, ["CHAR_A", "CHAR_B"], "A木剑抬起，B后退半步", "无", "slight_lateral_move 轻微横移", "中景 MS", "一招结果，不拍完整打斗", "改为剑光闪过+B后退"),
        shot("SH008", "shot_b B反打", 5, scene_id, ["CHAR_B"], "B画面右侧，看向左，压低声音", "明日卯时，来押第一趟镖。", "slow_push_in 缓慢推进", "近景 CU", "B给出认可但保留压力", "如果口型差，改为背影台词"),
        shot("SH009", "hook_shot 结尾钩子", 5, scene_id, ["CHAR_A"], "A低头看木剑，风吹旧旗", "无", "fixed_camera 固定机位", "中近景 MCU", "留下悬念", "如果脸不稳，改为背影+旧旗"),
    ]


def shot(sid: str, purpose: str, duration: int, scene_id: str, chars: list[str], position: str, dialogue: str, camera: str, size: str, action: str, fallback: str) -> dict[str, Any]:
    return {"shot_id 镜头编号": sid, "shot_purpose 镜头目的": purpose, "duration_seconds 时长秒数": duration, "scene_id 场景编号": scene_id, "character_ids 角色编号": chars, "character_position_start 角色起始位置": position, "character_position_end 角色结束位置": position, "motion_path 运动轨迹": "起点和终点保持清晰；如有移动，只允许前进一步或后退半步", "eyeline_direction 视线方向": "A看右，B看左，禁止跳轴", "axis_line 轴线": "A-B连线，摄影机不越轴", "shot_size 景别": size, "camera_angle 机位角度": "轴线同侧，侧前方约30度", "camera_height 机位高度": "眼平高度", "camera_movement 机位运动": camera, "lens_feel 镜头感": "50mm近景或35mm中景", "composition 构图": "主体清晰，背景不抢戏", "depth_layer 前中后景": "前景少量遮挡，中景人物，后景固定场景物件", "action_detail 动作细节": action, "dialogue_line 对白": dialogue, "emotional_state 情绪状态": "克制、压迫、试探", "sound_design 声音设计": "环境声、脚步、衣料摩擦，必要时加短暂停顿", "continuity_locks 连续性锁定": "同脸、同发型、同服装、同道具、同站位逻辑", "generation_risk 生成风险": "脸崩、手崩、跳轴、口型不同步", "fallback_shot 备用镜头": fallback}


def build_continuity_map() -> dict[str, Any]:
    return {"character_position_map 人物位置图": "CHAR_A始终在画面左侧逻辑，CHAR_B始终在画面右侧逻辑", "prop_state_map 道具状态图": "CHAR_A木剑在右手或腰侧，CHAR_B短刀在腰侧", "emotion_state_map 情绪状态图": "A从克制到坚定，B从压迫到认可", "camera_side_map 机位侧别图": "全程保持轴线同一侧", "scene_state_map 场景状态图": "主场景空间不变", "costume_state_map 服装状态图": "所有镜头服装不变", "injury_state_map 伤痕状态图": "本集无伤痕变化"}


def write_project_files(project: Project, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_project_yaml(out_dir / "project.yaml", project.data)
    write_text(out_dir / "script.md", render_script(project))
    write_text(out_dir / "assets.md", render_assets(project))
    write_text(out_dir / "storyboard.md", render_storyboard(project))
    write_text(out_dir / "prompts.md", render_prompts(project))
    write_text(out_dir / "qa.md", "# qa_report 质检报告\n\n尚未运行 qa_gate 质检闸门。\n")
    (out_dir / "exports").mkdir(exist_ok=True)


def render_script(project: Project) -> str:
    return f"""# script 剧本\n\n## project_name 项目名\n{project.data['project_name 项目名']}\n\n## core_conflict 核心冲突\n{project.data['core_conflict 核心冲突']}\n\n## scene 场次\nSCENE_01 主场景内完成一场正反打冲突。开场建立空间，中段对白对峙，后段一招结果，结尾留钩子。\n\n## dialogue_rules 对白规则\n- 单镜最多一句对白。\n- 单句尽量控制在25个中文字符以内。\n- 对白之间必须有反应镜头或插入镜头。\n"""


def render_assets(project: Project) -> str:
    lines = ["# assets 资产\n", "## characters 角色\n"]
    for c in project.characters:
        lines.append(_md_table(c))
    lines.append("\n## scenes 场景\n")
    for s in project.scenes:
        lines.append(_md_table(s))
    lines.append("\n## props 道具\n")
    for p in project.props:
        lines.append(_md_table(p))
    lines.append("\n## asset_reuse_plan 资产复用计划\n")
    lines.append(_md_table(project.data["asset_reuse_plan 资产复用计划"]))
    return "\n".join(lines)


def render_storyboard(project: Project) -> str:
    lines = ["# storyboard 分镜\n", "## blocking_plan 人物调度计划\n", _md_table(project.data["blocking_plan 人物调度计划"]), "\n## storyboard_sketch 草图分镜规则\n", "| english_name 中文字段 | requirement 要求 |\n|---|---|\n| frame_id 画框编号 | 对应 shot_id 镜头编号 |\n| character_blocking 人物调度 | A左B右，距离明确 |\n| motion_arrow 运动箭头 | 起点、终点、方向明确 |\n| camera_arrow 机位箭头 | 推、拉、横移方向明确 |\n| eyeline_arrow 视线箭头 | A看B，B看A |\n| axis_line 轴线 | 明确180度轴线 |\n| safe_camera_zone 安全机位区 | 摄影机只能在轴线一侧 |\n| prop_position 道具位置 | 道具位置前后统一 |\n", "\n## shot_plan 分镜计划\n"]
    for shot_data in project.shots:
        lines.append(f"\n### {shot_data['shot_id 镜头编号']} {shot_data['shot_purpose 镜头目的']}\n")
        lines.append(_md_table(shot_data))
    return "\n".join(lines)


def render_prompts(project: Project) -> str:
    lines = ["# prompts 提示词\n", "## character_asset_prompt 人物资产提示词\n"]
    for c in project.characters:
        lines.append(f"### {c['character_id 角色编号']} {c['character_name 角色名']}\n{c['character_name 角色名']}，{c['age 年龄']}，{c['face_shape 脸型']}，{c['hair_style 发型']}，{c['clothing_lock 服装锁定']}，{c['prop_lock 道具锁定']}，三视图，正面、侧面、背面，脸部特写，服装细节特写，neutral studio background 中性背景，consistent character design 角色一致性，禁止换脸、禁止换发型、禁止换服装。\n")
    lines.append("\n## scene_asset_prompt 场景资产提示词\n")
    for s in project.scenes:
        lines.append(f"### {s['scene_id 场景编号']} {s['scene_name 场景名']}\n{s['scene_name 场景名']}，{s['era 时代']}，{s['time_of_day 时间']}，{s['lighting_direction 光线方向']}，{s['color_palette 色卡']}，空间布局：{s['layout_map 空间布局']}，固定物件：{s['fixed_props 固定物件']}，全景、中景背景、空镜，禁止出现：{s['forbidden_elements 禁止元素']}。\n")
    lines.append("\n## video_prompt 视频提示词\n")
    for sh in project.shots:
        chars = ", ".join(sh["character_ids 角色编号"])
        lines.append(f"### {sh['shot_id 镜头编号']} {sh['shot_purpose 镜头目的']}\n\nplatform 目标平台：LibTV / Lovart\ncharacter_reference 角色参考：{chars}\nscene_reference 场景参考：{sh['scene_id 场景编号']}\naction_description 动作描述：{sh['action_detail 动作细节']}\nmotion_path 运动轨迹：{sh['motion_path 运动轨迹']}\ncamera_description 机位描述：{sh['shot_size 景别']}，{sh['camera_angle 机位角度']}，{sh['camera_height 机位高度']}，{sh['camera_movement 机位运动']}，{sh['lens_feel 镜头感']}\nemotional_performance 情绪表演：{sh['emotional_state 情绪状态']}\ndialogue_line 对白：{sh['dialogue_line 对白']}\ncontinuity_locks 连续性锁定：{sh['continuity_locks 连续性锁定']}\nnegative_prompt 负面提示词：禁止换脸，禁止换服装，禁止发型变化，禁止现代错误物件，禁止跳轴，禁止复杂运镜，禁止多人混战，禁止手指畸形，禁止道具消失\nfallback_prompt 备用提示词：{sh['fallback_shot 备用镜头']}\n")
    return "\n".join(lines)


def _md_table(data: dict[str, Any]) -> str:
    rows = ["| english_name 中文字段 | value 值 |", "|---|---|"]
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            value = str(value)
        rows.append(f"| {key} | {value} |")
    return "\n".join(rows)
