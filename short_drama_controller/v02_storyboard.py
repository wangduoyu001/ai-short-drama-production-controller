from __future__ import annotations

import re
from typing import Any

from .v02_dialogue import force_reverse_shot_units
from .v02_models import Project

ALLOWED_CAMERA = {
    "fixed_camera 固定机位",
    "slow_push_in 缓慢推进",
    "slight_lateral_move 轻微横移",
    "subtle_handheld 轻微手持",
}

CONFLICT_WORDS = [
    "杀", "死", "逃", "追", "逼", "威胁", "怒", "喝", "跪", "押", "围", "断", "血", "伤",
    "不许", "不能", "偏要", "拒绝", "护送", "灭世", "仇", "恨", "夺", "抢", "欺",
]
TURN_WORDS = ["突然", "却", "但", "然而", "终于", "转身", "没有回头", "停下", "抬头", "拔", "握", "沉默", "冷笑"]
POWER_WORDS = ["大人", "将军", "镖头", "掌门", "师父", "官", "王", "帝女", "少年", "少女", "众人", "跪", "押", "围"]
SUBTEXT_WORDS = ["沉默", "低声", "冷笑", "没有回头", "看着", "盯着", "握", "停顿", "颤", "咬牙"]


def build_shots(project: Project) -> None:
    scene = project.scenes[0]
    char_a = project.characters[0]
    char_b = project.characters[1] if len(project.characters) > 1 else project.characters[0]
    director_read = build_director_read(project.data.get("source_text 原文", ""), scene, char_a, char_b)
    project.data["director_read 导演读本"] = director_read
    project.data["project_state_capsule 项目状态胶囊"] = build_state_capsule(project, director_read)
    project.data["producer_plan 制片执行计划"] = build_producer_plan(project)
    project.data["approval_gates 确认闸门"] = build_approval_gates()

    units = force_reverse_shot_units(project.data.get("dialogue_lines 对白列表", []))
    shots = [make_shot("SH001", "master_shot 主镜头", scene, [char_a, char_b], "建立空间和轴线", "无", "无", 1, director_read, project)]

    for unit in units[:5]:
        speaker = char_a if unit["speaker_name 说话人"] in [char_a["character_name 角色名"], "主角"] else char_b
        purpose = "shot_a A正打" if speaker == char_a else "shot_b B反打"
        shots.append(make_shot(
            f"SH{len(shots)+1:03d}", purpose, scene, [speaker],
            f"{speaker['character_name 角色名']}发声或保持闭口",
            unit["dialogue_line 出口对白"], unit["os_line 画外音"], len(shots)+1, director_read, project,
        ))
        if len(shots) == 4:
            shots.append(make_shot("SH005", "insert_shot 插入镜头", scene, [char_a], "手部或道具特写", "无", "无", 5, director_read, project))

    while len(shots) < 8:
        if len(shots) == 6:
            purpose = "movement_result 运动结果"
            chars = [char_a, char_b]
        elif len(shots) < 7:
            purpose = "reaction_shot 反应镜头"
            chars = [char_b]
        else:
            purpose = "hook_shot 结尾钩子"
            chars = [char_a]
        shots.append(make_shot(f"SH{len(shots)+1:03d}", purpose, scene, chars, "情绪或动作推进", "无", "无", len(shots)+1, director_read, project))

    shots = shots[:12]
    project.data["blocking_plan 人物调度计划"] = {
        "axis_line 轴线": "CHAR_A与CHAR_B连线",
        "safe_camera_zone 安全机位区": "摄影机保持在轴线同侧",
        "eyeline_a A视线方向": "A看向画面右",
        "eyeline_b B视线方向": "B看向画面左",
    }
    project.data["shots 分镜列表"] = shots
    project.data["storyboard_layout 分镜总览布局"] = choose_storyboard_layout(len(shots))
    project.data["storyboard_grid_ascii 分镜总览简笔图"] = build_storyboard_grid_ascii(shots)
    project.data["dialogue_coverage_ascii 对白覆盖图"] = build_dialogue_coverage_ascii(shots)


def build_director_read(text: str, scene: dict[str, Any], char_a: dict[str, Any], char_b: dict[str, Any]) -> dict[str, str]:
    units = split_source_units(text)
    conflict_hits = find_terms(text, CONFLICT_WORDS)
    turn_hits = find_terms(text, TURN_WORDS)
    power_hits = find_terms(text, POWER_WORDS)
    subtext_hits = find_terms(text, SUBTEXT_WORDS)
    dialogue_samples = extract_dialogue_samples(text)
    char_a_name = char_a.get("character_name 角色名", "A")
    char_b_name = char_b.get("character_name 角色名", "B")
    conflict_sentence = find_best_sentence(units, conflict_hits or CONFLICT_WORDS)
    turn_sentence = find_best_sentence(units, turn_hits or TURN_WORDS)
    power_sentence = find_best_sentence(units, power_hits or POWER_WORDS)
    subtext_sentence = find_best_sentence(units, subtext_hits or SUBTEXT_WORDS)

    scene_function = infer_scene_function(conflict_hits, dialogue_samples, units)
    scene_turn = infer_scene_turn(turn_hits, conflict_hits, char_a_name)
    power_shift = infer_power_shift(power_hits, conflict_hits, char_a_name, char_b_name)
    subtext = infer_subtext(subtext_hits, dialogue_samples, char_a_name)
    director_intent = infer_director_intent(scene_function, scene_turn, subtext)

    return {
        "source_basis 原文依据": join_evidence(units[:3]),
        "conflict_terms 冲突词": "、".join(conflict_hits) if conflict_hits else "未发现强冲突词，按低强度关系压力处理",
        "dialogue_basis 对白依据": " / ".join(dialogue_samples[:3]) if dialogue_samples else "原文未发现明确引号对白，按动作与叙述推断",
        "relationship_basis 角色关系依据": "、".join(power_hits) if power_hits else f"根据{char_a_name}与{char_b_name}的对位关系推断",
        "scene_function 场景功能": scene_function,
        "scene_function_evidence 场景功能证据": conflict_sentence,
        "scene_turn 场景转折": scene_turn,
        "scene_turn_evidence 场景转折证据": turn_sentence,
        "pov_empathy 观众视角与共情位置": f"观众优先贴近{char_a_name}，通过其停顿、动作和反应理解压力来源",
        "power_shift 权力变化": power_shift,
        "power_shift_evidence 权力变化证据": power_sentence,
        "subtext 潜台词": subtext,
        "subtext_evidence 潜台词证据": subtext_sentence,
        "director_intent 导演意图": director_intent,
        "directorial_voice 导演声音": "克制写实、少运镜、重表演动作、重环境声；所有镜头必须服务原文证据链",
        "director_read_confidence 导演读本置信度": infer_director_confidence(conflict_hits, turn_hits, dialogue_samples),
    }


def split_source_units(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    parts = re.split(r"(?<=[。！？!?；;])", cleaned)
    units = [p.strip() for p in parts if p.strip()]
    return units or [cleaned[:160]]


def extract_dialogue_samples(text: str) -> list[str]:
    samples = re.findall(r"[“\"]([^”\"]{1,80})[”\"]", text)
    if samples:
        return samples[:5]
    colon_samples = re.findall(r"[:：]\s*([^。！？!?\n]{1,80})", text)
    return [s.strip() for s in colon_samples if s.strip()][:5]


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
    if not units:
        return "无原文段落依据，必须人工确认"
    return " / ".join(unit[:90] for unit in units)


def infer_scene_function(conflicts: list[str], dialogues: list[str], units: list[str]) -> str:
    if conflicts and dialogues:
        return "通过对白交锋和冲突词建立人物压力，并把原文推进为可拍的对峙场面"
    if conflicts:
        return "通过动作或叙述中的冲突词建立危险处境，推动角色做出选择"
    if dialogues:
        return "通过对白暴露人物关系和信息差，建立下一步行动理由"
    if len(units) <= 2:
        return "用短场景建立人物、地点和一个可继续生成的悬念"
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


def build_state_capsule(project: Project, director_read: dict[str, str]) -> dict[str, Any]:
    return {
        "accepted_clip 已接受片段": "none 尚未生成",
        "observed_start_state 实际起始状态": "待用户回填",
        "observed_end_state 实际结束状态": "待用户回填",
        "character_state 角色状态": [c.get("character_name 角色名", "") for c in project.characters],
        "scene_state 场景状态": [s.get("scene_name 场景名", "") for s in project.scenes],
        "prop_state 道具状态": [p.get("prop_name 道具名", "") for p in project.props],
        "director_intent 导演意图": director_read["director_intent 导演意图"],
        "next_clip_task 下一段任务": "先生成本段，用户确认实际结尾后再写下一段",
    }


def build_producer_plan(project: Project) -> dict[str, Any]:
    return {
        "production_scope 制作范围": "60-90秒，8-12镜，2-3个主要角色，1个主场景，先跑通样片流程",
        "episode_goal 本集目标": "把原文拆成可生成视频的导演物料包，不直接交付成片",
        "duration_plan 时长计划": "每镜约4-8秒，复杂动作拆成插入镜头或宫格硬切",
        "clip_plan 分段计划": "默认先做CLIP01；下一段必须基于用户确认的实际结尾继续",
        "asset_checklist 素材清单": ["角色三视图或脸部参考", "主场景概念图", "关键道具图", "首帧图或上一段末帧"],
        "platform_plan 平台生成计划": "先输出通用提示词，再按即梦、可灵、LibTV、ComfyUI等平台适配",
        "risk_log 风险记录": ["人物一致性", "口型误开", "动作崩坏", "场景跳变", "声音与对白冲突"],
        "approval_gates 审批节点": ["确认原文覆盖", "确认资产锁", "确认分镜", "确认提示词", "确认实际生成结尾"],
        "retake_budget 返修预算": "每个关键镜头优先2-3次；每次只改一个变量",
        "cost_note 成本备注": "高风险动作镜头先低成本测试，不直接批量生成",
    }


def build_approval_gates() -> dict[str, str]:
    return {
        "script_approved 剧本已确认": "pending 待确认",
        "assets_approved 资产已确认": "pending 待确认",
        "storyboard_approved 分镜已确认": "pending 待确认",
        "prompts_approved 提示词已确认": "pending 待确认",
        "export_approved 导出已确认": "pending 待确认",
    }


def make_shot(shot_id: str, purpose: str, scene: dict[str, Any], chars: list[dict[str, Any]], action: str, dialogue: str, os_line: str, index: int, director_read: dict[str, str], project: Project) -> dict[str, Any]:
    camera = "slow_push_in 缓慢推进" if "shot_" in purpose else "slight_lateral_move 轻微横移" if "movement" in purpose else "fixed_camera 固定机位"
    if camera not in ALLOWED_CAMERA:
        camera = "fixed_camera 固定机位"
    speaker_mode = "spoken_dialogue 出口对白" if dialogue != "无" else "os_voice OS画外音" if os_line != "无" else "none 无"
    shot_sizes = ["全景 WS", "近景 CU", "近景 CU", "特写 ECU", "中近景 MCU", "近景 CU", "中景 MS", "中近景 MCU"]
    aspect = "16:9 横屏"
    evidence = build_source_evidence(project.data.get("source_text 原文", ""), index, action, dialogue, os_line)
    motion_grid = build_motion_grid_ascii(purpose) if is_high_risk_purpose(purpose) else ""
    entry_pose = "运动或情绪起点明确"
    exit_pose = "运动结果或情绪落点明确"
    return {
        "shot_id 镜头编号": shot_id,
        "clip_id 单段编号": "CLIP01",
        "shot_purpose 镜头目的": purpose,
        "scene_id 场景编号": scene["scene_id 场景编号"],
        "location_name 场景名称": scene["scene_name 场景名"],
        "source_text_ref 原文引用位置": evidence["source_text_ref 原文引用位置"],
        "evidence_quote 原文证据句": evidence["evidence_quote 原文证据句"],
        "adaptation_note 改编说明": evidence["adaptation_note 改编说明"],
        "invented_flag 是否AI补充": evidence["invented_flag 是否AI补充"],
        "source_confidence 原文置信度": evidence["source_confidence 原文置信度"],
        "unknown_policy 不确定处理规则": "不确定内容必须标注为导演补足，禁止伪装成原文事实",
        "scene_function 场景功能": director_read["scene_function 场景功能"],
        "scene_turn 场景转折": director_read["scene_turn 场景转折"],
        "pov_empathy 观众视角与共情位置": director_read["pov_empathy 观众视角与共情位置"],
        "power_shift 权力变化": director_read["power_shift 权力变化"],
        "subtext 潜台词": director_read["subtext 潜台词"],
        "director_intent 导演意图": director_read["director_intent 导演意图"],
        "felt_intent 观众感受目标": "观众能明确感到本镜头推进了压力、选择或立场变化",
        "on_screen_characters 在场人物": [c["character_id 角色编号"] for c in chars],
        "focus_character 画面主体": chars[0]["character_id 角色编号"],
        "speaker_mode 发声模式": speaker_mode,
        "speaker_spatial_anchor 说话人空间锚点": chars[0]["spatial_anchor 空间锚点"] + "，" + chars[0]["clothing_lock 服装锁定"],
        "mouth_state 嘴型状态": "speaker_open 说话人开口" if dialogue != "无" else "all_closed 全员闭口",
        "dialogue_line 出口对白": dialogue,
        "os_line 画外音": os_line,
        "aspect_ratio 画幅比例": aspect,
        "character_symbols 人物符号": "A○=主角，B○=对手，P1=关键道具，▣=摄影机",
        "shot_size 景别": shot_sizes[min(index - 1, len(shot_sizes) - 1)],
        "camera_angle 机位角度": "轴线同侧，侧前方约30度",
        "camera_movement 机位运动": camera,
        "camera_axis 轴线方向": "A-B连线，摄影机在同侧",
        "screen_direction 画面方向": "A在画面左侧，B在画面右侧；A视线->，B视线<-；保持同侧轴线，不跳轴",
        "layer_depth 前中后景": build_layer_depth(scene),
        "prop_anchor 道具锚点": build_prop_anchor(project, chars[0], action),
        "sketch_ascii 简笔手绘图": build_sketch(purpose, aspect),
        "movement_arrow 运动箭头": build_movement_arrow(purpose),
        "camera_arrow 镜头箭头": build_camera_arrow(camera),
        "motion_grid_ascii 动作拆解六宫格": motion_grid,
        "motion_path 运动轨迹": "无大位移；如有运动，只保留起势、特写、结果",
        "entry_pose 起始姿态": entry_pose,
        "exit_pose 结束姿态": exit_pose,
        "action_detail 动作细节": action,
        "performance_action 表演动作": f"用一个可见动作承载潜台词：{action}",
        "this_clip_only 本段只拍": action,
        "reserved_for_later 后续保留": "后续反转、升级冲突或新场景，不在本镜提前完成",
        "planned_start_state 计划起始状态": entry_pose,
        "planned_end_state 计划结束状态": exit_pose,
        "observed_end_state 实际生成结尾状态": "待用户回填",
        "continuity_locks 连续性锁定": "同脸、同发型、同服装、同道具、同站位逻辑",
        "allowed_changes 允许变化": "只允许表情、手部小动作、光线轻微变化",
        "retake_variable 本次返修变量": "none 未返修；返修时一次只改一个变量",
        "fallback_shot 备用镜头": "改为侧脸、背影、手部、道具或反应镜头",
    }


def build_source_evidence(text: str, index: int, action: str, dialogue: str, os_line: str) -> dict[str, str]:
    clean = " ".join(text.split())
    target = dialogue if dialogue != "无" else os_line if os_line != "无" else ""
    if target and target in clean:
        pos = clean.find(target)
        start = max(0, pos - 30)
        end = min(len(clean), pos + len(target) + 30)
        return {
            "source_text_ref 原文引用位置": f"char:{pos}-{pos + len(target)}",
            "evidence_quote 原文证据句": clean[start:end],
            "adaptation_note 改编说明": "对白或旁白来自原文，镜头调度为导演拆解",
            "invented_flag 是否AI补充": "source_supported 原文支持",
            "source_confidence 原文置信度": "high 高",
        }
    quote = clean[:120] if clean else "无原文"
    return {
        "source_text_ref 原文引用位置": f"approx_shot:{index}",
        "evidence_quote 原文证据句": quote,
        "adaptation_note 改编说明": f"{action} 为导演调度补足，需用户确认是否符合原文",
        "invented_flag 是否AI补充": "director_bridge 导演补足",
        "source_confidence 原文置信度": "medium 中" if quote != "无原文" else "low 低",
    }


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
        for field in ["shot_id 镜头编号", "shot_purpose 镜头目的", "screen_direction 画面方向"]:
            cells = []
            for shot in chunk:
                text = shorten(str(shot.get(field, "")), cell_w - 2)
                cells.append(f" {text:<{cell_w - 2}} ")
            while len(cells) < cols:
                cells.append(" " * cell_w)
            lines.append("|" + "|".join(cells) + "|")
    lines.append(border)
    return "\n".join(lines)


def build_dialogue_coverage_ascii(shots: list[dict[str, Any]]) -> str:
    has_a = any("shot_a" in s.get("shot_purpose 镜头目的", "") for s in shots)
    has_b = any("shot_b" in s.get("shot_purpose 镜头目的", "") for s in shots)
    if not (has_a and has_b):
        return "无双人正反打对白，不生成 dialogue_coverage_ascii 对白覆盖图。"
    return """+------------------+------------------+------------------+
| MASTER 主镜头     | A 正打 shot_a     | B 反打 shot_b     |
| A○      ○B        | A○ -> B闭口       | A闭口 <- ○B       |
| 建立轴线不跳轴     | A开口，B画外方向   | B开口，A画外方向   |
+------------------+------------------+------------------+"""


def build_sketch(purpose: str, aspect_ratio: str) -> str:
    if "master" in purpose:
        return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：门框/阴影                   |
|                                      |
| MG 中景：A○ 左三分之一      ○B 右侧 |
|          A视线 ->        <- B视线    |
|                                      |
| BG 背景：主场景固定物件              |
| camera 摄影机：▣ 轴线同侧固定        |
+--------------------------------------+"""
    if "shot_a" in purpose:
        return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：B的肩或环境边缘可虚化       |
|                                      |
| MG 中景：A○ 近景占画面左/中         |
|          A视线 -> 画面右             |
|                                      |
| BG 背景：保持同一主场景              |
| camera 摄影机：▣ 侧前方30度          |
+--------------------------------------+"""
    if "shot_b" in purpose:
        return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：A的肩或环境边缘可虚化       |
|                                      |
| MG 中景：              ○B 近景右/中 |
|               画面左 <- B视线        |
|                                      |
| BG 背景：保持同一主场景              |
| camera 摄影机：▣ 侧前方30度          |
+--------------------------------------+"""
    if "insert" in purpose:
        return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：手部/道具占画面主体         |
|                                      |
| MG 中景：P1 道具 ○--- -> 触碰/握紧   |
|                                      |
| BG 背景：虚化，不换场景              |
| camera 摄影机：▣ 固定特写            |
+--------------------------------------+"""
    if "movement" in purpose:
        return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：保留空间参照物              |
|                                      |
| MG 中景：A○ 起点 -----> 结果位   ○B |
|          动作方向保持左 -> 右         |
|                                      |
| BG 背景：固定，不旋转空间            |
| camera 摄影机：▣ 轻微横移跟随        |
+--------------------------------------+"""
    if "reaction" in purpose:
        return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：画外事件方向留空            |
|                                      |
| MG 中景：              ○B 反应近景  |
|               画面左 <- B视线        |
|                                      |
| BG 背景：主场景固定物件              |
| camera 摄影机：▣ 固定机位            |
+--------------------------------------+"""
    return f"""frame / 画框：{aspect_ratio}
+--------------------------------------+
| FG 前景：环境边缘/遮挡物             |
|                                      |
| MG 中景：A○ 前景/中景 -> 下一镜方向  |
|                                      |
| BG 背景：保留主场景识别物            |
| camera 摄影机：▣ 固定机位            |
+--------------------------------------+"""


def build_layer_depth(scene: dict[str, Any]) -> str:
    scene_name = scene.get("scene_name 场景名", "主场景")
    return f"FG前景：门框/阴影/遮挡；MG中景：角色调度区；BG背景：{scene_name}固定物件"


def build_prop_anchor(project: Project, focus_character: dict[str, Any], action: str) -> str:
    prop_names = [p.get("prop_name 道具名", "") for p in project.props if p.get("prop_name 道具名")]
    prop = prop_names[0] if prop_names else "P1关键道具"
    owner = focus_character.get("character_name 角色名", "画面主体")
    if any(word in action for word in ["手", "道具", "刀", "剑", "握"]):
        return f"{prop}：由{owner}持有，位于画面主体手部区域，可小幅移动，不可消失"
    return f"{prop}：保持在场景固定位置或角色身上，不抢主体，不突然消失"


def is_high_risk_purpose(purpose: str) -> bool:
    return any(word in purpose for word in ["movement", "insert", "运动", "result"])


def build_motion_grid_ascii(purpose: str) -> str:
    if not is_high_risk_purpose(purpose):
        return ""
    return """+------------+------------+------------+
| 1 起势      | 2 接近      | 3 接触      |
| A○ 准备 ->  | A○ ---> B   | A/P1 -> B   |
| ▣ 固定      | ▣ 轻横移    | ▣ 特写      |
+------------+------------+------------+
| 4 结果      | 5 反应      | 6 收束      |
| B <- 后退   | B○ 停顿     | A○ 静止     |
| ▣ 中景      | ▣ 近景      | ▣ 固定      |
+------------+------------+------------+"""


def build_movement_arrow(purpose: str) -> str:
    if "movement" in purpose:
        return "A左侧起点 -> 画面中部结果位；只保留动作结果，不做复杂连续打斗"
    if "insert" in purpose:
        return "手部/道具：静止 -> 轻触/握紧 -> 停顿"
    if "shot_b" in purpose:
        return "无大位移；视线方向：B -> 画面左侧"
    return "无大位移；视线方向：A -> 画面右侧；人物大位置不变"


def build_camera_arrow(camera: str) -> str:
    if camera == "slow_push_in 缓慢推进":
        return "camera 摄影机：▣ 向前轻推，不改变轴线"
    if camera == "slight_lateral_move 轻微横移":
        return "camera 摄影机：▣ 左右轻微横移，不跨轴线"
    if camera == "subtle_handheld 轻微手持":
        return "camera 摄影机：▣ 轻微手持，主体稳定"
    return "camera 摄影机：▣ 固定不动"


def shorten(value: str, max_len: int) -> str:
    return value if len(value) <= max_len else value[: max_len - 1] + "…"
