# AI Short Drama Production Controller / AI短剧生产控制器

面向 AI 短剧生产的流程控制 Skill。它不是“一键生成短剧”的玄学按钮，而是把参考片、剧本、小说片段、口述创意或半成品 Prompt，压缩成可控范围，再生成稳定的资产、草图分镜、镜头表和平台提示词。

## core_features 核心功能

- `scope_gate 范围闸门`：一开始限制项目大小，防止项目爆炸。
- `input_normalize 输入标准化`：兼容参考片、剧本、小说片段、创意、半成品。
- `feasibility_gate 可生成性闸门`：检查故事、动作、场景、运动轨迹、机位、Prompt 是否清晰。
- `asset_lock 资产锁定`：控制人物脸、服装、道具、场景、色卡一致性。
- `blocking_plan 人物调度计划`：控制正反打、视线、轴线、站位。
- `motion_plan 运动轨迹计划`：控制人物从哪里到哪里、怎么动。
- `camera_plan 机位计划`：限制机位运动，避免复杂运镜崩坏。
- `storyboard_sketch 草图分镜`：用草图字段控制人物、机位、视线、运动箭头。
- `qa_gate 质检闸门`：PASS / WARN / BLOCKER。
- `repair_replace 返修替换`：返修后覆盖原文件，不制造垃圾文档。
- `export_pack 平台导出`：导出 LibTV、Lovart、通用 Prompt 和剪辑表。

## install 安装

```bash
python -m pip install -e .
```

## quick_start 快速开始

```bash
python -m short_drama_controller init --input examples/input_script.md --out demo_project --title 镖局收徒Demo
python -m short_drama_controller qa --project demo_project
python -m short_drama_controller repair --project demo_project
python -m short_drama_controller export --project demo_project
```

## output 项目输出

```text
demo_project/
├─ project.yaml
├─ script.md
├─ assets.md
├─ storyboard.md
├─ prompts.md
├─ qa.md
└─ exports/
   ├─ libtv_prompts.md
   ├─ lovart_prompts.md
   ├─ shot_table.csv
   └─ edit_list.csv
```

## field_rule 字段规则

所有字段采用：

```text
english_name 中文字段
```

例如：

```text
character_id 角色编号
camera_movement 机位运动
motion_path 运动轨迹
continuity_locks 连续性锁定
```
