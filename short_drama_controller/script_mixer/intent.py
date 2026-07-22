from __future__ import annotations

import re
from typing import Protocol

from .models import ScriptUnit, VisualIntent


class IntentProvider(Protocol):
    def generate(self, unit: ScriptUnit) -> VisualIntent:
        ...


_CONCEPT_MAP: dict[str, dict[str, list[str]]] = {
    "努力": {
        "literal": ["人物工作", "敲键盘", "深夜办公室"],
        "metaphor": ["逆光前行", "持续奔跑", "重复练习"],
        "tags": ["工作", "专注", "行动"],
        "emotion": ["坚持", "疲惫"],
    },
    "失败": {
        "literal": ["人物低头", "空荡办公室", "数据下跌"],
        "metaphor": ["雨中独行", "道路受阻", "反复回到原点"],
        "tags": ["挫折", "低谷", "压力"],
        "emotion": ["挫败", "迷茫"],
    },
    "赚钱": {
        "literal": ["手机订单", "电脑数据", "交易界面"],
        "metaphor": ["增长曲线", "机会窗口", "积累成果"],
        "tags": ["商业", "收入", "增长"],
        "emotion": ["期待", "兴奋"],
    },
    "自媒体": {
        "literal": ["手机拍摄", "剪辑软件界面", "创作者面对镜头"],
        "metaphor": ["信息流快速滑动", "内容持续发布"],
        "tags": ["短视频", "内容创作", "手机"],
        "emotion": ["专注"],
    },
    "系统": {
        "literal": ["流程图", "自动化界面", "多个任务连接"],
        "metaphor": ["齿轮协作", "流水线运转", "积木组合"],
        "tags": ["自动化", "流程", "效率"],
        "emotion": ["秩序", "稳定"],
    },
    "焦虑": {
        "literal": ["人物揉眉心", "查看手机消息", "深夜失眠"],
        "metaphor": ["拥挤人群", "快速闪烁画面", "阴影压迫"],
        "tags": ["压力", "失眠", "困扰"],
        "emotion": ["焦虑", "压迫"],
    },
    "机会": {
        "literal": ["人物发现信息", "打开电脑页面", "握手合作"],
        "metaphor": ["门被打开", "阳光穿过缝隙", "道路出现分岔"],
        "tags": ["发现", "选择", "未来"],
        "emotion": ["希望", "期待"],
    },
    "重复": {
        "literal": ["重复点击", "批量表格", "相同动作循环"],
        "metaphor": ["循环轨道", "原地奔跑", "时钟快速转动"],
        "tags": ["循环", "低效", "机械"],
        "emotion": ["疲惫", "麻木"],
    },
}

_NEGATIVE_BY_EMOTION: dict[str, list[str]] = {
    "焦虑": ["庆祝", "旅游", "轻松大笑"],
    "挫败": ["胜利", "欢呼", "领奖"],
    "希望": ["绝望", "黑屏", "崩溃"],
}


def _keywords(text: str) -> list[str]:
    clean = re.sub(r"[，。！？!?；;、,:：\s]", " ", text)
    tokens = [item for item in clean.split(" ") if len(item) >= 2]
    if tokens:
        return tokens[:8]
    return [text[:12]] if text else []


class RuleBasedIntentProvider:
    """Zero-cost fallback used before a local or cloud language model is configured."""

    def generate(self, unit: ScriptUnit) -> VisualIntent:
        literal: list[str] = []
        metaphor: list[str] = []
        tags: list[str] = []
        emotions: list[str] = []
        for concept, mapping in _CONCEPT_MAP.items():
            if concept in unit.text:
                literal.extend(mapping["literal"])
                metaphor.extend(mapping["metaphor"])
                tags.extend(mapping["tags"])
                emotions.extend(mapping["emotion"])

        if not literal:
            literal = [unit.text, *_keywords(unit.text)]
        if not metaphor:
            metaphor = [f"表达{unit.text[:16]}含义的生活化画面"]
        if not tags:
            tags = _keywords(unit.text)
        if not emotions:
            emotions = ["中性"]

        negative: list[str] = []
        for emotion in emotions:
            negative.extend(_NEGATIVE_BY_EMOTION.get(emotion, []))

        preferred_shots = ["特写", "快速运动"] if unit.role == "hook" else ["中景", "特写"]
        if unit.role == "conclusion":
            preferred_shots = ["稳定中景", "大全景"]

        return VisualIntent(
            unit_id=unit.unit_id,
            literal_queries=list(dict.fromkeys(literal)),
            metaphor_queries=list(dict.fromkeys(metaphor)),
            positive_tags=list(dict.fromkeys(tags)),
            negative_tags=list(dict.fromkeys(negative)),
            emotion=list(dict.fromkeys(emotions)),
            preferred_shots=preferred_shots,
        )


def build_visual_intents(
    units: list[ScriptUnit],
    provider: IntentProvider | None = None,
) -> list[VisualIntent]:
    selected = provider or RuleBasedIntentProvider()
    return [selected.generate(unit) for unit in units]
