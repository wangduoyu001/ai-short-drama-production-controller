# production_rules 生产规则

## scope_gate 范围闸门
- duration_seconds 时长秒数：60-90 秒。
- shot_count 镜头数量：8-12 个。
- character_count 角色数量：2-3 人。
- main_scene_count 主场景数量：1 个优先。
- action_level 动作等级：低到中。

## camera_rules 机位规则
允许：
- fixed_camera 固定机位
- slow_push_in 缓慢推进
- slight_lateral_move 轻微横移
- subtle_handheld 轻微手持

禁止：
- fast_pan 快速摇镜
- 360_orbit 360环绕
- complex_tracking 复杂跟拍
- crane_shot 升降机位
- long_take 长镜头调度

## motion_rules 运动规则
- 每个镜头只允许一个主动作。
- 每个动作必须有起点、终点、方向、速度。
- 复杂动作必须拆成插入镜头、反应镜头、结果镜头。
