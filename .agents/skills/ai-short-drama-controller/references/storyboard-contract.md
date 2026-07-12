# Storyboard contract / 故事板契约

## Goal / 目标

The storyboard must communicate how the shot is executed, not merely describe a pretty image.

故事板必须让人看懂：摄影机在哪里、人物从哪里到哪里、谁朝哪个方向发力、动作结果落在哪里、前后镜头如何衔接。

## Required hierarchy / 强制层级

```text
episode 单集
  -> scene 场
    -> generation_clip 生成片段（4-15秒）
      -> shot 镜头
```

Do not use `episode 单集` and `generation_clip 生成片段` as synonyms.

## Required shot fields / 镜头必填字段

Every shot must contain:

- `shot_id 镜头编号`
- `clip_id 生成片段编号`
- `source_quote 原文证据`
- `event_id 事件编号`
- `beat_id 节拍编号`
- `scene_id 场景编号`
- `character_id 角色编号`
- `prop_id 道具编号`
- `duration_seconds 镜头时长`
- `shot_purpose 镜头目的`
- `shot_size 景别`
- `camera_angle 机位角度`
- `camera_position 摄影机位置`
- `camera_movement 机位运动`
- `camera_axis 轴线`
- `safe_camera_zone 安全机位区`
- `screen_direction 画面方向`
- `eyeline 视线方向`
- `entry_pose 起始姿态`
- `exit_pose 结束姿态`
- `start_position 起点`
- `end_position 终点`
- `movement_path 运动轨迹`
- `layer_depth 前中后景`
- `prop_anchor 道具锚点`
- `first_frame 首帧`
- `end_frame 尾帧`
- `continuity_locks 连续性锁定`
- `fallback_shot 备用镜头`

Action shots add the fields listed in `action-contract.md`.

## Axis and screen direction / 轴线与画面方向

- Establish the conflict axis in a master or neutral shot.
- Keep the camera on one side of the axis during an exchange.
- Preserve entry/exit direction across cuts.
- A character leaving frame right should not appear moving frame left in the next shot unless the geography or reversal is explicitly established.
- To cross the axis, use a neutral frontal shot, visible camera move across the line, or a new establishing shot.

## Shot progression / 镜头推进

Avoid consecutive shots that perform the same visual function.

Bad sequence:

```text
medium front -> medium front -> medium front
```

Better sequence:

```text
wide geography -> close intention -> medium exchange -> insert contact -> reaction -> wide result
```

Jump cuts should change at least one meaningful dimension:

- shot-size group
- camera side within the safe zone
- subject
- information function
- action node
- emotional point of view

Do not vary shots merely to increase the count.

## Camera movement / 运镜

Use the simplest movement that communicates the event.

Default safe movements:

- `fixed_camera 固定机位`
- `slow_push_in 缓慢推进`
- `slight_lateral_move 轻微横移`
- `subtle_handheld 轻微手持`

Use orbit, crane, whip pan, long tracking, or complex one-shot movement only when spatial anchors and action timing are explicit. Complex movement must not hide unclear blocking.

## Storyboard sketch / 故事板草图

A human-readable sketch or grid must mark:

- frame border and aspect ratio
- camera symbol and movement arrow
- character symbols and facing direction
- start/end positions
- movement arrows
- attack and force arrows for action
- contact point
- foreground, midground, background
- fixed scene anchors
- shot number and duration

Text labels must remain sparse. The sketch is a spatial diagram, not a paragraph pasted into a box.

## Continuity handoff / 连续性接口

For adjacent clips, record:

- previous observed end state
- next planned start state
- face, costume, hairstyle, prop and scene locks
- character screen positions
- body orientation
- hand and weapon state
- light direction
- camera side

If the generated result differs from the planned end state, update the observed state before writing the next prompt. Reality, as usual, has declined to obey the planning document.

## Storyboard delivery / 故事板交付

A complete storyboard delivery should include only what the requested stage needs:

1. storyboard overview / 分镜总览
2. shot execution table / 镜头执行表
3. spatial/action sketch for high-risk shots / 高风险镜头空间动作草图
4. corresponding generation prompt / 对应生成提示词

Do not add editing essays, repeated narrative summaries, or unrelated asset descriptions.
