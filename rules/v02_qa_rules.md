# v02_qa_rules 质检规则

## BLOCKER 必须返修

- 主角缺 `face_shape 脸型`、`hair_style 发型`、`clothing_lock 服装锁定`、`forbidden_changes 禁止变化`。
- 镜头缺 `motion_path 运动轨迹`、`entry_pose 起始姿态`、`exit_pose 结束姿态`。
- 镜头缺 `camera_movement 机位运动` 或使用非允许机位。
- 镜头缺 `camera_axis 轴线方向`。
- OS / 画外音镜头没有 `all_closed 全员闭口`。
- 视频提示词缺 `ambience_sfx 环境底音`、`foley_sfx 拟音`、`prop_sfx 道具音`、`action_sfx 动作音`、`music_note 音乐建议`。

## WARN 警告

- 镜头数不在 8-12。
- 相邻镜头景别重复过多。
- 高风险镜头没有 `grid_prompt 宫格提示词`。
- 对白镜头没有 `speaker_spatial_anchor 说话人空间锚点`。
