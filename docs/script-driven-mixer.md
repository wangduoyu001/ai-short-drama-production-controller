# Script-driven local mixer / 文案驱动本地混剪

## 目标

用户输入文案，系统根据文案含义从本地素材库匹配画面，生成多来源时间线，并按项目需要使用真实配音、原视频音频、二者混合或静音。

本模块不硬编码软件、模型、素材盘符或缓存路径。仓库拉取到实际电脑后，先扫描运行环境；自动发现失败时，再使用本地忽略配置覆盖路径。

## 源视频处理窗口

每个原视频默认只处理前40秒：

```text
0秒 ～ min(原视频实际时长, 40秒)
```

40秒后的尾部不进行场景检测、不生成缩略图、不进入视觉分析、不构建向量，也不能被时间线引用。该限制针对每个原始素材，不限制最终成片总时长。

数据库同时保留：

- `duration`：原视频实际总时长。
- `indexed_duration`：实际入库时长，默认最多40秒。
- `ignored_tail_seconds`：被忽略的尾部时长。

配置：

```json
{
  "media_scan": {
    "maximum_source_process_seconds": 40.0
  }
}
```

完整后续路线见：

```text
docs/script-mixer-next-development-plan.md
```

## 当前完整流水线

```text
本地原视频
→ FFprobe 元数据和音轨识别
→ 每个源视频截取前40秒处理窗口
→ FFmpeg 场景切分
→ 关键帧缩略图
→ 本地视觉模型描述
→ 本地语义向量
→ SQLite 素材库

用户文案
→ 文案语义单元
→ 直接/隐喻画面意图
→ 文本和向量混合召回
→ 多来源全局编排
→ 时间线

可选真实配音
→ FFprobe 真实总时长
→ 本地 Whisper 词级时间戳
→ 用户原文与转写单调对齐
→ 真实句级和逐字时间
→ SRT / ASS / 卡拉OK ASS

时间线 + 音频 + 字幕
→ FFmpeg 渲染
→ MP4 + 可追溯报告
```

## 已实现能力

### 素材入库

- Windows、macOS、Linux 软件和模型位置发现。
- FFmpeg、FFprobe、Ollama、Whisper CLI、Python、Git、NVIDIA SMI 探测。
- Ollama、Hugging Face、Whisper、ComfyUI 常见模型目录扫描。
- FFprobe 读取时长、画幅、旋转、帧率、编码和音轨状态。
- 本地视频目录递归扫描。
- 文件指纹、增量更新、变化检测和丢失索引清理。
- 每个源视频默认只分析前40秒。
- FFmpeg 场景变化检测。
- 场景检测失败时固定窗口切分。
- 镜头中点缩略图。
- 快速扫描与完整扫描升级。
- 原视频只读，不移动、不删除、不覆盖。

### 画面理解和检索

- Ollama 模型能力读取。
- 文本、视觉和嵌入模型自动选择。
- 无模型时规则式画面意图回退。
- 关键帧主体、场景、动作、情绪、标签、景别、运动、水印和画质分析。
- Ollama 批量嵌入。
- SQLite 增量向量缓存。
- 文案实时向量化。
- 文本、标签、情绪、景别、画质、向量和历史使用融合评分。
- 原声模式对有音轨素材给予小幅奖励，但不覆盖画面语义。

### 时间线和混剪约束

- 相邻镜头禁止同源。
- 来源再次出现冷却。
- 单来源累计时长和占比限制。
- 单段连续镜头时长限制。
- 历史使用惩罚。
- 低匹配镜头和规则放宽报告。
- 原始来源、源时间码和匹配原因可追溯。
- 时间线禁止引用源视频40秒后的区间。

### 音频

支持：

- `auto`：有真实配音时使用配音，没有时保留原声。
- `narration`：只使用真实配音。
- `source`：保留原视频音频。
- `mixed`：真实配音与压低后的原声混合。
- `mute`：静音。

音频处理包括：

- 配音真实总时长读取。
- 原声按源时间码裁切。
- 原声跟随镜头变速。
- 无音轨镜头补等长静音。
- 配音响度标准化。
- 原声音量配置。
- 配音触发 sidechain ducking。
- 最终限幅。
- 原声覆盖率审核。

### Whisper 对齐

- 自动发现本地 Whisper CLI。
- 自动发现本地 `.pt` 权重。
- 支持显式模型名称或本地 `.pt` 路径。
- 默认禁止自动下载模型。
- 输出 JSON 和词级时间戳。
- 支持复用已有 Whisper JSON。
- 使用用户原文作为 initial prompt。
- 用户原文与 Whisper 转写进行单调序列对齐。
- 保留音频开头、结尾和句间停顿。
- 对齐覆盖率不足时退回按总时长比例分配。
- 降级原因写入项目报告。

Whisper 只负责提供时间证据。字幕正文始终使用用户输入的原文，不使用 Whisper 错别字覆盖原稿。

### 字幕

自动输出：

- `captions.srt`：通用句级字幕。
- `captions.ass`：可设置字体、字号、描边和安全区的句级字幕。
- `captions.karaoke.ass`：使用真实时间标记的逐字高亮字幕。

渲染时使用 `--burn-subtitles`，优先烧录逐字 ASS；没有逐字对齐时依次退回普通 ASS 和 SRT。

## 尚未实现

- TTS 自动配音生成。
- 背景音乐和音效素材库。
- 自动选音乐、卡点和情绪曲线。
- 代理视频生成。
- 大型素材库的 FAISS 或 Qdrant 后端。
- 人工审片网页面板。
- 达芬奇、Premiere、剪映工程文件导出。
- 导演系统 FastAPI 接口。
- 真实 Windows 素材集成压测。

## 模块目录

```text
short_drama_controller/script_mixer/
├─ audio.py
├─ catalog.py
├─ cli.py
├─ config.py
├─ embeddings.py
├─ enrichment.py
├─ environment.py
├─ intent.py
├─ media_probe.py
├─ models.py
├─ ollama_adapter.py
├─ pipeline.py
├─ planner.py
├─ render.py
├─ retrieval.py
├─ scanner.py
├─ scene_detection.py
├─ script_parser.py
├─ subtitles.py
├─ thumbnails.py
└─ transcription.py
```

## 本地运行数据

```text
.runtime/script_mixer/
├─ discovery.json
├─ last_scan.json
├─ last_enrichment.json
├─ last_embeddings.json
├─ media.db
├─ thumbnails/
└─ transcripts/
```

## 单个项目输出

```text
outputs/script_mixer/<project_id>/
├─ script.txt
├─ script_units.json
├─ visual_intents.json
├─ candidates.json
├─ transcript.json          # Whisper成功时
├─ alignment.json           # 对齐成功或回退结果
├─ timeline.json
├─ report.json
├─ render_plan.json
├─ subtitles/
│  ├─ captions.srt
│  ├─ captions.ass
│  └─ captions.karaoke.ass  # 逐字对齐成功时
└─ exports/
   └─ final.mp4
```

`.runtime/`、本地配置和视频输出已经加入 `.gitignore`。

## 第一次拉取后的顺序

### 1. 安装

```bash
python -m pip install -e .
```

### 2. 生成本机配置

```bash
script-driven-mixer init-config --out script_mixer.local.json
```

配置中的软件和模型位置默认留空。

### 3. 扫描环境

```bash
script-driven-mixer --config script_mixer.local.json doctor
```

### 4. 查看模型

```bash
script-driven-mixer --config script_mixer.local.json models
```

输出包括：

- Ollama 是否在线。
- 已安装 Ollama 模型和能力。
- 自动选择的文本、视觉和嵌入模型。
- Whisper CLI 路径。
- 本地 Whisper 权重。
- 自动选择的 Whisper 权重。
- 是否允许模型下载。

### 5. 初始化数据库

```bash
script-driven-mixer --config script_mixer.local.json init-db
```

### 6. 扫描素材

完整扫描：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow"
```

快速扫描：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow" \
  --fast
```

清理已经不存在的索引：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow" \
  --prune-missing
```

该命令只清理数据库，不删除原视频。

### 7. 视觉分析

```bash
script-driven-mixer --config script_mixer.local.json enrich-media --limit 100
script-driven-mixer --config script_mixer.local.json enrich-media
```

### 8. 构建向量

```bash
script-driven-mixer --config script_mixer.local.json build-embeddings \
  --limit 500 \
  --batch-size 32

script-driven-mixer --config script_mixer.local.json build-embeddings
```

### 9. 检查素材库

```bash
script-driven-mixer --config script_mixer.local.json catalog-status
```

状态输出包括：

- 原始素材总时长。
- 实际入库总时长。
- 被忽略尾部总时长。
- 被40秒限制截断的素材数量。

## 常用剪辑命令

### 无真实配音，保留原声

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --audio-mode source \
  --project-id source_audio_demo \
  --render
```

### 真实配音，自动 Whisper 对齐

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --project-id narration_demo \
  --render
```

### 真实配音、原声混合和逐字字幕烧录

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode mixed \
  --voice voice.wav \
  --burn-subtitles \
  --project-id mixed_demo \
  --render
```

### 使用已有 Whisper JSON

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --transcript-json voice.json \
  --burn-subtitles \
  --render
```

### 显式指定本地 Whisper 权重

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --whisper-model "D:/Models/Whisper/medium.pt" \
  --render
```

### 禁止本次转写

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode narration \
  --voice voice.wav \
  --no-transcribe \
  --render
```

此时仍使用配音真实总时长，但每句时间按文案长度比例分配。

### 只生成渲染计划

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --audio-mode mixed \
  --voice voice.wav \
  --burn-subtitles \
  --render \
  --dry-run
```

## 配置重点

### 源视频处理上限

```json
{
  "media_scan": {
    "maximum_source_process_seconds": 40.0
  }
}
```

设置为 `0` 表示不限制，但默认和推荐值为40秒。

### 默认不下载 Whisper 模型

```json
{
  "transcription": {
    "allow_model_download": false
  }
}
```

空 `speech_model` 表示扫描本地权重。没有本地模型时，系统回退到比例时间轴并写入警告。

允许 Whisper CLI 根据模型名称下载时，需要明确改为：

```json
{
  "transcription": {
    "allow_model_download": true
  }
}
```

### 对齐覆盖率

```json
{
  "transcription": {
    "minimum_alignment_coverage": 0.55
  }
}
```

低于阈值时不强行使用错误时间锚点。

### 字幕样式

```json
{
  "subtitles": {
    "font_name": "Microsoft YaHei",
    "font_size": 64,
    "outline": 3.0,
    "shadow": 1.0,
    "alignment": 2,
    "margin_vertical": 150,
    "burn_in_by_default": false
  }
}
```

仓库不携带字体文件。实际渲染使用电脑已安装字体；找不到指定字体时由 FFmpeg/libass 回退。

## 报告字段

`report.json` 包含：

- 唯一素材来源数量。
- 单来源最高占比。
- 各来源使用秒数。
- 低匹配镜头。
- 原声覆盖率。
- 配音真实时长。
- Whisper 模型和语言。
- 时间来源：`whisper_alignment`、`proportional_fallback` 或 `estimated`。
- 文案与转写对齐覆盖率。
- 字幕文件路径。
- 是否需要人工检查字幕。
- 是否允许正式导出。

素材库状态额外包含：

- `original_duration_seconds`
- `indexed_duration_seconds`
- `ignored_tail_seconds`
- `capped_source_count`
- `maximum_source_process_seconds`

## 测试

```bash
pytest -q tests/test_script_mixer*.py
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
script-driven-mixer --help
```

自动化测试必须：

- 不依赖网络。
- 不要求真实 FFmpeg、Whisper 或 Ollama。
- 使用假执行器验证外部命令契约。
- 覆盖 Python 3.10 和 3.12。
- 验证用户原文在逐字字幕中完整保留。
- 验证长素材不会产生40秒后的镜头。
- 验证FFmpeg场景检测只运行到40秒。

## 安全边界

- 原始素材只读。
- 不把本地绝对路径提交到 Git。
- 不自动上传素材。
- 不自动发布视频。
- 不偷偷下载模型。
- Whisper 识别文本不能覆盖用户原文。
- 源视频40秒后的尾部不能进入视觉分析、向量或时间线。
- 多来源混剪不等于获得版权授权。
- 正式发布前仍需人工检查画面、字幕、事实和素材权利。
