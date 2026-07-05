# qa_rules 质检规则

## BLOCKER 必须返修
- 主角缺 face_shape 脸型。
- 主角缺 clothing_lock 服装锁定。
- 场景缺 lighting_direction 光线方向。
- 场景缺 layout_map 空间布局。
- 有对白但无 axis_line 轴线。
- 动作无 motion_path 运动轨迹。
- 机位使用 forbidden_camera 禁止机位。
- Prompt 缺角色、场景、动作、机位任一项。

## WARN 警告
- 镜头数量不在 8-12。
- 单句对白超过25中文字符。
- 缺插入镜头。
- 缺反应镜头。
- Prompt 使用“电影感、震撼、史诗级”等弱词但无具体镜头语言。
