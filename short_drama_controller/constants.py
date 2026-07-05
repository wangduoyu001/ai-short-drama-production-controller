ALLOWED_CAMERA_MOVEMENTS = {
    "fixed_camera 固定机位",
    "slow_push_in 缓慢推进",
    "slight_lateral_move 轻微横移",
    "subtle_handheld 轻微手持",
}

FORBIDDEN_CAMERA_MOVEMENTS = {
    "fast_pan 快速摇镜",
    "360_orbit 360环绕",
    "complex_tracking 复杂跟拍",
    "crane_shot 升降机位",
    "long_take 长镜头调度",
    "multi_character_fight_tracking 多人打斗跟拍",
}

WEAK_PROMPT_WORDS = {
    "震撼", "大片感", "高级感", "电影感", "史诗级",
    "极致", "超燃", "激烈", "复杂", "华丽", "梦幻",
}

DEFAULT_LIMITS = {
    "production_mode 制作模式": "fast_demo 快速样片模式",
    "duration_seconds 时长秒数": "60-90",
    "shot_count 镜头数量": "8-12",
    "character_count 角色数量": "2-3",
    "main_scene_count 主场景数量": 1,
    "dialogue_rounds 对话轮数": "2-3",
    "action_level 动作等级": "low_to_medium 低到中",
    "episode_count 集数": 1,
}
