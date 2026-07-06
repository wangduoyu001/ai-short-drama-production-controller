# AI Short Drama Production Controller Skill / AI短剧生产控制器Skill

## skill_name 技能名称

AI Short Drama Production Controller / AI短剧生产控制器

## purpose 用途

This skill controls AI short-drama production. It converts scripts, novel excerpts, rough ideas, reference breakdowns, or partial prompts into a constrained short-drama project with asset locks, dialogue control, shot planning, sound design, QA, repair, and export files.

本 Skill 用于控制 AI 短剧生产流程。它不是一键生成短剧，而是把剧本、小说片段、口述创意、参考片拆解或半成品提示词，整理成可控的短剧项目。

## main_entry 主入口

Codex should run v0.2 full pipeline by default:

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
```

## install 安装

```bash
python -m pip install -e .
python scripts/install_for_codex.py
```

## hard_rules 硬规则

1. All fields must use `english_name 中文字段`.
2. Always preserve `source_text 原文`.
3. Always run source coverage checks.
4. Dialogue must be bound to extracted characters.
5. Spoken dialogue must have a strong `speaker_spatial_anchor 说话人空间锚点`.
6. OS / voice-over shots must keep all visible characters silent.
7. Every shot must include shot size, camera movement, motion path, continuity locks, fallback shot, and sound fields.
8. High-risk shots may use `grid_cut_mode 宫格硬切模式` with black frame anchor.
9. Repair replaces current project files. Do not generate endless repaired copies.
10. Do not copy third-party prompt templates verbatim. Only use derived rules.

## required_outputs 必须输出

A generated project should contain:

```text
project.yaml
storyboard.md
prompts.md
qa.md
exports/v02_video_prompts.md
exports/v02_grid_prompts.md
exports/v02_shot_table.csv
exports/v02_sound_table.csv
```

## qa_gates 质检闸门

The v0.2 QA must check:

- `project_schema 项目结构校验`
- `source_coverage 原文覆盖`
- `speaker_binding 说话人绑定`
- `speaker_spatial_anchor 说话人空间锚点`
- `shot_size_jump 景别跳变`
- `camera_movement 机位运动`
- `motion_path 运动轨迹`
- `sound_design 音效字段`
- `mouth_state 嘴型状态`

## preferred_scope 推荐制作范围

Use this default scope unless the user explicitly overrides it:

```text
duration_seconds 时长秒数: 60-90
shot_count 镜头数量: 8-12
character_count 角色数量: 2-3
main_scene_count 主场景数量: 1
dialogue_rounds 对话轮数: 2-3
action_level 动作等级: low_to_medium 低到中
```

## workflow 工作流

```text
input 输入
↓
extract_assets 资产提取
↓
bind_dialogue_to_characters 说话人绑定
↓
build_shots 分镜生成
↓
attach_sound_and_prompts 音效与提示词生成
↓
validate 高级QA
↓
repair_project 返修替换
↓
export_project 平台导出
```

## codex_behavior Codex行为要求

When Codex uses this repository:

1. Read this file first.
2. Read `CODEX_INSTALL.md` second.
3. Use `python -m short_drama_controller.v02_full_cli` as the default runner.
4. Do not use v0.1 as the main workflow unless debugging compatibility.
5. Keep generated projects out of git unless explicitly requested.
