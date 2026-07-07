from __future__ import annotations

from .v02_models import Project

ENTITY_NAMES = ["黄皮子", "狐仙", "仙家", "异物", "灵体", "求助人", "村民", "老人", "妇人", "孩子"]
PROP_NAMES = ["香炉", "供桌", "牌位", "黄纸", "符", "鸡窝", "鸡", "灯笼", "酒碗", "令牌", "信", "木箱", "镖旗", "刀", "剑"]
SCENES = [
    ("堂口", "民俗堂口", "夜晚", "香火红与冷灰侧光", "香案在中，门口在后，左右供桌", "香炉、供桌、牌位、红布"),
    ("香案", "堂口香案", "夜晚", "香火红光", "前景香炉，中景供桌，后景牌位", "香炉、黄纸、供品"),
    ("鸡窝", "夜里的鸡窝", "深夜", "月光与冷灰暗部", "鸡窝在右，院墙在后，人物从左进入", "木栅栏、鸡窝、土地、草堆"),
    ("破庙", "破庙室内", "夜晚", "冷月光与残火", "门口在后，供台在中，破帘在侧", "破供桌、断梁、灰尘、门帘"),
    ("院子", "乡村院子", "夜晚", "冷灰夜色和屋内暖光", "院门在后，鸡窝或柴堆在侧", "木门、柴堆、水缸、土墙"),
    ("山路", "荒山小路", "黄昏", "逆光与雾气", "小路斜穿画面，树影压住后景", "枯树、石头、尘土"),
    ("客栈", "古代客栈大堂", "夜晚", "灯笼暖光", "桌椅分层，楼梯在后，门口在侧", "木桌、灯笼、酒碗、楼梯"),
]


def expand_project_assets(project: Project) -> None:
    text = project.data.get("source_text 原文", "")
    expand_characters(project, text)
    expand_scenes(project, text)
    expand_props(project, text)


def expand_characters(project: Project, text: str) -> None:
    existing = {c.get("character_name 角色名") for c in project.characters}
    for name in ENTITY_NAMES:
        if name in text and name not in existing:
            is_entity = name in ["黄皮子", "狐仙", "仙家", "异物", "灵体"]
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
    existing = {s.get("scene_name 场景名") for s in project.scenes}
    for keyword, name, time, light, layout, props in SCENES:
        if keyword in text and name not in existing:
            project.scenes.append({
                "scene_id 场景编号": f"SCENE_{len(project.scenes)+1:02d}",
                "scene_name 场景名": name,
                "time_of_day 时间段": time,
                "lighting_direction 光线方向": light,
                "layout_map 空间布局": layout,
                "fixed_props 固定物件": props,
                "visual_prompt 视觉提示词": f"{name}，{time}，{light}，{layout}，{props}，空间稳定",
            })


def expand_props(project: Project, text: str) -> None:
    existing = {p.get("prop_name 道具名") for p in project.props}
    for name in PROP_NAMES:
        if name in text and name not in existing:
            project.props.append({
                "prop_id 道具编号": f"PROP_{len(project.props)+1:02d}",
                "prop_name 道具名": name,
                "visual_prompt 视觉提示词": f"{name}，纯外观，道具图，中性背景，无人物，无人名",
            })
