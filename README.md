# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.5.0`

面向 AI 短剧与 AI 漫剧生产的流程控制器和 Codex Skill。它不是“一键生成短剧”的玄学按钮，而是把小说、剧本、口述创意或半成品 Prompt / 生成提示词，整理成导演可用的标准化生产物料包。

## v0.5 更新

- 新增 Codex 原生 Skill：`.agents/skills/ai-short-drama-controller/`
- 新增项目级 `AGENTS.md`
- 新增资产、故事板、动作打戏三套执行契约
- 新增 `doctor` 环境与 Skill 自检命令
- 明确 `episode 单集` 与 `generation_clip 生成片段` 的层级
- 关闭 Skill 隐式调用，避免普通聊天误触发整条生产流程
- 保持原有 Python CLI、QA 阻断、返修覆盖和导出结构

## 最终交付是什么

本项目最终交付的是一个可继续返修的导演物料包：

1. 可阅读的分集剧本
2. 人物、场景、道具资产锁定与完整生图提示词
3. 4-15秒生成片段计划
4. 镜头执行表与故事板
5. 动作轨迹、机位、轴线、发力和受力设计
6. 首帧、图片、视频、尾帧、声音、负面与备用提示词
7. QA 报告与可导出物料

它不会凭空替你调用 Seedance、即梦、可灵、Veo 或其他外部平台，也不会声称已经生成最终成片。平台和模型是否接入，以仓库中是否存在真实集成代码为准。

## 核心生产层级

```text
episode 单集（通常2-3分钟）
  -> scene 场
    -> generation_clip 生成片段（4-15秒，通常10-15秒）
      -> shot 镜头
```

15 秒限制针对的是一次视频生成片段，不是完整一集。把这两个概念混在一起，后面的分镜、时长和剪辑都会一起变成一锅很有技术感的粥。

## Codex App / Codex CLI 使用

Codex 会从仓库根目录读取：

```text
AGENTS.md
.agents/skills/ai-short-drama-controller/SKILL.md
```

打开本仓库后，显式调用：

```text
$ai-short-drama-controller
```

示例指令：

```text
$ai-short-drama-controller
把我提供的小说改成3分钟一集的AI漫剧剧本。
本次只做剧本改写，不生成资产和分镜。
画幅16:9，写实古装武侠电影质感。
```

Skill 默认关闭隐式调用，因此必须明确选择或输入 `$ai-short-drama-controller`。这样普通讨论不会突然生成十几份生产文件。

## 安装与自检

需要 Python 3.10 或更高版本。

```bash
python -m pip install -e .
short-drama-controller-v02 doctor
```

`doctor` 会检查：

- Python 版本
- CLI 主入口模块
- 根目录 `AGENTS.md`
- Codex Skill 的 YAML frontmatter
- `agents/openai.yaml` 元数据

## 主入口

`short-drama-controller-v02` 指向：

```text
short_drama_controller.v02_full_cli:main
```

主流程命令：

```bash
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 repair --project demo_v02 --shot SH005
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

未安装时使用：

```bash
python -m short_drama_controller.v02_full_cli doctor
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

## 主流程结构

小说章节输入后，先生成并写入 `project.yaml`：

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
clip_plan 生成片段计划
shot_plan 分镜计划
coverage_qa 关键实体覆盖QA
```

分镜必须基于：

```text
story_events 事件链 -> beat_map 剧情节拍表 -> clip_plan 生成片段计划 -> shot_plan 分镜计划
```

每个 shot 必须绑定：

```text
source_quote 原文证据
event_id 事件编号
beat_id 节拍编号
clip_id 生成片段编号
scene_id 场景编号
character_id 角色编号
prop_id 道具编号
entry_pose 起始姿态
exit_pose 结束姿态
motion_path 运动轨迹
```

动作或打戏镜头还必须包含：

```text
attack_line 攻击线
defense_line 防守线
contact_point 接触点
force_direction 受力方向
body_response 身体反馈
reset_position 复位站位
fallback_shot 备用镜头
```

## 分阶段执行

Codex Skill 遵守“只执行用户明确要求的阶段”：

```text
rewrite 剧本改写
assets 资产提取
clips 生成片段拆分
storyboard 故事板
prompts 生成提示词
qa 质检返修
export 导出
```

用户只要求视频提示词时，不会顺手附赠人物小传、行业分析、制作感悟和另外八份 Markdown。那些东西通常只是文档数量在努力假装生产力。

## QA Gate / 质检闸门

`export` 前必须自动运行 QA。只要存在 `BLOCKER`，禁止导出。

`qa.md` 必须记录：

```text
qa_status 质检状态
allow_export 允许导出
blocker_count 阻塞问题数
warning_count 警告问题数
```

返修规则：

- 返修直接覆盖原目标文件或目标镜头
- 禁止生成 `final_v2`、`fixed`、`最新版` 等重复文件
- 单次定向返修只改变一个主要变量
- 高风险镜头必须保留备用镜头

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

视频提示词统一导出为：

```text
exports/video_prompts.md
```

## Codex Skill 目录

```text
.agents/skills/ai-short-drama-controller/
├─ SKILL.md
├─ agents/
│  └─ openai.yaml
└─ references/
   ├─ asset-contract.md
   ├─ storyboard-contract.md
   └─ action-contract.md
```

- `SKILL.md`：触发范围、生产阶段、工作流和输出控制
- `asset-contract.md`：人物三视图、场景和道具资产标准
- `storyboard-contract.md`：机位、轴线、人物运动轨迹和连续性标准
- `action-contract.md`：武器、步法、攻击线、接触点、受力和备用方案

## 测试

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
```

测试不得依赖网络。Smoke test 默认使用临时目录；传入 `--out` 时写入指定目录，不删除仓库固定目录。

## 版权安全

参考影视作品时，只学习结构、节奏、镜头逻辑、角色功能和可复用的生产模式。不要复制原作的角色名称、完整对白、具体情节、身份设定或世界观。
