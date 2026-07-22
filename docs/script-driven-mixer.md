# Script-driven local mixer / 文案驱动本地混剪

## 目标

用户只输入文案。系统根据文案语义生成画面意图，从本地素材目录中检索多个来源的镜头，规划时间线，并在运行环境具备 FFmpeg 时渲染视频。

本模块不硬编码任何软件或模型路径。仓库拉取到实际电脑后，先运行环境发现，再由配置覆盖无法自动发现的位置。

## 当前实现范围

已实现：

1. 跨平台软件与模型目录发现。
2. JSON 配置和空路径默认值。
3. 文案清洗、语义单元拆分和目标时长缩放。
4. 不依赖云端 Token 的规则式画面意图回退。
5. SQLite 素材镜头目录和使用历史。
6. 多字段文本召回、情绪和景别评分、历史使用惩罚。
7. 多来源时间线规划。
8. 相邻同源禁止、来源冷却、单来源时长和占比限制。
9. FFmpeg `filter_complex` 渲染命令生成。
10. 项目目录、候选镜头、时间线和审核报告输出。

暂未接入：

- 自动镜头切分。
- FFprobe 元数据入库。
- Whisper 转写。
- 本地视觉模型描述和向量提取。
- Qdrant、FAISS 或其他向量后端。
- Ollama 文案理解适配器。
- TTS、字幕烧录、音乐和音效混合。
- 达芬奇、Premiere、剪映工程文件导出。

这些能力必须通过适配器接入，不允许把实际电脑路径写进源码。

## 目录

```text
short_drama_controller/script_mixer/
├─ __init__.py
├─ catalog.py
├─ cli.py
├─ config.py
├─ environment.py
├─ intent.py
├─ models.py
├─ pipeline.py
├─ planner.py
├─ render.py
├─ retrieval.py
└─ script_parser.py
```

运行后产生：

```text
.runtime/script_mixer/
├─ discovery.json
└─ media.db

outputs/script_mixer/<project_id>/
├─ script.txt
├─ script_units.json
├─ visual_intents.json
├─ candidates.json
├─ timeline.json
├─ report.json
├─ render_plan.json
└─ exports/
   └─ final.mp4
```

`.runtime/` 和输出视频不应提交到 Git。

## 安装

```bash
python -m pip install -e .
```

项目本身暂不声明 FFmpeg、Ollama、Whisper、视觉模型等运行依赖。它们由实际电脑提供，并由 `doctor` 自动扫描。

## 第一次拉取到电脑后的顺序

### 1. 生成本机配置

```bash
script-driven-mixer init-config --out script_mixer.local.json
```

默认配置中的以下字段均为空：

```json
{
  "text_model": "",
  "vision_model": "",
  "embedding_model": "",
  "speech_model": ""
}
```

### 2. 扫描软件和模型

```bash
script-driven-mixer --config script_mixer.local.json doctor
```

扫描结果写入：

```text
.runtime/script_mixer/discovery.json
```

优先级：

1. 配置文件显式覆盖。
2. 系统 `PATH`。
3. 环境变量。
4. 常见用户目录和缓存目录。
5. 有深度和数量限制的文件系统扫描。

发现器当前查找：

- FFmpeg
- FFprobe
- Ollama
- Python
- Git
- NVIDIA SMI
- Whisper CLI
- Ollama 模型目录
- Hugging Face 缓存
- Whisper 模型缓存
- ComfyUI `models` 目录

### 3. 初始化素材数据库

```bash
script-driven-mixer --config script_mixer.local.json init-db
```

### 4. 导入临时镜头清单

自动素材分析器尚未接入前，可使用 JSON 清单导入：

```json
{
  "clips": [
    {
      "clip_id": "C001",
      "source_id": "SRC001",
      "source_path": "D:/Media/source_001.mp4",
      "source_start": 12.4,
      "source_end": 15.1,
      "duration": 2.7,
      "description": "年轻人深夜在办公室使用电脑工作",
      "tags": ["办公室", "电脑", "工作", "深夜"],
      "emotions": ["疲惫", "专注"],
      "shot_type": "中近景",
      "camera_motion": "缓慢推进",
      "width": 1080,
      "height": 1920,
      "quality_score": 0.9,
      "has_watermark": false,
      "usable": true
    }
  ]
}
```

导入：

```bash
script-driven-mixer --config script_mixer.local.json import-manifest --manifest clips.json
```

### 5. 根据文案生成时间线

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --project-id demo_001
```

### 6. 渲染

先只生成命令：

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --project-id demo_001 \
  --render \
  --dry-run
```

真实渲染：

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --project-id demo_002 \
  --render \
  --voice voice.wav
```

## 文案到画面的处理契约

不能直接拿整句文案搜索文件名。必须经过：

```text
原文案
→ 语义单元
→ 角色判断：钩子/主体/转折/结论
→ 直接画面查询
→ 隐喻画面查询
→ 正向标签
→ 负向约束
→ 情绪
→ 景别偏好
→ 素材召回
→ 全局重排
```

第一版提供规则式意图生成器，用于没有模型时保持流程可运行。后续 Ollama 或云端模型必须实现 `IntentProvider` 协议，返回同一个 `VisualIntent` 数据结构。

## 混剪硬规则

默认配置：

| 规则 | 默认值 |
|---|---:|
| 画幅 | 1080×1920 |
| 帧率 | 30 |
| 最少原素材来源 | 8 |
| 推荐原素材来源 | 12 |
| 单来源最大占比 | 15% |
| 单来源累计时长 | 4秒 |
| 单段连续镜头 | 3秒 |
| 最短镜头 | 0.7秒 |
| 来源再次出现间隔 | 3个镜头 |
| 低匹配阈值 | 0.45 |

约束无法满足时允许生成待审核时间线，但必须把放宽行为和低匹配镜头写入 `report.json`。正式发布流程不得忽略这些警告。

## 素材数据库契约

素材的最小单位是镜头片段，不是整条视频。每条记录至少需要：

- `clip_id`
- `source_id`
- `source_path`
- `source_start`
- `source_end`
- `duration`
- `description`
- `tags`
- `emotions`
- `shot_type`
- `camera_motion`
- `quality_score`
- `has_watermark`
- `usable`

后续向量数据不直接塞进 SQLite 大字段。SQLite 保存权威元数据，向量后端保存向量并以 `clip_id` 关联。

## 下一阶段开发顺序

### P1 素材自动入库

1. `ffprobe_adapter.py`：读取时长、画幅、帧率、编码、音轨。
2. `scene_detector.py`：自动镜头切分。
3. `thumbnail_extractor.py`：开始、中间、结束和代表关键帧。
4. `audio_extractor.py`：提取音频代理。
5. `manifest_builder.py`：统一生成 `MediaClip`。

验收：扫描指定目录后自动写入 SQLite，增量运行不重复分析未变化文件。

### P2 画面理解和向量

1. `vision_caption_adapter.py`：关键帧生成结构化描述。
2. `embedding_adapter.py`：描述文本向量。
3. `image_embedding_adapter.py`：关键帧跨模态向量。
4. `vector_store.py`：FAISS 或 Qdrant 实现。
5. `reranker.py`：融合文本、视觉、标签和历史使用分。

验收：输入“失败不是因为不努力”时，可以召回疲惫工作、循环劳动、迷茫人物等直接和隐喻画面，而不依赖文件名。

### P3 配音、字幕和音频

1. 配音导入和 TTS 适配器。
2. 句级与词级时间戳。
3. SRT/ASS 字幕生成。
4. 字幕安全区和模板。
5. 音量标准化和背景音乐 ducking。

验收：时间线长度以真实配音为准，字幕与配音同步。

### P4 人工审片面板

1. 每句文案展示当前镜头和候选镜头。
2. 锁定镜头。
3. 仅替换指定时间段。
4. 预览低清代理。
5. 显示匹配原因和来源占比。

验收：人工不需要重做全片即可替换任意低分镜头。

### P5 导演系统接入

通过 API 暴露：

```text
POST /script-mixer/discover
POST /script-mixer/catalog/scan
POST /script-mixer/projects
POST /script-mixer/projects/{id}/plan
POST /script-mixer/projects/{id}/render
POST /script-mixer/projects/{id}/segments/{segment_id}/replace
GET  /script-mixer/projects/{id}/report
```

导演系统只调用服务，不复制素材分析、检索和渲染代码。

## 测试

```bash
pytest -q tests/test_script_mixer.py
```

测试不依赖网络、FFmpeg 或真实模型。真实软件和真实素材集成测试放在本机执行，并将结果写入运行报告，不提交大型媒体文件。

## 安全边界

- 原始素材只读。
- 不自动删除或移动原素材。
- 不把本地绝对路径提交到 Git。
- 不因为多来源混剪就声称素材已获得授权。
- 不把低相似度或切碎镜头当作版权合规证明。
- 最终发布前必须人工审核画面、字幕、事实和授权。
