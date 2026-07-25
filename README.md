# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.6.0`

自有 AI 短剧导演控制器、Codex Skill 和单入口生产编排器。它把小说、剧本、口述创意或半成品提示词整理成导演物料，并生成资产、分镜、视频、配音与合成任务图。

`run-all` 可以只在本地生成计划，也可以把 `production_tasks.json` 导入本机 Comfy Cloud Manager。导入不等于执行，不会调用 ComfyUI `/prompt`、启动 GPU 或产生推理费用。

## 总工作流

```text
小说/剧本
  -> 原文保护与 SHA256
  -> 事件链、剧本、世界观与风格
  -> 人物/场景/道具资产锁定
  -> 节拍、片段与分镜
  -> 图片/视频/TTS 任务依赖图
  -> FFmpeg 合成计划
  -> QA 与导出
  -> 可选：导入本机 Comfy Cloud Manager
```

工作流契约：

```text
workflows/novel_to_drama.v1.json
```

用户只有一个入口，内部仍保持可替换、可续跑的阶段。否则把所有逻辑塞进一张巨型 ComfyUI 图，最终会得到一件看起来复杂、实际上没人敢维护的数字挂毯。

## 安装

需要 Python 3.10 或更高版本：

```bash
python -m pip install -e .
```

## 本地生成完整计划

```bash
short-drama-controller-v06 run-all \
  --input examples/input_script.md \
  --out demo_v06 \
  --title 镖局收徒Demo
```

## 一个命令生成并导入本机管理器

先启动 Comfy Cloud Manager，然后执行：

```bash
short-drama-controller-v06 run-all \
  --input examples/input_script.md \
  --out demo_v06 \
  --title 镖局收徒Demo \
  --manager-url http://127.0.0.1:8000
```

绑定管理器中已经存在的项目：

```bash
short-drama-controller-v06 run-all \
  --input examples/input_script.md \
  --out demo_v06 \
  --title 镖局收徒Demo \
  --manager-url http://127.0.0.1:8000 \
  --manager-project-id prj_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

导入成功后会写入：

```text
manager_import.json
```

该回执包含管理器计划编号、来源 SHA256、映射状态和 dry-run 安全证明。

## 导入已有计划

```bash
short-drama-controller-v06 sync-plan \
  --project demo_v06 \
  --manager-url http://127.0.0.1:8000
```

安全限制：

- 只允许 `http://127.0.0.1`、`http://localhost` 或 `http://[::1]`。
- 禁止公网域名、HTTPS代理地址、URL凭据、路径、查询参数和片段。
- 只调用 `/api/v1/production-plans/import`。
- 管理器必须返回 `dry_run_only=true`，否则拒绝保存回执。
- 请求体没有 `execute`、`submit`、API Key 或 Token。

## 状态与续跑

查看状态：

```bash
short-drama-controller-v06 workflow-status --project demo_v06
```

断点续跑：

```bash
short-drama-controller-v06 run-all \
  --input examples/input_script.md \
  --out demo_v06 \
  --resume
```

`--resume` 会跳过已完成阶段。输入原文发生变化时会拒绝续跑，防止证据链被悄悄替换。

## 输出

```text
demo_v06/
├─ workflow.json
├─ production_tasks.json
├─ assembly_plan.json
├─ manager_import.json        # 仅成功导入管理器后存在
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

## 任务图规则

### 角色资产

```text
角色全身图
  -> 角色三视图
  -> 角色头像/身份参考
```

### 分镜与视频

```text
角色/场景/道具资产
  -> 分镜主图
  -> 分镜视频
  -> 人工选片
```

### 音频与合成

```text
全部已选分镜视频 + 对白/旁白音轨
  -> FFmpeg concat
  -> 音轨混合
  -> 最终单集
```

合成失败必须输出 `BLOCKER`，禁止拿第一段视频冒充完整成片。

## 当前执行边界

已经完成：

- 小说/剧本输入与原文 SHA256。
- 导演物料包。
- 人物、场景、道具、分镜图、分镜视频和 TTS 任务图。
- 重试、断点续跑、候选版本和人工选片结构。
- FFmpeg 合成计划。
- Comfy Cloud Manager 本机 dry-run 导入。

尚未自动执行：

- 未创建真实生产批次。
- 未向 ComfyUI 提交 `/prompt`。
- 未启动 RunPod GPU。
- 未下载模型。
- 未调用 Liblib 或其他付费 API。
- 未生成真实 TTS。
- 未执行 FFmpeg 成片。

只有真实 Provider、工作流生产验证、媒体输出和 QA 全部通过后，状态才允许进入 `completed`。

## 原有 v02 命令

```bash
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 export --project demo_v02
```

这些命令继续保留，适合只做某个生产阶段。

## 测试

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v06 doctor
```

测试不得依赖公网，不得调用模型，不得启动 GPU。

## 来源与许可证

- LumenX：MIT，移植资产、分镜和版本结构。
- LocalMiniDrama：MIT，移植任务恢复、重试和 FFmpeg 合成思路。
- ArcReel：AGPL-3.0，只研究架构，不复制源码。
- Toonflow：存在补充商业条款，只研究产品流程，不复制核心源码。

详细来源和版权声明见 `THIRD_PARTY_NOTICES.md`。

参考影视作品时，只学习结构、节奏、镜头逻辑和角色功能，不复制原作角色名称、完整对白、具体情节或世界观。
