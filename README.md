# AI Short Drama Production Controller / AI短剧生产控制器

面向 AI 短剧生产的流程控制 Skill。它不是“一键生成短剧”的玄学按钮，而是把参考片、剧本、小说片段、口述创意或半成品 Prompt，压缩成可控范围，再生成稳定的资产、草图分镜、镜头表和平台提示词。

## core_features 核心功能

- `scope_gate 范围闸门`：一开始限制项目大小，防止项目爆炸。
- `input_normalize 输入标准化`：兼容参考片、剧本、小说片段、创意、半成品。
- `asset_lock 资产锁定`：控制人物脸、服装、道具、场景、色卡一致性。
- `dialogue_control 对白控制`：区分 OS 画外音与出口对白，控制嘴型。
- `blocking_plan 人物调度计划`：控制正反打、视线、轴线、站位。
- `motion_plan 运动轨迹计划`：控制人物从哪里到哪里、怎么动。
- `camera_plan 机位计划`：限制机位运动，避免复杂运镜崩坏。
- `sound_design 声音设计`：输出环境底音、拟音、道具音、动作音、音乐建议。
- `grid_cut_mode 宫格硬切模式`：高风险镜头使用黑屏冻结锚与硬切分格。
- `qa_gate 质检闸门`：PASS / WARN / BLOCKER。
- `repair_replace 返修替换`：返修后覆盖当前项目文件，不制造垃圾文档。
- `export_pack 平台导出`：导出视频提示词、宫格提示词、分镜表、音效表。

## install 安装

```bash
python -m pip install -e .
```

## v0.1 quick_start 快速开始

```bash
python -m short_drama_controller init --input examples/input_script.md --out demo_project --title 镖局收徒Demo
python -m short_drama_controller qa --project demo_project
python -m short_drama_controller repair --project demo_project
python -m short_drama_controller export --project demo_project
```

## v0.2 quick_start 快速开始

v0.2 作为独立入口存在，不直接覆盖 v0.1。

```bash
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

不安装时也可以：

```bash
python -m short_drama_controller.v02_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
```

## v0.2 output 项目输出

```text
demo_v02/
├─ project.yaml
├─ storyboard.md
├─ prompts.md
├─ qa.md
└─ exports/
   ├─ v02_video_prompts.md
   ├─ v02_grid_prompts.md
   ├─ v02_shot_table.csv
   └─ v02_sound_table.csv
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
ambience_sfx 环境底音
speaker_mode 发声模式
mouth_state 嘴型状态
```

## smoke_test 烟雾测试

```bash
python scripts/v02_smoke.py
```

GitHub Actions 会在 push / PR 时运行 v0.2 smoke test。
