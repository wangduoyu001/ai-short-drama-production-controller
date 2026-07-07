from __future__ import annotations

from typing import Any

from .v02_models import Issue, Project
from .v02_qa import summary as base_summary
from .v02_schema import validate_schema
from .v02_source_coverage import validate_source_coverage

ALLOWED_CAMERA = {"fixed_camera 固定机位", "slow_push_in 缓慢推进", "slight_lateral_move 轻微横移", "subtle_handheld 轻微手持"}
SPATIAL_MARKERS = ["画面左", "画面右", "左侧", "右侧", "前景", "后景", "中景"]
VISUAL_MARKERS = ["布衣", "短打", "腰带", "发", "脸", "衣", "袍", "甲", "剑", "刀"]


def validate(project: Project) -> list[Issue]:
    items: list[Issue] = []
    items += [as_issue(x) for x in validate_schema(project.data)]
    items += [as_issue(x) for x in validate_source_coverage(project.data)]
    items += validate_assets(project)
    items += validate_project_pack(project)
    items += validate_shots(project)
    items += validate_shot_size_jump(project)
    return items


def validate_project_pack(project: Project) -> list[Issue]:
    items: list[Issue] = []
    required = [
        "director_read 导演读本",
        "producer_plan 制片执行计划",
        "sound_plan 声音设计计划",
        "project_state_capsule 项目状态胶囊",
    ]
    for field in required:
        if not project.data.get(field):
            items.append(Issue("BLOCKER", "project.pack_missing", f"项目缺 {field}", "ADD 补充并覆盖旧文件"))
    return items


def validate_assets(project: Project) -> list[Issue]:
    items: list[Issue] = []
    fields = ["face_shape 脸型", "hair_style 发型", "clothing_lock 服装锁定", "forbidden_changes 禁止变化", "spatial_anchor 空间锚点"]
    for char in project.characters:
        cid = char.get("character_id 角色编号", "UNKNOWN")
        for field in fields:
            if not char.get(field):
                items.append(Issue("BLOCKER", "asset.character_lock_missing", f"{cid} 缺 {field}", "ADD 补充"))
    return items


def validate_shots(project: Project) -> list[Issue]:
    items: list[Issue] = []
    for shot in project.shots:
        sid = shot.get("shot_id 镜头编号", "UNKNOWN")
        if shot.get("camera_movement 机位运动") not in ALLOWED_CAMERA:
            items.append(Issue("BLOCKER", "camera.forbidden", f"{sid} 使用不允许机位", "DOWNGRADE 降级"))
        if shot.get("os_line 画外音") != "无" and shot.get("mouth_state 嘴型状态") != "all_closed 全员闭口":
            items.append(Issue("BLOCKER", "dialogue.os_mouth_open", f"{sid} OS必须全员闭口", "LOCK 锁定"))
        if shot.get("speaker_mode 发声模式", "").startswith("spoken_dialogue"):
            anchor = shot.get("speaker_spatial_anchor 说话人空间锚点", "")
            if not strong_anchor(anchor):
                items.append(Issue("BLOCKER", "dialogue.anchor_weak", f"{sid} 说话人空间锚点不够强：{anchor}", "REWRITE 重写"))
        for field in ["ambience_sfx 环境底音", "foley_sfx 拟音", "prop_sfx 道具音", "action_sfx 动作音", "music_note 音乐建议"]:
            if not shot.get(field):
                items.append(Issue("WARN", "sound.missing", f"{sid} 缺 {field}", "ADD 补充"))
        for field in [
            "director_intent 导演意图", "this_clip_only 本段只拍", "reserved_for_later 后续保留",
            "planned_end_state 计划结束状态", "observed_end_state 实际生成结尾状态", "retake_variable 本次返修变量",
            "sketch_ascii 简笔手绘图", "movement_arrow 运动箭头", "camera_arrow 镜头箭头", "screen_direction 画面方向",
        ]:
            if not shot.get(field):
                items.append(Issue("WARN", "director_pack.missing", f"{sid} 缺 {field}", "ADD 补充"))
    return items


def validate_shot_size_jump(project: Project) -> list[Issue]:
    items: list[Issue] = []
    sizes = [size_group(s.get("shot_size 景别", "")) for s in project.shots]
    if len(set(x for x in sizes if x)) < 3 and len(project.shots) >= 6:
        items.append(Issue("WARN", "shot_size.variety_low", "全片景别变化不足，至少需要三类景别", "REWRITE 重写"))
    last = ""
    count = 0
    for idx, size in enumerate(sizes, start=1):
        if size == last:
            count += 1
        else:
            last, count = size, 1
        if size and count >= 3:
            items.append(Issue("WARN", "shot_size.repeated", f"连续{count}个镜头同类景别：{size}，约SH{idx:03d}", "REWRITE 重写"))
    return items


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


def strong_anchor(anchor: str) -> bool:
    return any(x in anchor for x in SPATIAL_MARKERS) and any(x in anchor for x in VISUAL_MARKERS)


def as_issue(item: dict[str, str]) -> Issue:
    return Issue(item.get("level 等级", "WARN"), item.get("code 代码", "unknown"), item.get("message 信息", ""), item.get("repair_action 返修动作", "FLAG 标记"))


def summary(issues: list[Issue]) -> dict[str, Any]:
    return base_summary(issues)
