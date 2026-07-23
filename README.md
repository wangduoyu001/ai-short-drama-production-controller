# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.6.0`

面向 AI 短剧、AI 漫剧和本地信息流混剪的生产控制器与 Codex Skill。它不是一个写着“一键成片”却把问题藏进按钮里的演示，而是把剧本、资产、镜头、提示词和本地素材粗剪拆成可执行、可返修、可审核的生产流程。

## v0.6 更新

新增独立的文案驱动本地混剪模块：

```text
short_drama_controller/script_mixer/
```

当前已实现：

- `script-driven-mixer` 命令行入口
- FFmpeg、FFprobe、Ollama、Whisper CLI、ComfyUI 模型目录和常见模型缓存自动发现
- 软件和模型路径默认留空，不提交本机绝对路径
- 本地视频目录增量扫描
- 每个原视频默认只处理前40秒，超过部分不切镜、不分析、不向量化
- 原视频总时长、实际入库时长和忽略尾部分开记录
- FFprobe 元数据和原视频音轨识别
- FFmpeg 场景切分和固定窗口回退
- 镜头关键帧缩略图
- SQLite 原视频、镜头、使用历史和向量缓存
- Ollama 文本、视觉和嵌入模型能力检测与自动选择
- 文案转直接画面、隐喻画面、情绪、标签、景别和负向约束
- 关键帧视觉描述、水印识别和画质评分
- 镜头语义向量增量构建
- 词义、标签、情绪、景别、向量、画质和历史使用融合检索
- 多来源时间线编排
- 相邻同源、来源冷却、单来源占比和低匹配审核
- 真实配音、原视频音频、二者混合和静音模式
- 本地 Whisper 词级时间戳和用户原文对齐
- SRT、ASS 和逐字卡拉OK ASS 字幕
- FFmpeg 音频混合、自动压低、字幕烧录和预览成片
- Python 3.10/3.12 CI 测试工作流

详细开发契约：

```text
docs/script-driven-mixer.md
```

后续开发路线：

```text
docs/script-mixer-next-development-plan.md
```

## v0.5 能力

- Codex 原生 Skill：`.agents/skills/ai-short-drama-controller/`
- 项目级 `AGENTS.md`
- 资产、故事板、动作打戏执行契约
- `doctor` 环境与 Skill 自检
- 明确 `episode 单集` 与 `generation_clip 生成片段` 层级
- 保留 Python CLI、QA 阻断、返修覆盖和导出结构

## 两条独立生产链

### AI 短剧导演物料链

输入小说、剧本、口述创意或半成品提示词，输出：

1. 可阅读分集剧本
2. 人物、场景和道具资产锁定
3. 4-15 秒生成片段计划
4. 镜头执行表与故事板
5. 动作轨迹、机位、轴线、发力和受力设计
6. 首帧、图片、视频、尾帧、声音、负面和备用提示词
7. QA 报告与可导出物料

它不会凭空替你调用 Seedance、即梦、可灵、Veo 或其他外部平台。平台是否接入，以仓库是否存在真实集成代码为准。

### 文案驱动本地混剪链

输入文案，可选真实配音，输出：

```text
本地原视频
→ 每个素材只取前40秒处理窗口
→ 场景切分和视觉分析
→ 本地素材库

文案
→ 语义单元
→ 可选Whisper真实时间轴
→ 画面意图
→ 本地素材检索
→ 多来源编排
→ 音频混合
→ SRT/ASS/逐字字幕
→ 时间线与审核报告
→ FFmpeg预览成片
```

40秒限制针对每个原始素材，不限制最终成片时长。最终视频仍可组合多个来源。

它是独立的本地粗剪子系统，不改变短剧导演物料链的输出契约。

## 核心短剧生产层级

```text
episode 单集（通常2-3分钟）
  -> scene 场
    -> generation_clip 生成片段（4-15秒，通常10-15秒）
      -> shot 镜头
```

15 秒限制针对一次视频生成片段，不是完整一集。把两者混在一起，时长、分镜和剪辑会一起变成一锅很有技术感的粥。

## 安装

需要 Python 3.10 或更高版本。

```bash
python -m pip install -e .
```

安装后提供三个入口：

```text
short-drama-controller
short-drama-controller-v02
script-driven-mixer
```

## Codex App / Codex CLI

Codex 会读取：

```text
AGENTS.md
.agents/skills/ai-short-drama-controller/SKILL.md
```

显式调用短剧 Skill：

```text
$ai-short-drama-controller
```

示例：

```text
$ai-short-drama-controller
把我提供的小说改成3分钟一集的AI漫剧剧本。
本次只做剧本改写，不生成资产和分镜。
画幅16:9，写实古装武侠电影质感。
```

Skill 默认关闭隐式调用，避免普通讨论突然生成十几份生产文件。

# AI短剧控制器

## 自检

```bash
short-drama-controller-v02 doctor
```

检查：

- Python 版本
- CLI 主入口
- 根目录 `AGENTS.md`
- Codex Skill YAML frontmatter
- `agents/openai.yaml`

## 主流程命令

```bash
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 repair --project demo_v02 --shot SH005
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

未安装时：

```bash
python -m short_drama_controller.v02_full_cli doctor
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

## 短剧主流程

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

每个镜头保留：

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

动作镜头还必须包含：

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

```text
rewrite 剧本改写
assets 资产提取
clips 生成片段拆分
storyboard 故事板
prompts 生成提示词
qa 质检返修
export 导出
```

只执行用户明确要求的阶段。用户只要视频提示词时，不附赠人物小传、行业感悟和另外八份 Markdown。文档数量不等于生产力，虽然很多项目努力假装是。

## QA Gate

`export` 前自动运行 QA。存在 `BLOCKER` 时禁止导出。

```text
qa_status 质检状态
allow_export 允许导出
blocker_count 阻塞问题数
warning_count 警告问题数
```

返修覆盖原目标文件或镜头，禁止生成 `final_v2`、`fixed`、`最新版` 等重复文件。

# 文案驱动本地混剪

## 第一次在实际电脑运行

### 1. 生成本地配置

```bash
script-driven-mixer init-config --out script_mixer.local.json
```

所有模型名称默认留空，通过本地能力和缓存自动选择。配置文件已被 `.gitignore` 忽略。

默认源视频窗口：

```json
{
  "media_scan": {
    "maximum_source_process_seconds": 40.0
  }
}
```

### 2. 扫描软件和模型目录

```bash
script-driven-mixer --config script_mixer.local.json doctor
```

检查：

- FFmpeg 与 FFprobe
- Ollama
- Whisper CLI
- Python、Git、NVIDIA SMI
- Ollama、Hugging Face、Whisper 和 ComfyUI 模型目录

结果：

```text
.runtime/script_mixer/discovery.json
```

### 3. 查看模型能力

```bash
script-driven-mixer --config script_mixer.local.json models
```

显示 Ollama 模型能力，以及 Whisper CLI、本地权重和自动选择结果。默认不自动下载 Whisper 模型。

### 4. 初始化素材数据库

```bash
script-driven-mixer --config script_mixer.local.json init-db
```

### 5. 扫描素材目录

完整扫描：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow"
```

大素材库先快速入库：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow" \
  --fast
```

快速模式使用固定窗口切镜，不做场景检测和缩略图，但同样只处理每个素材的前40秒。之后直接运行普通扫描即可自动升级。

可选：

```text
--force          强制重新分析
--prune-missing  清理已从该目录删除的数据库索引
```

原视频始终只读。`--prune-missing` 不删除磁盘文件。

### 6. 检查素材库

```bash
script-driven-mixer --config script_mixer.local.json catalog-status
```

显示：

- 原视频与镜头数量。
- 原始素材总时长。
- 实际入库总时长。
- 被忽略尾部总时长。
- 被40秒规则截断的素材数量。
- 音轨、缩略图、视觉分析和向量缓存数量。

### 7. 分析关键帧

```bash
script-driven-mixer --config script_mixer.local.json enrich-media --limit 100
script-driven-mixer --config script_mixer.local.json enrich-media
```

视觉模型写入主体、场景、动作、情绪、标签、景别、镜头运动、水印和画质。由于素材库不存在40秒后的镜头，视觉分析不会读取尾部。

### 8. 构建素材向量

```bash
script-driven-mixer --config script_mixer.local.json build-embeddings \
  --limit 500 \
  --batch-size 32

script-driven-mixer --config script_mixer.local.json build-embeddings
```

缓存按 `clip_id + embedding_model + content_hash` 管理。内容未变化时不会重复计算。

## 常用剪辑命令

### 保留原视频音频

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --audio-mode source \
  --project-id source_demo \
  --render
```

### 使用真实配音并自动逐句对齐

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --project-id narration_demo \
  --render
```

### 配音与原声混合，烧录逐字字幕

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode mixed \
  --voice voice.wav \
  --burn-subtitles \
  --project-id mixed_demo \
  --render
```

### 复用已有 Whisper JSON

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --transcript-json voice.json \
  --burn-subtitles \
  --render
```

### 指定本地 Whisper 权重

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --whisper-model "D:/Models/Whisper/medium.pt" \
  --render
```

### 禁止本次 Whisper 转写

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --no-transcribe \
  --render
```

此时仍以配音真实总时长为准，但每句按文案长度比例分配。

### 只生成 FFmpeg 命令

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode mixed \
  --voice voice.wav \
  --burn-subtitles \
  --render \
  --dry-run
```

## 混剪默认规则

| 规则 | 默认值 |
|---|---:|
| 单个原视频处理窗口 | 前40秒 |
| 画幅 | 1080×1920 |
| 帧率 | 30 |
| 最少原素材来源 | 8 |
| 推荐来源 | 12 |
| 单来源最大占比 | 15% |
| 单来源累计时长 | 4秒 |
| 单段连续镜头 | 3秒 |
| 最短镜头 | 0.7秒 |
| 来源再次出现间隔 | 3个镜头 |
| 低匹配阈值 | 0.45 |

规则无法满足时，时间线保留警告，并在 `report.json` 中阻止正式导出。

## 混剪输出

```text
outputs/script_mixer/<project_id>/
├─ script.txt
├─ script_units.json
├─ visual_intents.json
├─ candidates.json
├─ transcript.json
├─ alignment.json
├─ timeline.json
├─ report.json
├─ render_plan.json
├─ subtitles/
│  ├─ captions.srt
│  ├─ captions.ass
│  └─ captions.karaoke.ass
└─ exports/
   └─ final.mp4
```

`transcript.json` 和逐字字幕只在成功获得转写时间证据时生成。

`report.json` 记录：

```text
unique_source_count 唯一来源数量
highest_single_source_ratio 最高单来源占比
low_match_segments 低匹配镜头
source_audio_coverage 原声覆盖率
timing_source 时间来源
alignment_coverage 文案转写对齐覆盖率
subtitle_review_required 字幕是否需要人工复核
warnings 规则放宽和风险
allow_final_export 是否允许正式导出
```

素材库状态额外记录：

```text
original_duration_seconds 原始总时长
indexed_duration_seconds 实际入库时长
ignored_tail_seconds 忽略尾部时长
capped_source_count 被40秒限制截断的素材数
```

Whisper 只提供时间证据。字幕正文始终使用用户输入原文，不使用识别错字覆盖原稿。

# Codex Skill 目录

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

# 测试

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
script-driven-mixer --help
```

混剪专项：

```bash
pytest -q tests/test_script_mixer*.py
```

专项测试不依赖网络、FFmpeg、FFprobe、Ollama、Whisper、真实模型或私人素材。GitHub Actions 在 Python 3.10 和 3.12 下执行。

当前测试还验证：

- 95秒素材只入库前40秒。
- 所有镜头 `source_end <= 40.0`。
- 场景检测命令包含40秒终止参数。
- 切换配置后旧索引自动升级。
- 快速扫描和完整扫描都遵守40秒规则。

# 版权安全

参考影视作品时，只学习结构、节奏、镜头逻辑、角色功能和可复用生产模式，不复制角色名称、完整对白、具体情节、身份设定或世界观。

多来源混剪、低文本相似度、短镜头、关闭原声和语义重写都不等于获得版权授权。素材来源、授权状态和最终发布责任必须保留人工审核。
