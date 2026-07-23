# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.7.0-dev`

本仓库包含两条独立生产链：

1. **AI短剧导演物料链**：剧本、资产、生成片段、分镜、提示词、QA和导出。
2. **文案驱动本地混剪链**：本地素材自动粗剪、真实配音、Whisper字幕、人工返修和剪映可编辑工程。

当前本地混剪的最终交付不是只有一条压平的MP4，而是：

```text
预览final.mp4
+
独立可拖动镜头
+
独立原声
+
完整配音
+
可编辑字幕
+
每个镜头的备用候选
+
可选剪映草稿
```

AI负责完成第一版粗剪，人最终在剪映里调整切点、替换画面、修改字幕、声音和节奏。把自动识别当成永不犯错的神谕，属于一种昂贵的乐观。

---

# 最快开始：Windows + Codex + 剪映

## 1. 让Codex拉取仓库

```bash
git clone https://github.com/wangduoyu001/ai-short-drama-production-controller.git
cd ai-short-drama-production-controller
git checkout feature/script-driven-local-mixer
```

PR合并后直接使用默认分支即可，不再需要最后一行。

## 2. 一键安装

在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_jianying_windows.ps1
```

需要脚本同时尝试安装FFmpeg：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_jianying_windows.ps1 -InstallMissingTools
```

安装内容：

```text
Python项目
剪映草稿可选适配器
本地配置
SQLite素材库
环境检查
剪映草稿目录检查
```

手工安装等价命令：

```bash
python -m pip install -e ".[jianying]"
script-driven-mixer init-config --out script_mixer.local.json
script-driven-mixer --config script_mixer.local.json init-db
script-driven-mixer --config script_mixer.local.json integration-check
script-driven-mixer --config script_mixer.local.json jianying-status
```

需要 Python 3.10 或更高版本。

## 3. 查看剪映草稿目录

剪映专业版：

```text
全局设置 → 草稿位置
```

可以写入本地配置：

```json
{
  "edit_package": {
    "jianying_draft_root": "D:/JianyingPro Drafts"
  }
}
```

本地配置被 `.gitignore` 忽略，不会把你的电脑路径提交到仓库。

## 4. 一键生成剪映项目

有真实配音：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 `
  -MediaRoot "D:\视频素材" `
  -Script "input.txt" `
  -Voice "voice.wav" `
  -DraftRoot "D:\JianyingPro Drafts"
```

没有配音，保留原视频声音：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 `
  -MediaRoot "D:\视频素材" `
  -Script "input.txt" `
  -DraftRoot "D:\JianyingPro Drafts"
```

第一次只验证链路，不运行Ollama视觉模型和向量：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 `
  -MediaRoot "D:\视频素材" `
  -Script "input.txt" `
  -Voice "voice.wav" `
  -SkipModels
```

等价CLI：

```bash
script-driven-mixer --config script_mixer.local.json make-jianying-project \
  --media-root "D:/视频素材" \
  --script input.txt \
  --voice voice.wav \
  --audio-mode mixed \
  --draft-root "D:/JianyingPro Drafts" \
  --candidate-count 3 \
  --handle-before 1 \
  --handle-after 1 \
  --burn-subtitles
```

---

# 最终流程

```text
本地视频素材
        │
        ├─ 每个原视频只处理前40秒
        ├─ FFprobe读取时长、画幅、帧率和音轨
        ├─ FFmpeg场景切分
        ├─ 缩略图和视觉描述
        └─ 本地语义向量
        │
        ▼
本地素材库
        │
文案 + 可选真实配音
        │
        ├─ 文案拆成时间单元
        ├─ Whisper提供词级时间
        ├─ 用户原文与时间对齐
        ├─ 理解每段需要的画面
        └─ 多来源镜头检索
        │
        ▼
自动粗剪时间线
        │
        ├─ final.mp4快速预览
        ├─ review.json审核清单
        ├─ 可替换、锁定、回退
        └─ 剪映可编辑包
        │
        ▼
剪映人工调整
        │
        ├─ 拖动镜头边缘
        ├─ 修改切点和顺序
        ├─ 从候选目录替换画面
        ├─ 修改字幕
        ├─ 调整配音和原声
        ├─ 添加音乐、音效和转场
        └─ 正式导出
```

---

# 为什么在剪映里可以自由修改

系统选择的源区间例如：

```text
5秒 ～ 8秒
```

编辑包默认导出：

```text
4秒 ～ 9秒
```

于是剪映片段中保留：

```text
前1秒余量
系统选中3秒
后1秒余量
```

你可以向前或向后拖动边缘，而不需要重新定位原始长视频。

余量仍受40秒限制。例如系统选中38～40秒时：

```text
实际导出：37～40秒
后余量：0秒
```

不会为了方便修改，把40秒后的内容偷偷放回来。

---

# 如何降低卡帧、跳帧和黑帧

剪映编辑包不会使用简单的关键帧附近无损截取，而是重新解码和编码：

```text
固定帧率CFR
H.264
统一项目分辨率
统一项目帧率
统一像素格式yuv420p
精确源时间解码
```

主要解决：

- 手机可变帧率造成时间漂移。
- 不同帧率、编码直接拼接造成卡顿。
- 非关键帧开始造成黑帧、首帧停顿或花屏。
- 异常时间戳造成音画错位。

这不能把损坏的原素材变健康，也不能保证AI选择的动作切点永远符合导演判断，所以系统同时提供前后余量和备用候选。

---

# 剪映编辑包输出

```text
outputs/script_mixer/<project_id>/
├─ script.txt
├─ script_units.json
├─ visual_intents.json
├─ candidates.json
├─ transcript.json
├─ alignment.json
├─ timeline.json
├─ review.json
├─ report.json
├─ render_plan.json
├─ subtitles/
│  ├─ captions.srt
│  ├─ captions.ass
│  └─ captions.karaoke.ass
├─ revisions/
└─ exports/
   ├─ final.mp4
   └─ jianying_package/
      ├─ video/
      │  ├─ S001_....mp4
      │  ├─ S002_....mp4
      │  └─ ...
      ├─ audio/
      │  ├─ S001_source.wav
      │  ├─ S002_source.wav
      │  └─ narration.wav
      ├─ subtitles/
      │  ├─ captions.srt
      │  ├─ captions.ass
      │  └─ captions.karaoke.ass
      ├─ candidates/
      │  ├─ S001/
      │  ├─ S002/
      │  └─ ...
      ├─ metadata/
      │  ├─ package_manifest.json
      │  ├─ timeline.csv
      │  └─ ffmpeg_commands.json
      └─ 剪映导入与修改说明.txt
```

草稿成功时还会在剪映草稿目录生成一个唯一命名的新工程，不覆盖已有草稿。

草稿轨道：

```text
视频轨：AI粗剪视频
音频轨：原声
音频轨：配音
字幕轨：字幕
```

草稿打不开时，标准编辑包仍然完整可用。按S001、S002顺序导入视频，再导入配音和SRT即可。剪映草稿是私有格式，不能把整个工作流的生死交给它。

详细说明：

```text
docs/jianying-edit-workflow.md
```

---

# 已有项目导出剪映包

```bash
script-driven-mixer --config script_mixer.local.json export-jianying-package \
  --project <项目ID> \
  --draft-root "D:/JianyingPro Drafts"
```

只要稳定编辑包，不生成草稿：

```bash
script-driven-mixer --config script_mixer.local.json export-jianying-package \
  --project <项目ID> \
  --no-draft
```

强制重新生成所有代理：

```bash
--force-package
```

只查看FFmpeg命令：

```bash
--package-dry-run
```

系统按源文件、源区间、余量、目标画幅、帧率和音频规格生成内容哈希。时间线返修后再次导出，只重新生成变化的镜头和候选，未变化资产直接复用。

---

# 人工返修命令

生成审核清单：

```bash
script-driven-mixer --config script_mixer.local.json review-project \
  --project <项目ID>
```

锁定满意镜头：

```bash
script-driven-mixer --config script_mixer.local.json lock-segment \
  --project <项目ID> \
  --segment S002
```

替换不满意镜头：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目ID> \
  --segment S002 \
  --keyword "手机 创作" \
  --reason "当前画面与文案不匹配"
```

保留锁定镜头，重新规划其他镜头：

```bash
script-driven-mixer --config script_mixer.local.json replan-project \
  --project <项目ID>
```

回退最近一次修改：

```bash
script-driven-mixer --config script_mixer.local.json rollback-project \
  --project <项目ID>
```

详细说明：

```text
docs/script-mixer-review.md
```

---

# 当前主要能力

## 素材

- 本地目录递归扫描。
- 文件指纹和增量更新。
- 每个原视频默认只处理前40秒。
- 原始时长、入库时长和忽略尾部分开记录。
- FFprobe元数据和音轨检测。
- FFmpeg场景切分和固定窗口回退。
- 缩略图。
- 原素材只读。

## 模型

- Ollama文本、视觉和嵌入模型自动发现。
- Whisper CLI和本地权重自动发现。
- 默认禁止自动下载模型。
- 缺少模型时明确降级，不阻断规则式粗剪。

## 检索与规划

- 直接画面和隐喻画面意图。
- 标签、情绪、景别和负向约束。
- 文本、向量、画质和历史使用融合评分。
- 相邻同源限制。
- 来源冷却。
- 单来源时长和占比审核。
- 低匹配报告。

## 音频

```text
auto
narration
source
mixed
mute
```

支持：

- 真实配音总时长。
- 原声按源时间裁切。
- 无音轨补静音。
- 配音响度标准化。
- 原声ducking。
- 配音和原声分轨导出。

## 字幕

- Whisper词级时间戳。
- 用户原文与转写时间单调对齐。
- SRT。
- ASS。
- 逐字卡拉OK ASS。
- Whisper只提供时间，不用识别错字覆盖用户原文。

## 可返修

- 当前镜头ID和候选排名。
- 锁定、解锁。
- 单镜头替换。
- 重新规划时保留锁定镜头。
- 修改前快照。
- 回退。
- 返修后QA报告重建。

## 真实电脑验收

```bash
script-driven-mixer --config script_mixer.local.json integration-check
```

检查：

- Python、目录权限、磁盘和SQLite。
- FFmpeg编码器、滤镜和libass。
- 中文字幕字体。
- NVIDIA显卡和显存。
- Ollama和Whisper。
- 实际H.264/AAC/ASS合成渲染。
- 真实素材分类。
- 40秒边界。
- 可选真实试剪。

详细说明：

```text
docs/script-mixer-integration-check.md
```

---

# AI短剧导演物料链

短剧生产层级：

```text
episode 单集
  → scene 场
    → generation_clip 生成片段（4～15秒）
      → shot 镜头
```

主命令：

```bash
short-drama-controller-v02 doctor
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

主流程：

```text
chapter_intake
→ story_events
→ characters / scenes / props
→ world_bible / style_bible
→ asset_lock
→ beat_map
→ clip_plan
→ shot_plan
→ coverage_qa
```

Codex Skill：

```text
.agents/skills/ai-short-drama-controller/
```

显式调用：

```text
$ai-short-drama-controller
```

存在BLOCKER时禁止正式导出。返修覆盖目标文件，不生成`final_v2`、`fixed`或`最新版`等重复产物。

---

# 测试

```bash
pytest -q
pytest -q tests/test_script_mixer*.py
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
script-driven-mixer --help
```

自动化测试：

- Python 3.10和3.12。
- 不依赖网络、真实FFmpeg、Ollama、Whisper、剪映或私人素材。
- 使用假执行器验证命令契约。
- 覆盖40秒边界、Whisper对齐、字幕、集成验收、返修、回退、固定帧率代理、前后余量、候选导出、缓存和剪映轨道。

---

# 关键文档

```text
docs/script-driven-mixer.md
docs/script-mixer-integration-check.md
docs/script-mixer-review.md
docs/jianying-edit-workflow.md
docs/script-mixer-next-development-plan.md
```

---

# 当前边界

- AI画面理解和镜头切分不能保证100%符合导演判断。
- Whisper仍需人工检查错字、断句和专有名词。
- 固定帧率代理能减少技术性卡帧，但不能修复原素材已经损坏的帧。
- 剪映草稿格式属于私有格式，版本升级可能影响直接草稿兼容性。
- 标准MP4、WAV、SRT和CSV编辑包始终保留，作为稳定底座。
- 背景音乐和音效自动选择尚未完成。
- TTS自动配音尚未完成。
- 多来源混剪不等于获得版权授权。
- 正式发布前必须人工检查画面、声音、字幕、事实和素材权利。
