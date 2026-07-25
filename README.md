# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.6.0`

面向 AI 短剧与 AI 漫剧生产的导演控制器、Codex Skill 和单入口生产编排器。它把小说、剧本、口述创意或半成品提示词整理成导演物料包，并继续生成资产、分镜、视频、配音和合成任务图。

当前 `run-all` 会完成本地编排、任务规划和物料导出，不会在未配置真实 Provider 时冒充已经生成图片、视频或最终成片。

## v0.6 更新

- 新增 `novel-to-drama.v1` 单入口总工作流。
- 新增 `run-all` 和 `workflow-status` 命令。
- 新增 `workflow.json` 断点状态、原文 SHA256 和阶段证据。
- 新增 `production_tasks.json`，统一描述人物资产、场景、道具、分镜图、分镜视频、TTS 和合成任务。
- 新增跳过已完成、失败重试、版本候选和人工选片策略。
- 新增 `assembly_plan.json`，输出确定性的 FFmpeg 拼接计划。
- 图像与视频任务统一路由到自有 `comfy-cloud-platform`，不绑定第三方短剧软件。
- 参考并改造 LumenX、LocalMiniDrama 的 MIT 许可实现，来源记录在 `THIRD_PARTY_NOTICES.md`。
- 未复制 ArcReel 的 AGPL 源码，也未复制 Toonflow 受补充商业条款约束的核心源码。

## 单入口总工作流

```text
小说/剧本
  -> chapter_intake 原文保护与哈希
  -> director_package 事件/资产/分镜/提示词
  -> asset_render_plan 人物/场景/道具任务
  -> storyboard_render_plan 分镜图任务
  -> video_render_plan 分镜视频任务
  -> audio_render_plan 对白/旁白任务
  -> assembly_plan FFmpeg 合成计划
  -> package_qa_export 物料 QA 与导出
```

工作流契约：

```text
workflows/novel_to_drama.v1.json
```

它是单入口工作流，但内部仍采用可替换阶段和任务依赖图。这样用户只需要启动一次，开发时又不用维护一张谁都不敢碰的巨型节点图。

## 一次运行

安装：

```bash
python -m pip install -e .
```

从小说或剧本生成完整生产计划：

```bash
short-drama-controller-v06 run-all \
  --input examples/input_script.md \
  --out demo_v06 \
  --title 镖局收徒Demo
```

查看状态：

```bash
short-drama-controller-v06 workflow-status --project demo_v06
```

断点续跑：

```bash
short-drama-controller-v06 run-all \
  --input examples/input_script.md \
  --out demo_v06 \
  --title 镖局收徒Demo \
  --resume
```

`--resume` 会跳过已经完成的阶段。若输入原文发生变化，会拒绝续跑，避免原文证据链被悄悄替换。

## 当前执行边界

### 已完成

- 小说/剧本输入与原文 SHA256。
- 导演物料包。
- 人物全身图、三视图、头像任务。
- 场景和道具参考图任务。
- 分镜图与分镜视频任务。
- 对白和旁白 TTS 任务。
- 失败重试、断点续跑和候选版本结构。
- FFmpeg 合成命令计划。
- 物料 QA 和提示词/表格导出。

### 尚未自动执行

- 未向 Comfy Cloud Manager 提交真实图像或视频任务。
- 未自动启动 RunPod GPU。
- 未下载任何模型。
- 未调用 Liblib 或其他付费 API。
- 未生成真实 TTS 音频。
- 未执行 FFmpeg 成片。

只有仓库中存在真实 Provider 代码并通过测试后，状态才允许从 `planned` 进入 `running/completed`。

## 最终交付

### 导演物料

1. 可阅读的分集剧本。
2. 人物、场景、道具资产锁定与完整生图提示词。
3. 4-15 秒生成片段计划。
4. 镜头执行表与故事板。
5. 动作轨迹、机位、轴线、发力和受力设计。
6. 首帧、图片、视频、尾帧、声音、负面与备用提示词。
7. QA 报告与平台导出表格。

### 生产编排

1. `workflow.json`：总工作流状态、阶段、重试和原文哈希。
2. `production_tasks.json`：资产、分镜、视频、音频和合成任务依赖图。
3. `assembly_plan.json`：FFmpeg 拼接顺序和输出文件。
4. 每项资产最多保留 10 个候选版本。
5. 最终选片必须经过人工确认。

## 核心生产层级

```text
episode 单集（通常2-3分钟）
  -> scene 场
    -> generation_clip 生成片段（4-15秒，通常10-15秒）
      -> shot 镜头
```

15 秒限制针对一次视频生成片段，不是完整一集。

## 主流程结构

小说章节输入后，写入 `project.yaml`：

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
story_events -> beat_map -> clip_plan -> shot_plan
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

## 任务图规则

### 角色资产链

```text
角色全身图
  -> 角色三视图
  -> 角色头像/身份参考
```

后续分镜优先使用已选三视图，其次使用全身图和头像。这个结构来自 LumenX 的角色一致性方法，并已重写成当前仓库的中英文字段契约。

### 分镜生成链

```text
角色/场景/道具资产
  -> 分镜主图
  -> 分镜视频
  -> 人工选片
```

### 合成链

```text
全部已选分镜视频 + 对白/旁白音轨
  -> FFmpeg concat
  -> 音轨混合
  -> 最终单集
```

若合成失败，必须输出 `BLOCKER`。禁止拿第一段视频冒充完整成片。

## QA Gate / 质检闸门

`export` 前自动运行物料 QA。存在 `BLOCKER` 时禁止导出。

媒体执行阶段后续还会增加第二层 QA：

- 图片身份一致性。
- 场景空间连续性。
- 首尾帧衔接。
- 视频损坏和时长检查。
- 对白、嘴型与字幕时间轴。
- 最终视频完整性。

## 项目输出

```text
demo_v06/
├─ workflow.json
├─ production_tasks.json
├─ assembly_plan.json
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

## 原有分阶段命令

```bash
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 repair --project demo_v02 --shot SH005
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

这些命令继续保留，适合只做剧本、资产、分镜或定向返修。

## Codex Skill

Codex 会读取：

```text
AGENTS.md
.agents/skills/ai-short-drama-controller/SKILL.md
```

显式调用：

```text
$ai-short-drama-controller
```

Skill 默认关闭隐式调用，避免普通讨论误触发整条生产流程。

## 测试

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v06 doctor
```

测试不得依赖网络，不得调用模型，不得启动 GPU。

## 来源与许可证

- LumenX：MIT，可移植资产、分镜和版本结构。
- LocalMiniDrama：MIT，可移植任务恢复、重试和 FFmpeg 合成思路。
- ArcReel：AGPL-3.0，只研究架构，不复制源码。
- Toonflow：存在补充商业条款，只研究产品流程，不复制核心源码。

详细来源、Commit 和版权声明见：

```text
THIRD_PARTY_NOTICES.md
```

## 版权安全

参考影视作品时，只学习结构、节奏、镜头逻辑、角色功能和可复用生产模式。不要复制原作角色名称、完整对白、具体情节、身份设定或世界观。
