# AI短剧导演系统

版本：`0.7.0`

这是唯一维护的 AI 短剧导演生产仓库。系统把小说、剧本、口述创意或半成品提示词整理成导演物料，并生成可恢复的资产、分镜、视频、声音和合成任务图。

## 单一工作流

```text
原始内容
  -> 剧情与章节事件图谱
  -> 剧本与节拍
  -> 人物/场景/道具资产锁定
  -> 镜头与分镜
  -> 图片/视频/声音任务图
  -> 人工审核与返修
  -> 合成计划
  -> QA 与导出
```

工作流契约：`workflows/novel_to_drama.v1.json`

## 安装

需要 Python 3.10 或更高版本：

```bash
python -m pip install -e .
```

## 使用

生成完整生产计划：

```bash
short-drama-controller run \
  --input examples/input_script.md \
  --out demo \
  --title 镖局收徒Demo
```

查看状态：

```bash
short-drama-controller status --project demo
```

断点续跑：

```bash
short-drama-controller run \
  --input examples/input_script.md \
  --out demo \
  --resume
```

生成节点化导演工作流模板：

```bash
short-drama-controller graph-template --out director_graph.json
```

导入本机生产管理器：

```bash
short-drama-controller sync \
  --project demo \
  --manager-url http://127.0.0.1:8000
```

本地检查：

```bash
short-drama-controller doctor
pytest -q
```

## 核心结构

```text
short_drama_controller/
├─ director_system/
│  ├─ agents.py       # 导演、编剧、资产、分镜、制作、审核角色
│  ├─ graph.py        # 节点依赖、状态、重试和阻塞
│  ├─ providers.py    # 文本、图片、视频、TTS、工作流、合成接口
│  └─ story.py        # 章节事件图谱和上下文召回
├─ cli.py             # 唯一命令入口
├─ v06_unified_workflow.py
└─ v06_manager_sync.py
```

旧实现文件目前仅作为内部兼容层，不再提供独立命令或独立版本。后续修改统一从 `short-drama-controller` 入口进入。

## 当前已完成

- 原始内容 SHA256 与断点状态。
- 剧本、事件链、世界观和风格物料。
- 人物、场景、道具和分镜任务图。
- 图片、视频、TTS 和合成依赖关系。
- 候选版本、人工选片、失败重试和阻塞状态。
- 节点化导演工作流契约。
- 分层 Agent 定义。
- Provider 注册和能力路由。
- 章节事件图谱、依赖校验和局部上下文提取。
- 本机生产管理器 dry-run 导入。

## 当前执行边界

尚未默认自动执行：

- 真实图片和视频推理。
- GPU 启动与模型下载。
- 付费模型接口调用。
- 真实 TTS。
- FFmpeg 最终成片执行。

只有真实 Provider、媒体输出、人工审核和 QA 全部通过后，状态才允许进入 `completed`。

## 文档

- `docs/ARCHITECTURE.md`
- `docs/CODE_MAP.md`
- `docs/DEVELOPMENT.md`
- `THIRD_PARTY_NOTICES.md`
