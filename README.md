# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.4.0`

面向 AI 短剧生产的流程控制 Skill / 技能。它不是“一键生成短剧”的玄学按钮，而是把剧本、小说章节、口述创意或半成品 Prompt / 生成提示词，整理成导演可用的标准化生产物料包。

## 主入口

`short-drama-controller-v02` 必须指向：

```text
short_drama_controller.v02_full_cli:main
```

安装后推荐命令：

```bash
python -m pip install -e .
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

未安装时等价命令：

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

## 主流程结构

小说章节输入后，必须先生成并写入 `project.yaml`：

```text
chapter_intake 章节解析
story_events 事件链
characters 角色列表
scenes 场景列表
props 道具列表
world_bible 世界观
style_bible 风格圣经
asset_lock 资产锁定
beat_map 剧情节拍表
shot_plan 分镜计划
coverage_qa 关键实体覆盖QA
```

分镜必须基于：

```text
story_events 事件链 -> beat_map 剧情节拍表 -> shot_plan 分镜计划
```

每个 shot 必须绑定：

```text
source_quote 原文证据
event_id 事件编号
beat_id 节拍编号
scene_id 场景编号
character_id 角色编号
prop_id 道具编号
```

## QA Gate

`export` 前必须自动运行 QA。只要存在 `BLOCKER`，禁止导出。

`qa.md` 必须记录：

```text
qa_status 质检状态
allow_export 允许导出
blocker_count 阻塞问题数
warning_count 警告问题数
```

## 导出文件名

统一使用：

```text
exports/video_prompts.md
```

禁止混用：

```text
exports/v02_video_prompts.md
```

## 项目输出

```text
demo_v02/
├─ project.yaml
├─ script.md
├─ chapter_intake.md
├─ story_events.md
├─ world_bible.md
├─ style_bible.md
├─ characters.md
├─ three_views.md
├─ scene_plan.md
├─ coverage_qa.md
├─ assets.md
├─ storyboard.md
├─ producer.md
├─ sound.md
├─ prompts.md
├─ qa.md
└─ exports/
   ├─ first_frame_prompts.md
   ├─ image_prompts.md
   ├─ video_prompts.md
   ├─ end_frame_prompts.md
   ├─ negative_prompts.md
   ├─ fallback_shots.md
   ├─ grid_prompts.md
   ├─ batch_inference.md
   ├─ shot_table.csv
   ├─ sound_table.csv
   ├─ producer_table.csv
   ├─ action_table.csv
   ├─ shot_inference_table.csv
   ├─ batch_inference_table.csv
   └─ grid_strategy_table.csv
```

## 测试

```bash
pytest -q
python scripts/v02_smoke.py
python scripts/v02_smoke.py --out /tmp/v02_smoke_out
```

smoke test 默认使用临时目录；传入 `--out` 时写入指定目录，不删除仓库固定目录。
