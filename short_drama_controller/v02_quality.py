from __future__ import annotations

from typing import Any

from .v02_models import Issue, Project
from .v02_qa import summary as base_summary
from .v02_schema import validate_schema
from .v02_source_coverage import validate_source_coverage
from .v02_storyboard import is_high_risk_purpose

ALLOWED_CAMERA = {"fixed_camera 固定机位", "slow_push_in 缓慢推进", "slight_lateral_move 轻微横移", "subtle_handheld 轻微手持"}
SPATIAL_MARKERS = ["画面左", "画面右", "左侧", "右侧", "前景", "后景", "中景"]
VISUAL_MARKERS = ["布衣", "短打", "腰带", "发", "脸", "衣", "袍", "甲", "剑", "刀"]
BANNED_PLACEHOLDERS = ["情绪或动作推进", "运动或情绪起点明确", "运动结果或情绪落点明确", "建立空间和轴线", "手部或道具特写"]
ABSTRACT_PROMPT_WORDS = ["让观众", "导演意图", "潜台词", "权力变化", "观众感受", "证明自己", "退路", "底牌"]


def validate(project: Project) -> list[Issue]:
    items: list[Issue] = []
    items += [as_issue(x) for x in validate_schema(project.data)]
    items += [as_issue(x) for x in validate_source_coverage(project.data)]
    items += validate_assets(project)
    items += validate_project_pack(project)
    items += validate_beat_map(project)
    items += validate_director_read(project)
    items += validate_shots(project)
    items += validate_shot_size_jump(project)
    return items


def validate_project_pack(project: Project) -> list[Issue]:
    items: list[Issue] = []
    required = [
        "beat_map 剧情节拍表",
        "director_read 导演读本",
        "producer_plan 制片执行计划",
        "sound_plan 声音设计计划",
        "project_state_capsule 项目状态胶囊",
        "approval_gates 确认闸门",
        "storyboard_layout 分镜总览布局",
        "storyboard_grid_ascii 分镜总览简笔图",
    ]
    for field in required:
        if not project.data.get(field):
            items.append(Issue("BLOCKER", "project.pack_missing", f"项目缺 {field}", "ADD 补充并覆盖旧文件"))
    if has_two_person_dialogue(project) and not project.data.get("dialogue_coverage_ascii 对白覆盖图"):
        items.append(Issue("WARN", "storyboard.dialogue_coverage_missing", "双人对白项目缺 dialogue_coverage_ascii 对白覆盖图", "ADD 补充"))
    return items


def validate_beat_map(project: Project) -> list[Issue]:
    items: list[Issue] = []
    beats = project.data.get("beat_map 剧情节拍表", [])
    required = ["beat_id 节拍编号", "source_quote 原文证据", "visible_action 可见动作", "dialogue 对白", "conflict 冲突", "emotion_shift 情绪变化", "power_shift 权力变化", "subtext 潜台词", "shot_hint 镜头建议"]
    if not beats:
        return [Issue("BLOCKER", "beat_map.missing", "缺 beat_map 剧情节拍表，镜头无法基于剧情生成", "REBUILD 重新生成")]
    for beat in beats:
        bid = beat.get("beat_id 节拍编号", "UNKNOWN")
        for field in required:
            if not beat.get(field):
                items.append(Issue("WARN", "beat_map.field_missing", f"{bid} 缺 {field}", "REBUILD 重新生成节拍"))
        if contains_placeholder(beat):
            items.append(Issue("BLOCKER", "beat_map.placeholder", f"{bid} 含模板占位符", "REWRITE 重写具体节拍"))
    return items


def validate_director_read(project: Project) -> list[Issue]:
    items: list[Issue] = []
    director_read = project.data.get("director_read 导演读本", {})
    required = [
        "source_basis 原文依据", "conflict_terms 冲突词", "dialogue_basis 对白依据", "relationship_basis 角色关系依据",
        "scene_function 场景功能", "scene_function_evidence 场景功能证据", "scene_turn 场景转折", "scene_turn_evidence 场景转折证据",
        "power_shift 权力变化", "power_shift_evidence 权力变化证据", "subtext 潜台词", "subtext_evidence 潜台词证据",
        "director_intent 导演意图", "director_read_confidence 导演读本置信度",
    ]
    for field in required:
        if not director_read.get(field):
            items.append(Issue("WARN", "director_read.missing_evidence", f"导演读本缺 {field}", "REBUILD 重新基于原文生成导演读本"))
    confidence = director_read.get("director_read_confidence 导演读本置信度", "")
    if confidence.startswith("low"):
        items.append(Issue("WARN", "director_read.low_confidence", "导演读本置信度低，需要人工确认场景功能、转折、权力变化和潜台词", "CONFIRM 人工确认"))
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
    beat_ids = {b.get("beat_id 节拍编号") for b in project.data.get("beat_map 剧情节拍表", [])}
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
        required_shot_fields = [
            "beat_id 节拍编号", "source_quote 原文节拍证据", "director_intent 导演意图", "this_clip_only 本段只拍", "reserved_for_later 后续保留",
            "planned_end_state 计划结束状态", "observed_end_state 实际生成结尾状态", "retake_variable 本次返修变量",
            "aspect_ratio 画幅比例", "character_symbols 人物符号", "sketch_ascii 简笔手绘图", "movement_arrow 运动箭头", "camera_arrow 镜头箭头",
            "screen_direction 画面方向", "layer_depth 前中后景", "prop_anchor 道具锚点", "source_text_ref 原文引用位置", "evidence_quote 原文证据句",
            "adaptation_note 改编说明", "invented_flag 是否AI补充", "source_confidence 原文置信度", "unknown_policy 不确定处理规则",
        ]
        for field in required_shot_fields:
            if not shot.get(field):
                items.append(Issue("WARN", "director_pack.missing", f"{sid} 缺 {field}", "ADD 补充"))
        if shot.get("beat_id 节拍编号") not in beat_ids:
            items.append(Issue("WARN", "shot.beat_missing", f"{sid} 没有绑定有效 beat_id 节拍编号", "REBUILD 重新绑定节拍"))
        if contains_placeholder(shot):
            items.append(Issue("BLOCKER", "shot.placeholder", f"{sid} 含模板占位符，不能作为可用分镜", "REWRITE 重写具体动作"))
        purpose = shot.get("shot_purpose 镜头目的", "")
        if is_high_risk_purpose(purpose) and not shot.get("motion_grid_ascii 动作拆解六宫格"):
            items.append(Issue("WARN", "storyboard.motion_grid_missing", f"{sid} 高风险镜头缺 motion_grid_ascii 动作拆解六宫格", "ADD 补充"))
        if shot.get("invented_flag 是否AI补充") == "director_bridge 导演补足":
            items.append(Issue("WARN", "source.director_bridge", f"{sid} 含导演补足内容，需要用户确认：{shot.get('adaptation_note 改编说明', '')}", "CONFIRM 人工确认"))
        items += validate_prompt_storyboard_consistency(shot, sid)
    return items


def validate_prompt_storyboard_consistency(shot: dict, sid: str) -> list[Issue]:
    items: list[Issue] = []
    image_prompt = shot.get("image_prompt 图片提示词", "")
    has_characters = bool(shot.get("on_screen_characters 在场人物"))
    if has_characters and any(word in image_prompt for word in ["无人物", "无人空镜", "empty scene", "no character"]):
        items.append(Issue("BLOCKER", "prompt.character_conflict", f"{sid} 分镜有人物但 image_prompt 写无人", "REWRITE 重写图片提示词"))
    for word in ABSTRACT_PROMPT_WORDS:
        if word in image_prompt:
            items.append(Issue("WARN", "prompt.abstract_intent", f"{sid} image_prompt 含抽象导演意图：{word}", "MOVE 移到导演读本或视频提示词"))
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
            items.append(Issue("WARN", "shot_size.repeated", f"连续{count}个镜头同类景别：{size}，约SH{idx:03d}", "REPAIR 重排景别"))
    return items


def contains_placeholder(data: dict) -> bool:
    text = str(data)
    return any(word in text for word in BANNED_PLACEHOLDERS)


def has_two_person_dialogue(project: Project) -> bool:
    modes = [s.get("shot_purpose 镜头目的", "") for s in project.shots]
    return any("shot_a" in x for x in modes) and any("shot_b" in x for x in modes)


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
