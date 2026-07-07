from __future__ import annotations

from typing import Any

from .v02_models import Project

HOOK_WORDS = ["死", "消失", "背叛", "真相", "秘密", "跪", "求", "血", "哭", "闯", "抓", "亲生", "身份", "禁忌", "报应", "上门", "反转"]
PAYOFF_WORDS = ["打脸", "揭穿", "反击", "报仇", "救", "认出", "逆袭", "翻身", "夺回", "证明", "跪下", "认错"]
REVERSAL_WORDS = ["突然", "没想到", "却", "其实", "原来", "竟然", "反而", "转身", "下一秒", "这时"]
CLIFF_WORDS = ["门开了", "电话响了", "身后", "黑影", "出现", "认出", "抬头", "一句话", "停住", "看见", "真相"]

DRAMA_BEATS = [
    ("cold_open 冷开场", "前三秒抛出危险、羞辱、秘密或反常画面"),
    ("identity_pressure 身份压力", "快速交代谁被压迫、谁掌权、谁隐藏身份"),
    ("conflict_lock 冲突锁定", "用一个明确目标把人物锁进同一场冲突"),
    ("reversal_midpoint 中段反转", "用信息差或动作结果改变局面"),
    ("payoff 爽点兑现", "让观众看到一次反击、揭穿、获救或身份优势"),
    ("cliffhanger 集尾钩子", "停在新威胁、新信息或下一场冲突入口"),
]


def build_drama_adaptation(project: Project) -> None:
    text = project.data.get("source_text 原文", "")
    blocks = project.data.get("event_blocks 事件段落拆分", [])
    project.data["drama_structure 短剧结构"] = {
        "format_target 形态目标": "vertical_microdrama 竖屏微短剧；每个 generation_clip 生成片段 4-15 秒",
        "opening_hook 开场钩子": choose_hook(text, blocks),
        "core_desire 核心欲望": infer_core_desire(text),
        "conflict_engine 冲突发动机": infer_conflict_engine(text),
        "reversal_plan 反转计划": build_reversal_plan(text, blocks),
        "payoff_plan 爽点计划": build_payoff_plan(text, blocks),
        "cliffhanger_plan 集尾钩子计划": build_cliffhanger_plan(text, blocks),
        "episode_beats 单集节奏": build_episode_beats(blocks),
        "adaptation_rules 改编规则": [
            "前三秒必须给可见钩子，不用旁白解释世界观",
            "每个片段只解决一个冲突节点，不一镜讲完整件事",
            "对白服务压迫、反击、信息差，禁止散文化解释",
            "每集结尾停在新问题、新危险、新身份或新反转上",
            "小说心理描写必须改成动作、道具、视线和沉默",
        ],
    }


def choose_hook(text: str, blocks: list[dict[str, Any]]) -> dict[str, str]:
    best = find_sentence(text, HOOK_WORDS) or first_core_event(blocks)
    return {
        "hook_type 钩子类型": classify_hook(best),
        "hook_image 钩子画面": best or "用反常动作或危险场面开场",
        "hook_question 观众问题": infer_hook_question(best),
        "rewrite_note 改写说明": "把小说铺垫前移为开场可见画面，先让观众产生问题，再补信息",
    }


def infer_core_desire(text: str) -> str:
    if any(word in text for word in ["救", "求助", "找", "护送"]):
        return "救人/求助/完成护送"
    if any(word in text for word in ["报仇", "反击", "夺回", "证明"]):
        return "反击压迫并夺回主动权"
    if any(word in text for word in ["真相", "秘密", "身份"]):
        return "揭开真相或隐藏身份"
    return "主角必须在压力下完成一个立刻可见的目标"


def infer_conflict_engine(text: str) -> str:
    if "禁忌" in text or "仙" in text or "堂口" in text:
        return "禁忌被触犯，民俗规则反噬人物行动"
    if any(word in text for word in ["身份", "亲生", "真假"]):
        return "身份信息差制造压迫和反转"
    if any(word in text for word in ["追", "逃", "打", "杀", "护送"]):
        return "身体行动和追逃压力推动情节"
    return "人物目标和外部阻力持续碰撞"


def build_reversal_plan(text: str, blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    source = [b.get("core_event 核心事件", "") for b in blocks] or [text]
    out = []
    for idx, event in enumerate(source[:4], 1):
        if any(word in event for word in REVERSAL_WORDS + HOOK_WORDS):
            out.append({"reversal_id 反转编号": f"REV_{idx:02d}", "source_event 来源事件": event[:100], "screen_reversal 可拍反转": make_reversal(event)})
    return out or [{"reversal_id 反转编号": "REV_01", "source_event 来源事件": first_core_event(blocks), "screen_reversal 可拍反转": "让看似弱势的一方突然掌握关键信息或道具"}]


def build_payoff_plan(text: str, blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    events = [b.get("core_event 核心事件", "") for b in blocks] or [text]
    out = []
    for idx, event in enumerate(events[:4], 1):
        if any(word in event for word in PAYOFF_WORDS + ["救", "挡", "认出"]):
            out.append({"payoff_id 爽点编号": f"PAY_{idx:02d}", "source_event 来源事件": event[:100], "visible_payoff 可见爽点": make_payoff(event)})
    return out or [{"payoff_id 爽点编号": "PAY_01", "source_event 来源事件": first_core_event(blocks), "visible_payoff 可见爽点": "主角用动作或信息差赢回一次主动权"}]


def build_cliffhanger_plan(text: str, blocks: list[dict[str, Any]]) -> dict[str, str]:
    candidate = find_sentence(text, CLIFF_WORDS + REVERSAL_WORDS) or last_core_event(blocks)
    return {
        "cliffhanger_type 钩子类型": classify_cliff(candidate),
        "ending_image 结尾画面": candidate or "门外出现新人物或新证据",
        "next_episode_question 下一集问题": infer_hook_question(candidate),
        "cut_point 剪断点": "在答案出现前一秒切断，保留问题不解释",
    }


def build_episode_beats(blocks: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not blocks:
        return [{"beat_id 节奏编号": key, "beat_goal 节奏目标": value, "source_block 来源段落": "待补原文"} for key, value in DRAMA_BEATS]
    out = []
    for idx, (key, value) in enumerate(DRAMA_BEATS):
        block = blocks[min(idx, len(blocks) - 1)]
        out.append({"beat_id 节奏编号": key, "beat_goal 节奏目标": value, "source_block 来源段落": block.get("block_id 段落编号", ""), "source_event 来源事件": block.get("core_event 核心事件", "")[:100]})
    return out


def find_sentence(text: str, words: list[str]) -> str:
    for part in split_sentences(text):
        if any(word in part for word in words):
            return part[:140]
    return ""


def split_sentences(text: str) -> list[str]:
    import re
    return [x.strip() for x in re.split(r"(?<=[。！？!?；;])", " ".join(text.split())) if x.strip()]


def first_core_event(blocks: list[dict[str, Any]]) -> str:
    return str(blocks[0].get("core_event 核心事件", "")) if blocks else ""


def last_core_event(blocks: list[dict[str, Any]]) -> str:
    return str(blocks[-1].get("core_event 核心事件", "")) if blocks else ""


def classify_hook(text: str) -> str:
    if any(word in text for word in ["死", "血", "消失"]):
        return "danger_hook 危险钩子"
    if any(word in text for word in ["跪", "求", "哭"]):
        return "humiliation_hook 羞辱/求助钩子"
    if any(word in text for word in ["真相", "秘密", "身份"]):
        return "secret_hook 秘密/身份钩子"
    return "abnormal_hook 反常画面钩子"


def classify_cliff(text: str) -> str:
    if any(word in text for word in ["出现", "身后", "黑影"]):
        return "new_threat 新威胁"
    if any(word in text for word in ["真相", "认出", "身份"]):
        return "new_information 新信息"
    return "unanswered_question 未回答问题"


def infer_hook_question(text: str) -> str:
    if not text:
        return "接下来会发生什么？"
    if any(word in text for word in ["身份", "亲生", "认出"]):
        return "这个人的真实身份到底是什么？"
    if any(word in text for word in ["死", "血", "消失", "黑影"]):
        return "危险来自哪里，主角能不能活下来？"
    if any(word in text for word in ["求", "跪", "上门"]):
        return "求助人到底隐瞒了什么？"
    return "这个反常事件背后的原因是什么？"


def make_reversal(event: str) -> str:
    return f"把事件改成可见反转：前半镜头按观众预期推进，后半镜头用动作/道具/身份信息推翻预期。依据：{event[:60]}"


def make_payoff(event: str) -> str:
    return f"把事件改成一次可见爽点：压迫先成立，再让主角用行动或信息差赢回主动。依据：{event[:60]}"
