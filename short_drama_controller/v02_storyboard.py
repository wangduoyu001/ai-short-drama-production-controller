from __future__ import annotations

import re
from typing import Any

from .v02_models import Project

ALLOWED_CAMERA = {
    "fixed_camera 固定机位",
    "slow_push_in 缓慢推进",
    "slight_lateral_move 轻微横移",
    "subtle_handheld 轻微手持",
}

CONFLICT_WORDS = ["杀", "死", "逃", "追", "逼", "威胁", "怒", "喝", "跪", "押", "围", "断", "血", "伤", "不许", "不能", "偏要", "拒绝", "护送", "灭世", "仇", "恨", "夺", "抢", "欺"]
TURN_WORDS = ["突然", "却", "但", "然而", "终于", "转身", "没有回头", "停下", "抬头", "拔", "握", "沉默", "冷笑"]
POWER_WORDS = ["大人", "将军", "镖头", "掌门", "师父", "官", "王", "帝女", "少年", "少女", "众人", "跪", "押", "围"]
SUBTEXT_WORDS = ["沉默", "低声", "冷笑", "没有回头", "看着", "盯着", "握", "停顿", "颤", "咬牙"]
PROP_WORDS = ["刀", "剑", "枪", "弓", "碗", "酒", "门", "信", "令牌", "马", "镖", "箱", "火", "灯", "帘"]
SCENE_WORDS = ["破庙", "客栈", "街", "巷", "大殿", "山路", "树林", "屋内", "门外", "院中", "城门", "码头", "桥", "雨夜"]
BANNED_PLACEHOLDERS = ["情绪或动作推进", "运动或情绪起点明确", "运动结果或情绪落点明确", "建立空间和轴线", "手部或道具特写"]


def build_shots(project: Project) -> None:
    scene0 = first_scene(project)
    char_a = first_character(project)
    char_b = project.characters[1] if len(project.characters) > 1 else char_a
    source_text = project.data.get("source_text 原文", "")
    director_read = build_director_read(source_text, scene0, char_a, char_b)
    beat_map = build_beat_map(source_text, project, director_read)

    project.data["beat_map 剧情节拍表"] = beat_map
    project.data["director_read 导演读本"] = director_read
    project.data["project_state_capsule 项目状态胶囊"] = build_state_capsule(project, director_read)
    project.data["producer_plan 制片执行计划"] = build_producer_plan(project)
    project.data["approval_gates 确认闸门"] = build_approval_gates()

    shots: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None
    for index, beat in enumerate(beat_map[:12], start=1):
        scene = choose_scene_for_beat(project, beat)
        chars = choose_shot_characters(project, beat, index)
        shot = make_shot(f"SH{index:03d}", beat, scene, chars, index, director_read, project, previous)
        shots.append(shot)
        previous = shot

    project.data["blocking_plan 人物调度计划"] = {
        "axis_line 轴线": "核心冲突人物连线；三人以上先用 master_shot 建立空间",
        "safe_camera_zone 安全机位区": "摄影机保持在轴线同侧，多人物时以主冲突两人为轴线",
        "scene_binding 场景绑定": "每个 shot 必须来自 beat.scene_hint 或原文场景证据",
        "character_limit 人物限制": "单镜最多调度3个核心人物，更多人物改为crowd 群像或拆镜",
    }
    project.data["shots 分镜列表"] = shots
    project.data["storyboard_layout 分镜总览布局"] = choose_storyboard_layout(len(shots))
    project.data["storyboard_grid_ascii 分镜总览简笔图"] = build_storyboard_grid_ascii(shots)
    project.data["dialogue_coverage_ascii 对白覆盖图"] = build_dialogue_coverage_ascii(shots)


def build_beat_map(text: str, project: Project, director_read: dict[str, str]) -> list[dict[str, str]]:
    units = split_source_units(text) or ["原文为空：需要用户补充故事原文"]
    beats = [build_beat(unit, project, index) for index, unit in enumerate(units, start=1)]
    return expand_coverage_beats(beats, project, director_read)


def build_beat(unit: str, project: Project, index: int) -> dict[str, str]:
    dialogue = first_dialogue(unit)
    conflict = "、".join(find_terms(unit, CONFLICT_WORDS)) or "关系压力较低，需要用表演细节承载"
    turn = "、".join(find_terms(unit, TURN_WORDS)) or "状态推进"
    visible_action = extract_visible_action(unit, dialogue)
    return {
        "beat_id 节拍编号": f"B{index:03d}",
        "source_quote 原文证据": unit[:180],
        "visible_action 可见动作": visible_action,
        "dialogue 对白": dialogue or "无",
        "conflict 冲突": conflict,
        "emotion_shift 情绪变化": infer_emotion_shift(unit, conflict, turn),
        "power_shift 权力变化": infer_beat_power(unit, project),
        "subtext 潜台词": infer_beat_subtext(unit, dialogue),
        "shot_hint 镜头建议": choose_shot_hint(index, unit, dialogue, visible_action),
        "scene_hint 场景建议": detect_scene_hint(unit, project),
        "characters 相关角色": "、".join(detect_beat_characters(unit, project)) or "主角",
        "coverage_role 覆盖功能": "source 源节拍",
    }


def expand_coverage_beats(beats: list[dict[str, str]], project: Project, director_read: dict[str, str]) -> list[dict[str, str]]:
    target = choose_target_shot_count(beats)
    expanded = list(beats)
    source = beats[-1]
    while len(expanded) < target:
        base = beats[(len(expanded) - len(beats)) % len(beats)] if beats else source
        expanded.append(make_coverage_beat(base, len(expanded) + 1, project, director_read))
    return expanded[:target]


def choose_target_shot_count(beats: list[dict[str, str]]) -> int:
    if len(beats) <= 2:
        return 6
    if len(beats) <= 5:
        return 8
    return min(12, max(8, len(beats)))


def make_coverage_beat(base: dict[str, str], index: int, project: Project, director_read: dict[str, str]) -> dict[str, str]:
    role_cycle = ["reaction 反应", "insert 插入", "movement_result 动作结果", "hook 钩子"]
    role = role_cycle[(index - 1) % len(role_cycle)]
    focus = base.get("characters 相关角色") or first_character(project).get("character_name 角色名", "主角")
    visible = base.get("visible_action 可见动作", "角色保持原文动作后的姿态")
    if role.startswith("reaction"):
        action, hint = f"{focus}听完上一句后停顿半秒，视线没有离开对方，呼吸压低", "reaction_shot 反应镜头"
    elif role.startswith("insert"):
        prop = first_prop_name(project) or "关键道具"
        action, hint = f"{prop}在画面前景停住，角色手指收紧，承接原文动作：{visible}", "insert_shot 插入镜头"
    elif role.startswith("movement_result"):
        action, hint = f"动作结果落在角色站位变化上：{visible}之后，双方距离被重新拉开", "movement_result 运动结果"
    else:
        action, hint = f"镜头停在{focus}未说出口的反应上，为下一段保留悬念", "hook_shot 结尾钩子"
    return {
        **base,
        "beat_id 节拍编号": f"B{index:03d}",
        "visible_action 可见动作": action,
        "dialogue 对白": "无",
        "emotion_shift 情绪变化": director_read.get("scene_turn 场景转折", base.get("emotion_shift 情绪变化", "情绪压力延续")),
        "subtext 潜台词": director_read.get("subtext 潜台词", base.get("subtext 潜台词", "动作背后保留未说破的态度")),
        "shot_hint 镜头建议": hint,
        "coverage_role 覆盖功能": role,
    }


def detect_scene_hint(unit: str, project: Project) -> str:
    for scene in project.scenes:
        name = scene.get("scene_name 场景名", "")
        sid = scene.get("scene_id 场景编号", "")
        if name and name in unit:
            return f"{sid} / {name}"
    for word in SCENE_WORDS:
        if word in unit:
            return word
    return first_scene(project).get("scene_id 场景编号", "SCENE_01")


def detect_beat_characters(unit: str, project: Project) -> list[str]:
    names: list[str] = []
    for char in project.characters:
        name = char.get("character_name 角色名", "")
        cid = char.get("character_id 角色编号", "")
        if (name and name in unit) or (cid and cid in unit):
            names.append(name or cid)
    return names[:4]


def choose_scene_for_beat(project: Project, beat: dict[str, str]) -> dict[str, Any]:
    hint = beat.get("scene_hint 场景建议", "") + beat.get("source_quote 原文证据", "")
    for scene in project.scenes:
        if scene.get("scene_id 场景编号", "") in hint or scene.get("scene_name 场景名", "") in hint:
            return scene
    return first_scene(project)


def choose_shot_characters(project: Project, beat: dict[str, str], index: int) -> list[dict[str, Any]]:
    if not project.characters:
        return [first_character(project)]
    text = " ".join([beat.get("characters 相关角色", ""), beat.get("source_quote 原文证据", ""), beat.get("visible_action 可见动作", ""), beat.get("dialogue 对白", "")])
    matched = [c for c in project.characters if c.get("character_name 角色名", "") and c.get("character_name 角色名", "") in text]
    if matched:
        return matched[:3]
    hint = beat.get("shot_hint 镜头建议", "")
    if "master" in hint or "movement" in hint:
        return project.characters[:3]
    if "shot_b" in hint and len(project.characters) > 1:
        return [project.characters[1]]
    return [project.characters[0]]


def build_director_read(text: str, scene: dict[str, Any], char_a: dict[str, Any], char_b: dict[str, Any]) -> dict[str, str]:
    units = split_source_units(text)
    conflict_hits = find_terms(text, CONFLICT_WORDS)
    turn_hits = find_terms(text, TURN_WORDS)
    power_hits = find_terms(text, POWER_WORDS)
    subtext_hits = find_terms(text, SUBTEXT_WORDS)
    dialogue_samples = extract_dialogue_samples(text)
    char_a_name = char_a.get("character_name 角色名", "A")
    char_b_name = char_b.get("character_name 角色名", "B")
    scene_function = infer_scene_function(conflict_hits, dialogue_samples, units)
    scene_turn = infer_scene_turn(turn_hits, conflict_hits, char_a_name)
    power_shift = infer_power_shift(power_hits, conflict_hits, char_a_name, char_b_name)
    subtext = infer_subtext(subtext_hits, dialogue_samples, char_a_name)
    return {
        "source_basis 原文依据": join_evidence(units[:3]),
        "conflict_terms 冲突词": "、".join(conflict_hits) if conflict_hits else "未发现强冲突词，按低强度关系压力处理",
        "dialogue_basis 对白依据": " / ".join(dialogue_samples[:3]) if dialogue_samples else "原文未发现明确引号对白，按动作与叙述推断",
        "relationship_basis 角色关系依据": "、".join(power_hits) if power_hits else f"根据{char_a_name}与{char_b_name}的对位关系推断",
        "scene_function 场景功能": scene_function,
        "scene_function_evidence 场景功能证据": find_best_sentence(units, conflict_hits or CONFLICT_WORDS),
        "scene_turn 场景转折": scene_turn,
        "scene_turn_evidence 场景转折证据": find_best_sentence(units, turn_hits or TURN_WORDS),
        "pov_empathy 观众视角与共情位置": f"观众优先贴近{char_a_name}，通过其停顿、动作和反应理解压力来源",
        "power_shift 权力变化": power_shift,
        "power_shift_evidence 权力变化证据": find_best_sentence(units, power_hits or POWER_WORDS),
        "subtext 潜台词": subtext,
        "subtext_evidence 潜台词证据": find_best_sentence(units, subtext_hits or SUBTEXT_WORDS),
        "director_intent 导演意图": infer_director_intent(scene_function, scene_turn, subtext),
        "directorial_voice 导演声音": "克制写实、少运镜、重表演动作、重环境声；所有镜头必须服务原文证据链",
        "director_read_confidence 导演读本置信度": infer_director_confidence(conflict_hits, turn_hits, dialogue_samples),
    }


def make_shot(shot_id: str, beat: dict[str, str], scene: dict[str, Any], chars: list[dict[str, Any]], index: int, director_read: dict[str, str], project: Project, previous_shot: dict[str, Any] | None = None) -> dict[str, Any]:
    purpose = beat.get("shot_hint 镜头建议", "reaction_shot 反应镜头")
    camera = choose_camera(purpose)
    dialogue = beat.get("dialogue 对白", "无")
    focus = chars[0]
    visible_action = clean_action(beat.get("visible_action 可见动作", ""), beat)
    evidence = build_source_evidence(project.data.get("source_text 原文", ""), index, visible_action, dialogue, "无", beat)
    shot: dict[str, Any] = {
        "shot_id 镜头编号": shot_id,
        "beat_id 节拍编号": beat.get("beat_id 节拍编号", f"B{index:03d}"),
        "clip_id 单段编号": "CLIP01",
        "shot_purpose 镜头目的": purpose,
        "scene_id 场景编号": scene.get("scene_id 场景编号", "SCENE_01"),
        "location_name 场景名称": scene.get("scene_name 场景名", "主场景"),
        "source_text_ref 原文引用位置": evidence["source_text_ref 原文引用位置"],
        "evidence_quote 原文证据句": evidence["evidence_quote 原文证据句"],
        "adaptation_note 改编说明": evidence["adaptation_note 改编说明"],
        "invented_flag 是否AI补充": evidence["invented_flag 是否AI补充"],
        "source_confidence 原文置信度": evidence["source_confidence 原文置信度"],
        "unknown_policy 不确定处理规则": "不确定内容必须标注为导演补足，禁止伪装成原文事实",
        "source_quote 原文节拍证据": beat.get("source_quote 原文证据", ""),
        "scene_hint 场景建议": beat.get("scene_hint 场景建议", ""),
        "characters 相关角色": beat.get("characters 相关角色", ""),
        "scene_function 场景功能": director_read["scene_function 场景功能"],
        "scene_turn 场景转折": beat.get("emotion_shift 情绪变化", director_read["scene_turn 场景转折"]),
        "pov_empathy 观众视角与共情位置": director_read["pov_empathy 观众视角与共情位置"],
        "power_shift 权力变化": beat.get("power_shift 权力变化", director_read["power_shift 权力变化"]),
        "subtext 潜台词": beat.get("subtext 潜台词", director_read["subtext 潜台词"]),
        "director_intent 导演意图": director_read["director_intent 导演意图"],
        "felt_intent 观众感受目标": beat.get("emotion_shift 情绪变化", "观众能看懂本镜头的态度变化"),
        "on_screen_characters 在场人物": [c.get("character_id 角色编号", "CHAR_A") for c in chars],
        "focus_character 画面主体": focus.get("character_id 角色编号", "CHAR_A"),
        "speaker_mode 发声模式": "spoken_dialogue 出口对白" if dialogue != "无" else "none 无",
        "speaker_spatial_anchor 说话人空间锚点": focus.get("spatial_anchor 空间锚点", "画面左侧") + "，" + focus.get("clothing_lock 服装锁定", "固定服装"),
        "mouth_state 嘴型状态": "speaker_open 说话人开口" if dialogue != "无" else "all_closed 全员闭口",
        "dialogue_line 出口对白": dialogue,
        "os_line 画外音": "无",
        "aspect_ratio 画幅比例": "16:9 横屏",
        "character_symbols 人物符号": "A○=主角，B○=对手，C○=第三人，P1=关键道具，▣=摄影机",
        "shot_size 景别": choose_shot_size(index, purpose, previous_shot),
        "camera_angle 机位角度": choose_camera_angle(purpose, len(chars)),
        "camera_movement 机位运动": camera,
        "camera_axis 轴线方向": "主冲突人物连线，摄影机保持同侧；三人以上先建立空间",
        "screen_direction 画面方向": choose_screen_direction(chars, purpose),
        "layer_depth 前中后景": build_layer_depth(scene),
        "prop_anchor 道具锚点": build_prop_anchor(project, focus, visible_action),
        "movement_arrow 运动箭头": build_movement_arrow_from_beat(beat, purpose),
        "camera_arrow 镜头箭头": build_camera_arrow(camera),
        "motion_path 运动轨迹": build_movement_arrow_from_beat(beat, purpose),
        "entry_pose 起始姿态": build_entry_pose(beat, previous_shot),
        "exit_pose 结束姿态": build_exit_pose(beat),
        "action_detail 动作细节": visible_action,
        "performance_action 表演动作": visible_action,
        "this_clip_only 本段只拍": visible_action,
        "reserved_for_later 后续保留": "后续反转、升级冲突或新场景，不在本镜提前完成",
        "planned_start_state 计划起始状态": build_entry_pose(beat, previous_shot),
        "planned_end_state 计划结束状态": build_exit_pose(beat),
        "observed_end_state 实际生成结尾状态": "待用户回填",
        "continuity_locks 连续性锁定": "同脸、同发型、同服装、同道具、同站位逻辑",
        "allowed_changes 允许变化": "只允许表情、手部小动作、光线轻微变化",
        "retake_variable 本次返修变量": "none 未返修；返修时一次只改一个变量",
        "fallback_shot 备用镜头": build_fallback_shot(beat, purpose),
        "motion_grid_ascii 动作拆解六宫格": "",
    }
    shot["sketch_ascii 简笔手绘图"] = build_sketch(shot)
    if is_high_risk_shot(shot):
        shot["motion_grid_ascii 动作拆解六宫格"] = build_motion_grid_ascii(shot)
    return shot


def clean_action(action: str, beat: dict[str, str]) -> str:
    value = action.strip()
    if not value or any(bad in value for bad in BANNED_PLACEHOLDERS):
        value = beat.get("source_quote 原文证据", "").strip()[:70]
    return value or "角色在画面中保持可见姿态，等待用户补充原文动作"


def choose_camera(purpose: str) -> str:
    if "shot_" in purpose:
        return "slow_push_in 缓慢推进"
    if "movement" in purpose or "insert" in purpose:
        return "slight_lateral_move 轻微横移"
    return "fixed_camera 固定机位"


def choose_shot_size(index: int, purpose: str, previous_shot: dict[str, Any] | None) -> str:
    preferred = "全景 WS" if "master" in purpose else "特写 ECU" if "insert" in purpose else "中景 MS" if "movement" in purpose else "近景 CU" if "shot_" in purpose else "中近景 MCU"
    if previous_shot and size_group(previous_shot.get("shot_size 景别", "")) == size_group(preferred):
        for alt in ["全景 WS", "中景 MS", "中近景 MCU", "近景 CU", "特写 ECU"]:
            if size_group(alt) != size_group(preferred) and size_group(alt) != size_group(previous_shot.get("shot_size 景别", "")):
                return alt
    return preferred


def choose_camera_angle(purpose: str, char_count: int = 1) -> str:
    if char_count >= 3:
        return "轴线同侧，中景或全景建立三人空间"
    if "shot_a" in purpose or "shot_b" in purpose:
        return "轴线同侧，侧前方约30度"
    if "insert" in purpose:
        return "固定特写，略低角度贴近手部或道具"
    if "movement" in purpose:
        return "轴线同侧，斜45度保留动作方向"
    return "轴线同侧，正侧之间保留空间关系"


def choose_screen_direction(chars: list[dict[str, Any]], purpose: str) -> str:
    if len(chars) >= 3:
        return "A在左，B在右，C在后景或中间；主冲突A-B保持同侧轴线，C不抢主体"
    if "shot_b" in purpose:
        return "B在画面右侧或中右，视线<-；A保持画外左侧方向，不跳轴"
    if "insert" in purpose:
        return "道具或手部位于画面中部，动作方向沿上一镜视线轴线延续"
    return "A在画面左侧，B在画面右侧；A视线->，B视线<-；保持同侧轴线，不跳轴"


def build_sketch(shot_or_purpose: Any, aspect_ratio: str | None = None) -> str:
    if not isinstance(shot_or_purpose, dict):
        return "frame / 画框：16:9 横屏\n+--------------------------------------+\n| FG 前景：遮挡/环境边缘               |\n| MG 中景：A○ 左/中                    |\n| BG 背景：主场景固定物件              |\n| camera 摄影机：▣ 固定不动            |\n+--------------------------------------+"
    shot = shot_or_purpose
    return f"""frame / 画框：{shot.get('aspect_ratio 画幅比例', '16:9 横屏')}；shot_size / 景别：{shot.get('shot_size 景别', '')}
+--------------------------------------+
| FG 前景：{extract_depth_part(shot.get('layer_depth 前中后景', ''), 'FG')} |
|                                      |
| MG 中景：{build_character_line(shot)} |
| 方向：{shorten(shot.get('screen_direction 画面方向', ''), 30)} |
| 动作：{shorten(shot.get('movement_arrow 运动箭头', ''), 30)} |
|                                      |
| BG 背景：{extract_depth_part(shot.get('layer_depth 前中后景', ''), 'BG')} |
| {shorten(shot.get('camera_arrow 镜头箭头', ''), 36)} |
| prop / 道具：{shorten(shot.get('prop_anchor 道具锚点', ''), 26)} |
+--------------------------------------+"""


def build_character_line(shot: dict[str, Any]) -> str:
    chars = shot.get("on_screen_characters 在场人物", [])
    if len(chars) >= 3:
        return "A○ 左侧   C○ 中/后景   ○B 右侧"
    if len(chars) >= 2:
        return "A○ 左侧        ○B 右侧"
    if shot.get("focus_character 画面主体", "") == "CHAR_B":
        return "             ○B 右/中"
    return "A○ 左/中"


def build_source_evidence(text: str, index: int, action: str, dialogue: str, os_line: str, beat: dict[str, str] | None = None) -> dict[str, str]:
    clean = " ".join(text.split())
    target = dialogue if dialogue != "无" else os_line if os_line != "无" else ""
    if target and target in clean:
        pos = clean.find(target)
        start = max(0, pos - 30)
        end = min(len(clean), pos + len(target) + 30)
        return {"source_text_ref 原文引用位置": f"char:{pos}-{pos + len(target)}", "evidence_quote 原文证据句": clean[start:end], "adaptation_note 改编说明": "对白或旁白来自原文，镜头调度为导演拆解", "invented_flag 是否AI补充": "source_supported 原文支持", "source_confidence 原文置信度": "high 高"}
    if beat and beat.get("source_quote 原文证据"):
        quote = beat["source_quote 原文证据"]
        return {"source_text_ref 原文引用位置": beat.get("beat_id 节拍编号", f"approx_shot:{index}"), "evidence_quote 原文证据句": quote[:140], "adaptation_note 改编说明": "镜头动作基于该节拍可拍化处理", "invented_flag 是否AI补充": "source_supported 原文支持", "source_confidence 原文置信度": "medium 中"}
    quote = clean[:120] if clean else "无原文"
    return {"source_text_ref 原文引用位置": f"approx_shot:{index}", "evidence_quote 原文证据句": quote, "adaptation_note 改编说明": f"{action} 为导演调度补足，需用户确认是否符合原文", "invented_flag 是否AI补充": "director_bridge 导演补足", "source_confidence 原文置信度": "medium 中" if quote != "无原文" else "low 低"}


def build_layer_depth(scene: dict[str, Any]) -> str:
    scene_name = scene.get("scene_name 场景名", "主场景")
    return f"FG前景：门框/阴影/遮挡；MG中景：角色调度区；BG背景：{scene_name}固定物件"


def build_prop_anchor(project: Project, focus_character: dict[str, Any], action: str) -> str:
    prop = first_prop_name(project) or "P1关键道具"
    owner = focus_character.get("character_name 角色名", "画面主体")
    if any(word in action for word in PROP_WORDS + ["手", "握"]):
        return f"{prop}：由{owner}持有或贴近手部区域，可小幅移动，不可消失"
    return f"{prop}：保持在场景固定位置或角色身上，不抢主体，不突然消失"


def build_movement_arrow(purpose_or_beat: Any) -> str:
    if isinstance(purpose_or_beat, dict):
        return build_movement_arrow_from_beat(purpose_or_beat, purpose_or_beat.get("shot_hint 镜头建议", ""))
    purpose = str(purpose_or_beat)
    if "movement" in purpose:
        return "起点：A左侧或中景位置 -> 结果：动作后停在画面中部"
    if "insert" in purpose:
        return "局部动作：手部/道具静止 -> 收紧或触碰 -> 停顿"
    if "shot_b" in purpose:
        return "无大位移；B的视线从画面右侧压回左侧"
    return "无大位移；角色通过视线、手部和呼吸完成态度变化"


def build_movement_arrow_from_beat(beat: dict[str, str], purpose: str) -> str:
    action = beat.get("visible_action 可见动作", "")
    if "movement" in purpose:
        return f"起点：A左侧或中景位置 -> 结果：动作后停在画面中部；依据动作：{action[:50]}"
    if "insert" in purpose:
        return f"局部动作：手部/道具静止 -> 收紧或触碰 -> 停顿；依据动作：{action[:50]}"
    if "shot_b" in purpose:
        return "无大位移；B的视线从画面右侧压回左侧"
    return "无大位移；角色通过视线、手部和呼吸完成态度变化"


def build_camera_arrow(camera: str) -> str:
    if camera == "slow_push_in 缓慢推进":
        return "camera 摄影机：▣ 向前轻推，不改变轴线"
    if camera == "slight_lateral_move 轻微横移":
        return "camera 摄影机：▣ 左右轻微横移，不跨轴线"
    if camera == "subtle_handheld 轻微手持":
        return "camera 摄影机：▣ 轻微手持，主体稳定"
    return "camera 摄影机：▣ 固定不动"


def build_motion_grid_ascii(purpose_or_shot: Any) -> str:
    action = purpose_or_shot.get("action_detail 动作细节", "本镜动作") if isinstance(purpose_or_shot, dict) else str(purpose_or_shot)
    return f"""+------------+------------+------------+
| 1 起势      | 2 接近      | 3 接触/停顿  |
| A○ 准备     | A○ ---> 目标 | 动作核心     |
| {shorten(action, 8):<8} | 保持轴线     | 道具不消失   |
+------------+------------+------------+
| 4 结果      | 5 反应      | 6 收束      |
| 位置变化     | 对方停顿     | A○ 保持     |
| ▣ 中景      | ▣ 近景      | ▣ 固定      |
+------------+------------+------------+"""


def is_high_risk_purpose(purpose: str) -> bool:
    return any(word in purpose for word in ["movement", "insert", "运动", "result", "动作", "道具"])


def is_high_risk_shot(shot: dict[str, Any]) -> bool:
    purpose = shot.get("shot_purpose 镜头目的", "")
    action = shot.get("action_detail 动作细节", "")
    return is_high_risk_purpose(purpose) or any(word in action for word in CONFLICT_WORDS + PROP_WORDS)


def first_dialogue(text: str) -> str:
    samples = extract_dialogue_samples(text)
    return samples[0] if samples else ""


def extract_visible_action(unit: str, dialogue: str) -> str:
    stripped = unit.strip()
    without_dialogue = stripped.replace(dialogue, "") if dialogue else stripped
    for candidate in split_action_phrases(without_dialogue):
        if has_action_signal(candidate):
            return candidate[:80]
    if dialogue:
        return f"说话人说出“{dialogue[:24]}”前后，视线停在对方身上，手部动作保持可见"
    return f"画面呈现原文状态：{stripped[:60]}"


def split_source_units(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[。！？!?；;])", cleaned)
    return [p.strip() for p in parts if p.strip()] or [cleaned[:160]]


def extract_dialogue_samples(text: str) -> list[str]:
    samples = re.findall(r"[“\"]([^”\"]{1,80})[”\"]", text)
    if samples:
        return samples[:5]
    colon_samples = re.findall(r"[:：]\s*([^。！？!?\n]{1,80})", text)
    return [s.strip() for s in colon_samples if s.strip()][:5]


def split_action_phrases(text: str) -> list[str]:
    parts = re.split(r"[，,。！？!?；;、]", text)
    return [p.strip(" ：:”“\" ") for p in parts if p.strip(" ：:”“\" ")]


def has_action_signal(text: str) -> bool:
    return any(word in text for word in TURN_WORDS + CONFLICT_WORDS + SUBTEXT_WORDS + PROP_WORDS)


def find_terms(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    for term in terms:
        if term in text and term not in hits:
            hits.append(term)
    return hits[:8]


def find_best_sentence(units: list[str], terms: list[str]) -> str:
    if not units:
        return "无原文证据，必须人工确认"
    for unit in units:
        if any(term in unit for term in terms):
            return unit[:140]
    return units[0][:140]


def join_evidence(units: list[str]) -> str:
    return " / ".join(unit[:90] for unit in units) if units else "无原文段落依据，必须人工确认"


def infer_scene_function(conflicts: list[str], dialogues: list[str], units: list[str]) -> str:
    if conflicts and dialogues:
        return "通过对白交锋和冲突词建立人物压力，并把原文推进为可拍的对峙场面"
    if conflicts:
        return "通过动作或叙述中的冲突词建立危险处境，推动角色做出选择"
    if dialogues:
        return "通过对白暴露人物关系和信息差，建立下一步行动理由"
    return "把原文段落压缩为一个明确的场景任务，服务后续镜头连续性"


def infer_scene_turn(turns: list[str], conflicts: list[str], char_a_name: str) -> str:
    if turns:
        return f"转折来自“{'、'.join(turns[:3])}”：场面从静态信息进入可见动作或态度变化"
    if conflicts:
        return f"转折来自冲突压力升级：{char_a_name}必须从被动承受转为做出反应"
    return f"转折来自{char_a_name}的状态变化：从观察进入表达或行动"


def infer_power_shift(power_terms: list[str], conflicts: list[str], char_a_name: str, char_b_name: str) -> str:
    if any(term in power_terms for term in ["大人", "将军", "镖头", "掌门", "师父", "官", "王", "帝女"]):
        return f"权力起初由身份或地位更高的一方掌握，随后通过{char_a_name}的动作、沉默或对白出现反向牵制"
    if conflicts:
        return f"权力起初由施压者掌握，随后{char_a_name}用可见反应打断压迫节奏"
    return f"{char_a_name}与{char_b_name}的权力关系尚不明确，按试探关系处理，需用户确认"


def infer_subtext(subtext_terms: list[str], dialogues: list[str], char_a_name: str) -> str:
    if subtext_terms:
        return f"潜台词来自“{'、'.join(subtext_terms[:3])}”：人物真正的态度藏在停顿、眼神、手部动作和沉默里"
    if dialogues:
        return "对白表面传递信息，真实重点是说话人的底气、迟疑或试探"
    return f"{char_a_name}表面行动简单，潜台词应由身体姿态、视线和环境声承担"


def infer_director_intent(scene_function: str, scene_turn: str, subtext: str) -> str:
    return f"让观众先看懂压力来源，再看见转折发生；镜头、声音和动作都服务于：{scene_turn}。潜台词处理：{subtext}"


def infer_director_confidence(conflicts: list[str], turns: list[str], dialogues: list[str]) -> str:
    score = len(conflicts) + len(turns) + len(dialogues)
    if score >= 5:
        return "high 高：原文冲突、转折和对白证据较充分"
    if score >= 2:
        return "medium 中：有部分原文证据，导演补足需人工确认"
    return "low 低：原文证据不足，必须人工确认导演读本"


def infer_beat_power(unit: str, project: Project) -> str:
    hits = find_terms(unit, POWER_WORDS)
    char_a = first_character(project).get("character_name 角色名", "主角")
    char_b = project.characters[1].get("character_name 角色名", "对手") if len(project.characters) > 1 else "对手"
    if hits:
        return f"权力依据：{','.join(hits[:3])}；{char_a}与{char_b}的强弱关系在本节拍发生可见变化"
    if find_terms(unit, CONFLICT_WORDS):
        return f"施压者暂时占上风，{char_a}通过反应动作争回主动"
    return f"{char_a}与{char_b}保持试探关系，权力未完全揭开"


def infer_beat_subtext(unit: str, dialogue: str) -> str:
    hits = find_terms(unit, SUBTEXT_WORDS)
    if hits:
        return f"潜台词来自{','.join(hits[:3])}，真实态度藏在停顿、视线和手部动作里"
    if dialogue:
        return "对白表面传递信息，镜头重点放在说话前后的迟疑、压迫或底气"
    return "没有明确对白时，潜台词由身体姿态、环境声和停顿承担"


def infer_emotion_shift(unit: str, conflict: str, turn: str) -> str:
    if turn != "状态推进":
        return f"从压住情绪转向可见反应，触发词：{turn}"
    if conflict.startswith("关系压力较低"):
        return "从观察状态转为轻微警觉，情绪变化保持克制"
    return f"从被动承受转为准备反击，冲突依据：{conflict}"


def choose_shot_hint(index: int, unit: str, dialogue: str, visible_action: str) -> str:
    if index == 1:
        return "master_shot 主镜头"
    if dialogue:
        return "shot_a A正打" if index % 2 == 0 else "shot_b B反打"
    if any(word in visible_action for word in PROP_WORDS):
        return "insert_shot 插入镜头"
    if find_terms(unit, CONFLICT_WORDS + TURN_WORDS):
        return "movement_result 运动结果"
    return "reaction_shot 反应镜头"


def build_entry_pose(beat: dict[str, str], previous_shot: dict[str, Any] | None) -> str:
    if previous_shot:
        return f"承接上一镜结果：{previous_shot.get('planned_end_state 计划结束状态', '')[:60]}"
    return f"以原文节拍开场：{beat.get('source_quote 原文证据', '')[:60]}"


def build_exit_pose(beat: dict[str, str]) -> str:
    return f"停在本节拍变化后：{beat.get('emotion_shift 情绪变化', '')[:70]}"


def build_fallback_shot(beat: dict[str, str], purpose: str) -> str:
    if "shot_" in purpose:
        return "改为过肩近景，保留说话人嘴型和对方画外方向"
    if "insert" in purpose:
        return "改为手部或道具静态特写，减少复杂接触"
    return f"改为反应镜头，保留原文证据：{beat.get('source_quote 原文证据', '')[:50]}"


def choose_storyboard_layout(shot_count: int) -> str:
    if shot_count <= 8:
        return "2x4 八宫格"
    if shot_count == 9:
        return "3x3 九宫格"
    return "3x4 十二宫格"


def build_storyboard_grid_ascii(shots: list[dict[str, Any]]) -> str:
    layout = choose_storyboard_layout(len(shots))
    cols = 4 if layout.startswith("2x4") or layout.startswith("3x4") else 3
    rows = (len(shots) + cols - 1) // cols
    cell_w = 18
    lines: list[str] = [f"storyboard_layout 分镜总览布局：{layout}"]
    border = "+" + "+".join("-" * cell_w for _ in range(cols)) + "+"
    for row in range(rows):
        lines.append(border)
        chunk = shots[row * cols:(row + 1) * cols]
        for field in ["shot_id 镜头编号", "beat_id 节拍编号", "scene_id 场景编号"]:
            cells = [f" {shorten(str(shot.get(field, '')), cell_w - 2):<{cell_w - 2}} " for shot in chunk]
            while len(cells) < cols:
                cells.append(" " * cell_w)
            lines.append("|" + "|".join(cells) + "|")
    lines.append(border)
    return "\n".join(lines)


def build_dialogue_coverage_ascii(shots: list[dict[str, Any]]) -> str:
    has_a = any("shot_a" in s.get("shot_purpose 镜头目的", "") for s in shots)
    has_b = any("shot_b" in s.get("shot_purpose 镜头目的", "") for s in shots)
    if not (has_a and has_b):
        return "双人正反打不足：按当前原文对白密度处理，需人工确认是否增加对白覆盖。"
    return "+------------------+------------------+------------------+\n| MASTER 主镜头     | A 正打 shot_a     | B 反打 shot_b     |\n| A○      ○B        | A○ -> B闭口       | A闭口 <- ○B       |\n| 建立轴线不跳轴     | A开口，B画外方向   | B开口，A画外方向   |\n+------------------+------------------+------------------+"


def build_state_capsule(project: Project, director_read: dict[str, str]) -> dict[str, Any]:
    return {"accepted_clip 已接受片段": "none 尚未生成", "observed_start_state 实际起始状态": "待用户回填", "observed_end_state 实际结束状态": "待用户回填", "character_state 角色状态": [c.get("character_name 角色名", "") for c in project.characters], "scene_state 场景状态": [s.get("scene_name 场景名", "") for s in project.scenes], "prop_state 道具状态": [p.get("prop_name 道具名", "") for p in project.props], "director_intent 导演意图": director_read["director_intent 导演意图"], "next_clip_task 下一段任务": "先生成本段，用户确认实际结尾后再写下一段"}


def build_producer_plan(project: Project) -> dict[str, Any]:
    return {"production_scope 制作范围": "默认按原文密度生成6-12镜；原文薄时不强撑60-90秒", "episode_goal 本集目标": "把原文拆成可生成视频的导演物料包，不直接交付成片", "duration_plan 时长计划": "每镜约4-8秒；对白少时压缩时长，避免空镜头水时长", "clip_plan 分段计划": "默认先做CLIP01；下一段必须基于用户确认的实际结尾继续", "asset_checklist 素材清单": ["角色三视图或脸部参考", "主场景概念图", "关键道具图", "首帧图或上一段末帧"], "platform_plan 平台生成计划": "先输出通用提示词，再按即梦、可灵、LibTV、ComfyUI等平台适配", "risk_log 风险记录": ["人物一致性", "口型误开", "动作崩坏", "场景跳变", "声音与对白冲突"], "approval_gates 审批节点": ["确认原文覆盖", "确认资产锁", "确认分镜", "确认提示词", "确认实际生成结尾"], "retake_budget 返修预算": "每个关键镜头优先2-3次；每次只改一个变量", "cost_note 成本备注": "高风险动作镜头先低成本测试，不直接批量生成"}


def build_approval_gates() -> dict[str, str]:
    return {"script_approved 剧本已确认": "pending 待确认", "assets_approved 资产已确认": "pending 待确认", "storyboard_approved 分镜已确认": "pending 待确认", "prompts_approved 提示词已确认": "pending 待确认", "export_approved 导出已确认": "pending 待确认"}


def size_group(value: str) -> str:
    if "全景" in value or "WS" in value:
        return "wide"
    if "中景" in value or "MS" in value:
        return "medium"
    if "近景" in value or "CU" in value:
        return "close"
    if "特写" in value or "ECU" in value:
        return "detail"
    return value


def first_scene(project: Project) -> dict[str, Any]:
    return project.scenes[0] if project.scenes else {"scene_id 场景编号": "SCENE_01", "scene_name 场景名": "主场景"}


def first_character(project: Project) -> dict[str, Any]:
    return project.characters[0] if project.characters else {"character_id 角色编号": "CHAR_A", "character_name 角色名": "主角", "spatial_anchor 空间锚点": "画面左侧", "clothing_lock 服装锁定": "固定服装"}


def first_prop_name(project: Project) -> str:
    for prop in project.props:
        name = prop.get("prop_name 道具名", "")
        if name:
            return name
    return ""


def extract_depth_part(text: str, marker: str) -> str:
    for part in text.split("；"):
        if part.startswith(marker):
            return part.split("：", 1)[-1][:14]
    return text[:14] or "固定空间参照"


def shorten(value: str, max_len: int) -> str:
    return value if len(value) <= max_len else value[: max_len - 1] + "…"
