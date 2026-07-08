from __future__ import annotations

import re

from .v02_models import Project

SCENE_SEEDS = [
    ("堂口", "民俗堂口"), ("香案", "堂口香案"), ("鸡窝", "夜里的鸡窝"), ("破庙", "破庙室内"),
    ("院子", "乡村院子"), ("山路", "荒山小路"), ("客栈", "古代客栈大堂"),
]
ENTITY_SEEDS = ["黄皮子", "狐仙", "仙家", "妖物", "黑影", "异物", "灵体", "求助人", "村民", "老人", "妇人", "孩子"]
PROP_SEEDS = ["香炉", "供桌", "牌位", "黄纸", "符", "鸡窝", "鸡", "灯笼", "酒碗", "令牌", "信", "木箱", "镖旗", "刀", "剑"]

SCENE_SUFFIXES = ["堂", "庙", "院", "屋", "房", "楼", "阁", "殿", "府", "庄", "寨", "村", "镇", "街", "巷", "桥", "河", "湖", "山", "林", "洞", "谷", "店", "铺", "仓", "船", "车", "台", "坛", "井", "园", "城", "门", "祠", "观", "寺", "塔", "营", "站", "办公室"]
PROP_MEASURES = ["把", "柄", "口", "只", "个", "张", "盏", "碗", "杯", "封", "块", "枚", "根", "条", "件", "面", "卷", "本", "串", "双", "支", "杆", "炉", "桌"]
PROP_ACTIONS = ["拿起", "握住", "递出", "掏出", "放下", "点燃", "推开", "抱着", "扛着", "背着", "打开", "关上", "举起", "收起", "塞进", "扔下"]
STOP_WORDS = {"一个", "一下", "时候", "地方", "东西", "男人", "女人", "他们", "我们", "自己", "声音", "眼神", "动作", "画面", "镜头"}


def expand_project_assets(project: Project) -> None:
    text = project.data.get("source_text 原文", "")
    expand_characters(project, text)
    expand_scenes(project, text)
    expand_props(project, text)


def expand_characters(project: Project, text: str) -> None:
    existing = {c.get("character_name 角色名") for c in project.characters}
    for name in unique(ENTITY_SEEDS + extract_named_entities(text)):
        if name and name in text and name not in existing and len(project.characters) < 12:
            add_character(project, name)
            existing.add(name)


def add_character(project: Project, name: str) -> None:
    is_entity = any(x in name for x in ["仙", "灵", "妖", "异物", "黄皮子", "狐", "黑影"])
    project.characters.append({
        "character_id 角色编号": f"CHAR_{len(project.characters)+1:02d}",
        "character_name 角色名": name,
        "aliases 代称": [name],
        "role_function 角色功能": "异物/灵体" if is_entity else "配角/事件推动者",
        "face_shape 脸型": "非人轮廓固定" if is_entity else "清晰可识别脸型",
        "hair_style 发型": "轮廓固定" if is_entity else "固定发型",
        "clothing_lock 服装锁定": "形象轮廓固定" if is_entity else "低饱和旧衣，身份服装固定",
        "prop_lock 道具锁定": "按剧情归属锁定",
        "spatial_anchor 空间锚点": "画面边缘或中后景",
        "forbidden_changes 禁止变化": "禁止换脸、换发型、换服装、年龄变化、形象漂移",
    })


def expand_scenes(project: Project, text: str) -> None:
    existing_names = {s.get("scene_name 场景名") for s in project.scenes}
    candidates = [name for keyword, name in SCENE_SEEDS if keyword in text]
    candidates += extract_dynamic_scenes(text)
    for name in unique(candidates):
        if valid_name(name) and name not in existing_names and len(project.scenes) < 16:
            project.scenes.append(make_scene(project, name))
            existing_names.add(name)


def make_scene(project: Project, name: str) -> dict:
    return {
        "scene_id 场景编号": f"SCENE_{len(project.scenes)+1:02d}",
        "scene_name 场景名": name,
        "time_of_day 时间段": infer_time(name),
        "lighting_direction 光线方向": "按原文光线；未明示则低饱和稳定侧光",
        "layout_map 空间布局": "前景遮挡，中景人物调度区，后景固定物件；进出路线必须清楚",
        "fixed_props 固定物件": "由原文场景物件决定；未明示则保留门、墙、地面等空间锚点",
        "visual_prompt 视觉提示词": f"{name}，空间稳定，前中后景清楚，低饱和电影写实，无字幕，无水印",
    }


def expand_props(project: Project, text: str) -> None:
    existing = {p.get("prop_name 道具名") for p in project.props}
    candidates = [name for name in PROP_SEEDS if name in text]
    candidates += extract_dynamic_props(text)
    for name in unique(candidates):
        if valid_name(name) and name not in existing and len(project.props) < 24:
            project.props.append({
                "prop_id 道具编号": f"PROP_{len(project.props)+1:02d}",
                "prop_name 道具名": name,
                "visual_prompt 视觉提示词": f"{name}，纯外观，道具图，中性背景，无人物，无人名，材质清楚",
            })
            existing.add(name)


def extract_dynamic_scenes(text: str) -> list[str]:
    suffix_group = "|".join(SCENE_SUFFIXES)
    patterns = [
        rf"(?:在|到|进|进了|来到|走进|回到|守在|躲进|穿过|离开)([\u4e00-\u9fa5]{{1,10}}(?:{suffix_group}))",
        rf"([\u4e00-\u9fa5]{{1,8}}(?:{suffix_group}))(?:里|内|外|前|后|旁|边|口)",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text))
    return [normalize_name(x) for x in found]


def extract_dynamic_props(text: str) -> list[str]:
    measure_group = "|".join(PROP_MEASURES)
    action_group = "|".join(PROP_ACTIONS)
    patterns = [
        rf"(?:一|两|三|那|这|几)?(?:{measure_group})([\u4e00-\u9fa5]{{1,8}})",
        rf"(?:{action_group})([\u4e00-\u9fa5]{{1,8}})",
        rf"([\u4e00-\u9fa5]{{1,8}})(?:响了|碎了|亮了|灭了|落地|掉下)",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text))
    return [normalize_name(x) for x in found]


def extract_named_entities(text: str) -> list[str]:
    suffixes = ["仙", "灵", "者", "人", "师", "客", "童", "婆", "叔", "娘", "爷"]
    found: list[str] = []
    for suffix in suffixes:
        found.extend(re.findall(rf"([\u4e00-\u9fa5]{{1,5}}{suffix})", text))
    return [normalize_name(x) for x in found]


def infer_time(name: str) -> str:
    if any(word in name for word in ["夜", "灯", "堂", "庙"]):
        return "夜晚或昏暗时段"
    if any(word in name for word in ["山", "街", "桥", "村", "院"]):
        return "由原文时间决定"
    return "由原文决定"


def normalize_name(value: str) -> str:
    cleaned = value.strip(" ，。！？；：、的了着过在到进里内外前后旁边口")
    return cleaned[:12]


def valid_name(value: str) -> bool:
    return 1 < len(value) <= 12 and value not in STOP_WORDS and not any(bad in value for bad in ["什么", "怎么", "不是", "没有"])


def unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out
