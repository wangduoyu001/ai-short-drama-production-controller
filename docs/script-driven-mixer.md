# Script-driven local mixer / 文案驱动本地混剪

## 目标

用户只输入文案。系统把文案拆成带时间的语义单元和画面意图，从本地素材库检索多个来源镜头，生成可追溯时间线，并在实际电脑发现 FFmpeg 后渲染视频。

本模块不硬编码软件、模型、素材盘符或缓存路径。仓库拉取到实际电脑后，先自动发现运行环境，再由本地忽略配置覆盖无法发现的位置。

## 已实现能力

1. 跨 Windows、macOS、Linux 的软件与模型目录发现。
2. JSON 配置、旧配置迁移和空模型路径默认值。
3. FFprobe 视频元数据读取：时长、画幅、旋转、帧率、视频编码、音频编码和音轨状态。
4. 本地素材目录递归扫描和格式过滤。
5. 文件指纹、增量扫描、变化检测和缺失索引清理。
6. FFmpeg 场景变化检测。
7. 场景检测失败时固定窗口切分回退。
8. 镜头中点缩略图提取。
9. 快速扫描与完整扫描状态区分，普通扫描可自动升级快速记录。
10. SQLite 原视频、镜头、使用历史、扫描状态和向量缓存。
11. Ollama 本地服务探测、模型列表和能力读取。
12. 按 `completion`、`vision`、`embedding` 能力自动选择模型。
13. Ollama JSON Schema 结构化文案画面意图。
14. Ollama 视觉模型关键帧描述、标签、情绪、景别、运动、水印和画质分析。
15. Ollama `/api/embed` 批量镜头向量构建。
16. 向量按镜头、模型和内容哈希增量缓存。
17. 文案画面意图实时向量化与余弦相似度检索。
18. 无本地模型时的规则式画面意图和关键词检索回退。
19. 词义、标签、情绪、景别、画质、向量和历史使用融合评分。
20. 多来源时间线规划。
21. 相邻同源禁止、来源冷却、单来源时长和占比限制。
22. FFmpeg `filter_complex` 渲染命令生成。
23. 项目目录、候选镜头、时间线和审核报告输出。
24. Python 3.10/3.12 GitHub Actions 测试工作流。

## 尚未实现

- Whisper 语音转写和原字幕提取。
- 上传配音后的真实句级与词级时间轴。
- TTS、SRT、ASS 字幕和字幕烧录。
- 背景音乐、音效、响度标准化和自动 ducking。
- 代理视频生成。
- 大型素材库的 FAISS 或 Qdrant 后端。
- 人工审片网页面板。
- 达芬奇、Premiere、剪映工程文件导出。
- 导演系统 FastAPI 接口。

## 模块目录

```text
short_drama_controller/script_mixer/
├─ __init__.py
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
└─ thumbnails.py
```

运行数据：

```text
.runtime/script_mixer/
├─ discovery.json
├─ last_scan.json
├─ last_enrichment.json
├─ last_embeddings.json
├─ media.db
└─ thumbnails/
```

单个混剪项目：

```text
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

`.runtime/`、本地配置和视频输出均已加入 `.gitignore`。

## 安装

```bash
python -m pip install -e .
```

Python 包本身不强制安装 FFmpeg、Ollama、Whisper、ComfyUI 或模型文件。外部能力由实际电脑提供，并通过 `doctor`、`models` 和本地配置解析。

## 第一次拉取到电脑后的完整顺序

### 1. 生成本机配置

```bash
script-driven-mixer init-config --out script_mixer.local.json
```

模型名称默认留空：

```json
{
  "local_models": {
    "auto_select_ollama_models": true,
    "ollama_base_url": "http://127.0.0.1:11434",
    "text_model": "",
    "vision_model": "",
    "embedding_model": "",
    "speech_model": ""
  }
}
```

空名称表示根据 Ollama 模型能力自动选择，而不是要求用户先猜本地模型路径。

### 2. 扫描软件和模型目录

```bash
script-driven-mixer --config script_mixer.local.json doctor
```

结果写入：

```text
.runtime/script_mixer/discovery.json
```

路径优先级：

1. 本地配置显式覆盖。
2. 系统 `PATH`。
3. 环境变量。
4. 常见用户目录和缓存目录。
5. 有深度与文件数量限制的文件系统扫描。

当前查找：

- FFmpeg
- FFprobe
- Ollama
- Whisper CLI
- Python
- Git
- NVIDIA SMI
- Ollama 模型目录
- Hugging Face 缓存
- Whisper 模型缓存
- ComfyUI `models` 目录

### 3. 查看 Ollama 模型能力

```bash
script-driven-mixer --config script_mixer.local.json models
```

输出包括：

- Ollama 服务是否在线
- 已安装模型
- 每个模型的能力
- 参数规模与量化等级
- 自动选择的文本模型
- 自动选择的视觉模型
- 自动选择的嵌入模型
- 每个嵌入模型已缓存的镜头数量

文本任务优先使用不带视觉能力的模型；视觉任务只选择明确报告 `vision` 能力的模型；向量任务只选择明确报告 `embedding` 能力的模型。

### 4. 初始化数据库

```bash
script-driven-mixer --config script_mixer.local.json init-db
```

### 5. 扫描本地素材目录

完整扫描：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow"
```

素材量很大时可先快速入库：

```bash
script-driven-mixer --config script_mixer.local.json scan-media \
  --root "D:/Media/InformationFlow" \
  --fast
```

快速模式：

- 使用 FFprobe 读取元数据
- 使用固定时间窗口切镜
- 暂不运行场景检测
- 暂不提取缩略图
- 原视频状态记录为 `fast`

之后运行普通扫描会自动升级，无需修改文件或手动加 `--force`。

```text
--force          强制重做未变化文件
--prune-missing  清理数据库中已经从该素材目录删除的索引
```

`--prune-missing` 只删除数据库记录，不删除磁盘原视频。

### 6. 检查素材库

```bash
script-driven-mixer --config script_mixer.local.json catalog-status
```

输出：

- 原视频数量
- 镜头数量
- 各扫描状态数量
- 素材总时长
- 丢失原文件数量
- 缩略图数量
- 已完成视觉分析的镜头数量
- 各嵌入模型的向量缓存数量

### 7. 使用本地视觉模型增强素材

先试运行少量镜头：

```bash
script-driven-mixer --config script_mixer.local.json enrich-media --limit 100
```

确认正常后运行完整增量分析：

```bash
script-driven-mixer --config script_mixer.local.json enrich-media
```

重新分析已有记录：

```bash
script-driven-mixer --config script_mixer.local.json enrich-media --force
```

每个镜头会增加：

- 可见主体
- 场景
- 动作
- 情绪
- 语义标签
- 景别
- 镜头运动线索
- 水印判断
- 画质评分

检测到明显水印的镜头会被标记，并从默认候选中排除。

### 8. 构建语义向量

先试运行：

```bash
script-driven-mixer --config script_mixer.local.json build-embeddings \
  --limit 500 \
  --batch-size 32
```

完整增量构建：

```bash
script-driven-mixer --config script_mixer.local.json build-embeddings
```

强制重建：

```bash
script-driven-mixer --config script_mixer.local.json build-embeddings --force
```

向量文本由以下内容组成：

```text
画面描述
标签
情绪
景别
镜头运动
```

缓存主键：

```text
clip_id + embedding_model
```

内容哈希未变化时跳过重新计算。切镜后失效的旧向量会在完整构建时清理。

向量采用压缩的 float32 二进制保存在同一个 SQLite 数据库中。第一版适合单机中小型素材库，不要求额外安装向量数据库。

### 9. 输入文案生成时间线

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --project-id demo_001
```

文案规划会：

1. 优先尝试自动选择的 Ollama 文本模型。
2. 要求模型按 JSON Schema 输出画面意图。
3. 本地服务不可用或结果不合格时退回规则式画面意图。
4. 若对应嵌入模型已有缓存，自动生成文案向量并加入检索评分。
5. 若没有向量缓存，使用描述、标签、情绪和景别继续检索。
6. 进行多来源全局编排。
7. 输出时间线和质量报告。

不会在 `plan` 时自动重算全部素材向量。向量构建必须通过独立命令执行，避免一次普通剪辑意外触发长时间后台任务。

### 10. 生成渲染命令

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --project-id demo_001 \
  --render \
  --dry-run
```

### 11. 真实渲染

```bash
script-driven-mixer --config script_mixer.local.json plan \
  --script input.txt \
  --duration 30 \
  --project-id demo_002 \
  --render \
  --voice voice.wav
```

当前 `voice.wav` 只作为最终音轨合入。下一阶段将使用真实配音时间戳重建文案单元和字幕时间线。

## 扫描状态

| 状态 | 含义 |
|---|---|
| `ready` | 完整扫描完成 |
| `fast` | 固定窗口快速入库，待完整升级 |
| `metadata_only` | FFprobe 已完成，但 FFmpeg 不可用，暂无场景检测和缩略图 |
| `skipped` | 时长低于最低要求 |
| `failed` | 无视频流、无法读取时长或其他阻断错误 |

当 FFmpeg 后续安装成功，再次普通扫描会自动升级 `fast` 或 `metadata_only` 记录。

## 素材增量机制

文件指纹综合：

- 文件大小
- 纳秒级修改时间
- 文件头采样
- 文件尾采样

未变化文件不会重新执行 FFprobe、场景检测或缩略图提取。变化文件会在单个数据库事务中更新原视频记录并替换对应镜头。

原始视频始终只读，不转码覆盖、不重命名、不移动。

## 文案到画面的处理契约

禁止只拿整句文案或文件名做匹配。必须经过：

```text
原文案
→ 语义单元
→ 角色：钩子/主体/转折/结论
→ 直接画面查询
→ 隐喻画面查询
→ 正向标签
→ 负向约束
→ 情绪
→ 景别偏好
→ 文案向量
→ 素材召回
→ 全局重排
```

例如：

```text
文案：失败不是因为不够努力
直接画面：深夜工作、疲惫人物、电脑操作、数据下跌
隐喻画面：原地循环、雨中独行、道路受阻
情绪：挫败、疲惫、迷茫
排除：庆祝、领奖、轻松旅游
```

Ollama 与规则式生成器都返回统一的 `VisualIntent`，后续检索层不依赖具体模型。

## 混合检索评分

有向量缓存时：

```text
38% 向量语义
24% 描述与查询词义重叠
12% 标签
12% 画质
9% 情绪
5% 景别
```

无向量缓存时自动重新分配到文本和结构化字段。

额外惩罚：

- 水印
- 不可用镜头
- 历史高频使用
- 负向语义冲突
- 横屏裁切成本

向量余弦相似度只保留正相关部分。无关向量不会因为数值归一化白得基础分。

## 混剪硬规则

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

约束无法满足时，只能生成待审核时间线。放宽行为、来源不足和低匹配镜头必须写入 `report.json`。

## 数据库契约

### 原视频 `media_sources`

至少记录：

- `source_id`
- `source_path`
- `filename`
- `file_size`
- `modified_ns`
- `fingerprint`
- `duration`
- `width`
- `height`
- `fps`
- `video_codec`
- `audio_codec`
- `rotation`
- `status`
- `error`

### 镜头 `media_clips`

至少记录：

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
- `thumbnail_path`

### 向量 `clip_embeddings`

至少记录：

- `clip_id`
- `model`
- `content_hash`
- `dimensions`
- `vector_blob`
- `updated_at`

手工 `import-manifest` 仍兼容，不要求先创建 `media_sources` 记录。

## 下一阶段：真实配音与字幕时间轴

开发顺序：

1. 音频 FFprobe 适配器。
2. 上传配音时长校验。
3. Whisper CLI 与 Python 后端自动发现。
4. 句级和词级时间戳统一数据契约。
5. 文案与转写结果对齐。
6. 按真实语速重建 `ScriptUnit`。
7. SRT 和 ASS 字幕输出。
8. 字幕安全区与模板配置。
9. 配音响度标准化。
10. 背景音乐 ducking。

验收：成片时间线严格跟随真实配音，而不是只按字数估时。

## 后续扩展

### 大型向量后端

SQLite 版本用于先跑通单机闭环。素材镜头达到几十万级后，按统一 `VectorSearchProvider` 协议接入 FAISS 或 Qdrant，不改文案、时间线和渲染层。

### 人工审片面板

- 每句文案显示当前镜头与候选镜头
- 锁定镜头
- 只替换指定片段
- 低清代理预览
- 匹配理由和来源占比

### 导演系统接口

```text
POST /script-mixer/discover
GET  /script-mixer/models
POST /script-mixer/catalog/scan
POST /script-mixer/catalog/enrich
POST /script-mixer/catalog/embeddings
GET  /script-mixer/catalog/status
POST /script-mixer/projects
POST /script-mixer/projects/{id}/plan
POST /script-mixer/projects/{id}/render
POST /script-mixer/projects/{id}/segments/{segment_id}/replace
GET  /script-mixer/projects/{id}/report
```

导演系统只调用服务，不复制素材分析、检索和渲染代码。

## 测试

```bash
pytest -q tests/test_script_mixer*.py
```

测试不依赖网络、FFmpeg、FFprobe、Ollama、真实模型或私人素材。外部工具通过假执行器测试，真实集成测试只在实际电脑运行。

GitHub Actions：

```text
.github/workflows/script-mixer-ci.yml
Python 3.10
Python 3.12
```

## 安全边界

- 原始素材只读。
- 不自动删除、重命名、移动或覆盖原素材。
- `--prune-missing` 只删除数据库索引，不删除磁盘文件。
- 不把本地绝对路径提交到 Git。
- 不把图片或文案发往云端，除非以后显式配置云端适配器。
- 多来源混剪、低文本相似度和短镜头不等于版权授权。
- 最终发布前必须人工检查素材授权、字幕、事实、水印和平台规则。
