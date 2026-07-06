from __future__ import annotations

from .v02_models import Issue, Project

ALLOWED_CAMERA = {
    "fixed_camera 固定机位",
    "slow_push_in 缓慢推进",
    "slight_lateral_move 轻微横移",
    "subtle_handheld 轻微手持",
}


def validate(project: Project) -> list[Issue]:
    issues: list[Issue] = []
    for c in project.characters:
        for field in ["face_shape 脸型", "hair_style 发型", "clothing_lock 服装锁定", "forbidden_changes 禁止变化"]:
            if not c.get(field):
                issues.append(Issue("BLOCKER", "asset.character_lock_missing", f"{c.get('character_id 角色编号')} 缺 {field}", "ADD 补充"))
    for shot in project.shots:
        sid = shot["shot_id 镜头编号"]
        required = ["motion_path 运动轨迹", "entry_pose 起始姿态", "exit_pose 结束姿态", "camera_movement 机位运动", "camera_axis 轴线方向", "fallback_shot 备用镜头"]
        for field in required:
            if not shot.get(field):
                issues.append(Issue("BLOCKER", "shot.control_missing", f"{sid} 缺 {field}", "ADD 补充"))
        if shot["camera_movement 机位运动"] not in ALLOWED_CAMERA:
            issues.append(Issue("BLOCKER", "camera.forbidden", f"{sid} 使用禁止机位", "DOWNGRADE 降级"))
        if shot["os_line 画外音"] != "无" and shot["mouth_state 嘴型状态"] != "all_closed 全员闭口":
            issues.append(Issue("BLOCKER", "dialogue.os_mouth_open", f"{sid} OS必须全员闭口", "LOCK 锁定"))
        for field in ["ambience_sfx 环境底音", "foley_sfx 拟音", "prop_sfx 道具音", "action_sfx 动作音", "music_note 音乐建议"]:
            if not shot.get(field):
                issues.append(Issue("WARN", "sound.missing", f"{sid} 缺 {field}", "ADD 补充"))
    return issues


def summary(issues: list[Issue]) -> dict:
    blockers = [x for x in issues if x.level == "BLOCKER"]
    warnings = [x for x in issues if x.level == "WARN"]
    return {
        "qa_status 质检状态": "BLOCKER" if blockers else "WARN" if warnings else "PASS",
        "blocker_count 阻塞问题数": len(blockers),
        "warning_count 警告问题数": len(warnings),
        "issues 问题列表": [x.__dict__ for x in issues],
    }
