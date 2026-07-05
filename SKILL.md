# AI Short Drama Production Controller / AI短剧生产控制器

## purpose 目的

Use this skill to control AI short drama production workflows. It converts reference videos, scripts, novel excerpts, rough ideas, or partial prompts into a constrained, producible short-drama project with locked assets, storyboard sketches, shot plans, platform prompts, QA reports, and repair actions.

使用本 Skill 时，必须优先稳定性，不追求“一键大片”。任何输入都要先过范围限制，再做资产、分镜、提示词和质检。

## hard_rules 硬规则

1. All output fields must use `english_name 中文字段`.
2. Always run `scope_gate 范围闸门` first.
3. If the project is too large, reduce it immediately before generating anything.
4. Keep only six core project files: `project.yaml`, `script.md`, `assets.md`, `storyboard.md`, `prompts.md`, `qa.md`.
5. Repair must replace the target file, not create endless repaired copies.
6. Lock assets before shot planning.
7. Every dialogue scene must have blocking, eyeline, axis line, and safe camera zone.
8. Every motion must have start position, end position, direction, speed, and fallback.
9. v0.1 only allows these camera movements: `fixed_camera 固定机位`, `slow_push_in 缓慢推进`, `slight_lateral_move 轻微横移`, `subtle_handheld 轻微手持`.
10. High-risk shots must have `fallback_shot 备用镜头`.

## default_production_mode 默认制作模式

Use `fast_demo 快速样片模式` unless the user explicitly requests another mode.

Default limits:

- `duration_seconds 时长秒数`: 60-90
- `shot_count 镜头数量`: 8-12
- `character_count 角色数量`: 2-3
- `main_scene_count 主场景数量`: 1
- `dialogue_rounds 对话轮数`: 2-3
- `action_level 动作等级`: low_to_medium 低到中
- `episode_count 集数`: 1

## workflow 工作流

1. `scope_gate 范围闸门`
2. `input_normalize 输入标准化`
3. `feasibility_gate 可生成性闸门`
4. `story_repair 故事修复`
5. `asset_lock 资产锁定`
6. `asset_reuse_plan 资产复用计划`
7. `blocking_plan 人物调度计划`
8. `motion_plan 运动轨迹计划`
9. `camera_plan 机位计划`
10. `storyboard_sketch 草图分镜`
11. `shot_plan 分镜计划`
12. `prompt_build 提示词生成`
13. `prompt_clarity_gate 提示词清晰度闸门`
14. `qa_gate 质检闸门`
15. `repair_replace 返修替换`
16. `export_pack 平台导出`

## copyright_safety 版权安全

When input is a reference film, learn only structure, rhythm, shot logic, character function, and reusable production pattern. Do not copy exact names, dialogue, plot, character identity, or worldbuilding.
