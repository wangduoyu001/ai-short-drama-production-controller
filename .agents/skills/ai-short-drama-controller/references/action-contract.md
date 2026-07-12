# Action contract / 动作与打戏契约

## Principle / 原则

Design physical action that can be understood frame by frame. Do not replace mechanics with effects, adjectives, or vague phrases such as “激烈交锋”“招式凌厉”“展开大战”.

动作设计必须让人看见起势、路线、接触、受力、结果和复位。一个镜头只承担一个清楚的动作节点。

## Required action fields / 动作必填字段

Every high-risk action shot must define:

- `action_id 动作编号`
- `start_state 起始状态`
- `start_pose 起始姿态`
- `footwork 步法`
- `movement_line 移动线`
- `attack_line 攻击线`
- `defense_line 防守线`
- `contact_point 接触点`
- `force_direction 受力方向`
- `body_response 身体反馈`
- `weapon_state 武器状态`
- `speed_rhythm 速度节奏`
- `end_state 结束状态`
- `reset_position 复位站位`
- `risk_level 风险等级`
- `fallback_shot 备用镜头`
- `grid_cut_prompt 宫格硬切提示词`

## Action grammar / 动作语法

Use this structure:

```text
起始姿态 -> 启动部位 -> 移动路线 -> 攻击/防守路线 -> 接触点 -> 受力反馈 -> 结束姿态 -> 下一动作接口
```

Example form, not fixed content:

```text
右脚后撤半步压低重心 -> 左肩先转带动枪尾 -> 枪尖沿胸口高度直线前送 -> 对手剑脊向外斜拨 -> 枪尖与剑脊在两人中线右侧接触 -> 剑手前臂受冲击向外展开、上身后仰半步 -> 枪手枪尖停在对手肩外、双方重新拉开一枪距离
```

## Weapon distinction / 武器差异

Weapon behavior must affect spacing, timing, and body mechanics.

### Long weapon / 长兵器

- maintains distance
- uses line control, sweeping arcs, thrusts, shaft blocks, and leverage
- requires hand spacing and rear-hand drive
- close-range disadvantage should be visible

### Sword or short weapon / 剑与短兵器

- enters inside the long weapon's effective range
- changes line with wrist and body angle
- uses deflection, borrowing force, close cuts, and rapid direction changes
- cannot casually block a heavy long-weapon strike without body displacement

### Unarmed / 徒手

- define guard, weight transfer, hip/shoulder drive, target, contact surface, and recovery
- avoid impossible floating impacts or unexplained knockback

## Shot coverage / 镜头覆盖

A readable fight clip normally uses functional coverage such as:

1. `wide geography 全景空间建立`
2. `intent 起势与意图`
3. `approach 接近与步法`
4. `contact 接触点`
5. `defense 防守反馈`
6. `counter 反击`
7. `off_balance 失衡`
8. `reaction 反应`
9. `environment_feedback 环境反馈`
10. `reset/hook 复位或钩子`

Do not force all ten nodes into every clip. Select only the nodes needed for the story result and model duration.

## Camera rules / 动作机位规则

- Establish geography before rapid cutting.
- Preserve the attacker's screen direction through the contact sequence.
- Put the contact point inside the frame, not outside an ambiguous crop.
- Do not combine a complex full-body action with an aggressive orbit unless the blocking is extremely simple.
- Use inserts for grip, footwork, blade contact, cloth pull, impact debris, or injury details.
- Return to a wider result shot after a close contact sequence when the new positions matter.

## Rhythm / 节奏

Use contrast:

- stillness before launch
- fast attack
- short contact hold or perceptible impact beat
- reaction
- reposition

Continuous uniform speed reads as weightless. Leave micro-pauses where intention, contact, or consequence must be understood.

## Fallback design / 降级方案

Every complex action must have a simpler fallback preserving the same narrative result.

Preferred fallback patterns:

- replace continuous choreography with hard-cut action nodes
- show attack setup -> contact insert -> opponent reaction -> result wide
- replace complex camera motion with fixed or slight lateral camera
- reduce simultaneous actors
- separate weapon action and environmental destruction
- imply the most unstable motion through sound, shadow, debris, or reaction only when the result remains clear

Fallback is not permission to remove the dramatic consequence.

## Safety and generation clarity / 安全与生成清晰度

- Avoid instructions that require real-world dangerous performance.
- Keep prompts focused on fictional cinematic depiction.
- For generation models, describe one primary action per shot and reserve later actions explicitly.
- Do not ask the model to finish the entire fight early.
