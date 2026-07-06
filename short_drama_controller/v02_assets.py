from __future__ import annotations

from typing import Any


def extract_assets(text: str) -> dict[str, list[dict[str, Any]]]:
    return {
        "characters 角色列表": extract_characters(text),
        "scenes 场景列表": extract_scenes(text),
        "props 道具列表": extract_props(text),
    }


def extract_characters(text: str) -> list[dict[str, Any]]:
    keywords = ["少年", "镖头", "师兄", "师父", "长老", "弟子", "主角", "男主", "女主", "反派", "老板", "店员"]
    names = unique([name for name in keywords if name in text]) or ["主角", "对手"]
    out = []
    for idx, name in enumerate(names[:3], start=1):
        cid = f"CHAR_{chr(64 + idx)}"
        out.append({
            "character_id 角色编号": cid,
            "character_name 角色名": name,
            "aliases 代称": [name],
            "role_function 角色功能": "主角" if idx == 1 else "对手/配角",
            "face_shape 脸型": "瘦削长脸" if idx == 1 else "方脸短须",
            "hair_style 发型": "黑色束发",
            "clothing_lock 服装锁定": "灰蓝布衣，黑色腰带" if idx == 1 else "深褐短打，旧皮护腕",
            "prop_lock 道具锁定": "木剑" if idx == 1 else "短刀",
            "spatial_anchor 空间锚点": "画面左侧" if idx == 1 else "画面右侧",
            "forbidden_changes 禁止变化": "禁止换脸、换发型、换服装、年龄变化、无关现代物件",
        })
    return out


def extract_scenes(text: str) -> list[dict[str, Any]]:
    if "镖局" in text or "武侠" in text:
        return [scene("SCENE_01", "古代镖局院子", "傍晚", "左侧暖黄侧光", "左门、右兵器架、后院墙、中央空地", "木门、兵器架、旧旗、石砖地")]
    return [scene("SCENE_01", "简洁对话场景", "夜晚", "稳定侧光", "A左B右，中间空地或桌面", "门、桌、墙面")]


def scene(sid: str, name: str, time: str, light: str, layout: str, props: str) -> dict[str, Any]:
    return {
        "scene_id 场景编号": sid,
        "scene_name 场景名": name,
        "time_of_day 时间段": time,
        "lighting_direction 光线方向": light,
        "layout_map 空间布局": layout,
        "fixed_props 固定物件": props,
        "visual_prompt 视觉提示词": f"{name}，{time}，{light}，{layout}，{props}，无人物，空间稳定",
    }


def extract_props(text: str) -> list[dict[str, Any]]:
    names = [x for x in ["木剑", "短刀", "长剑", "酒杯", "信物", "手机", "灯笼"] if x in text]
    if not names:
        names = ["木剑", "短刀"] if "镖局" in text else ["关键道具"]
    return [{
        "prop_id 道具编号": f"PROP_{i:02d}",
        "prop_name 道具名": name,
        "visual_prompt 视觉提示词": f"{name}，纯外观，道具图，中性背景，无人物，无人名",
    } for i, name in enumerate(names[:5], 1)]


def unique(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out
