# 文案驱动本地混剪：真实电脑集成验收

## 目的

本阶段验证仓库代码在真实 Windows 或 macOS 电脑上是否具备可运行条件，而不只是在 GitHub Actions 的无媒体测试环境中通过。

集成验收分为三层：

```text
环境可用 environment_ready
→ 素材和文案已准备 ready_for_real_trial
→ 真实预览已经成功导出 trial_completed
```

三个状态不能混为一个“成功”。环境通过不代表真实素材已经试剪，真实素材可读也不代表最终MP4已经生成。

## 输出位置

默认报告：

```text
.runtime/script_mixer/integration_report.json
```

合成测试文件：

```text
.runtime/script_mixer/integration/synthetic_render/
├─ integration.ass
└─ integration.mp4
```

真实试剪仍写入：

```text
outputs/script_mixer/integration_<时间>/
```

## 第一层：基础环境检查

```bash
script-driven-mixer --config script_mixer.local.json integration-check
```

该命令检查：

1. Python版本是否为3.10或更高。
2. 运行目录、数据库目录和输出目录是否可写。
3. 可用磁盘空间是否达到配置阈值。
4. SQLite数据库能否初始化和迁移。
5. FFmpeg与FFprobe是否存在。
6. Ollama、Whisper和NVIDIA工具是否存在。
7. FFmpeg是否具备：
   - `libx264`
   - `AAC`
   - `subtitles/libass`
   - `scale`
   - `crop`
   - `concat`
   - `loudnorm`
   - `sidechaincompress`
8. 配置的中文字幕字体或其他CJK字体是否存在。
9. NVIDIA显卡、驱动和显存状态。
10. 本地文本、视觉、嵌入和Whisper模型状态。
11. 是否可以实际生成一条带中文ASS字幕、H.264视频和AAC音频的合成MP4。

基础检查不会扫描用户素材，也不会运行真实30秒试剪。

退出码：

- `0`：环境阻塞项为空。
- `1`：存在阻塞项。

## 第二层：真实素材与40秒边界

快速增量扫描：

```bash
script-driven-mixer --config script_mixer.local.json integration-check \
  --media-root "D:/你的素材目录" \
  --script input.txt
```

完整场景检测和缩略图：

```bash
script-driven-mixer --config script_mixer.local.json integration-check \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --full-media-scan
```

该阶段验证：

- 素材目录可读。
- 至少产生一个可用原视频和镜头。
- 快速扫描和完整扫描都遵守40秒窗口。
- 所有镜头满足：

```text
source_start >= 0
source_end <= 40.0
```

- 报告真实素材分类：
  - 横屏。
  - 竖屏。
  - 有音轨。
  - 无音轨。
  - 10秒以内。
  - 超过40秒。
- 记录新增、变化和未变化文件数量。
- 证明重复执行可以利用增量索引续跑。

真实素材清单模板：

```text
config/script_mixer.integration-checklist.example.json
```

模板中的路径保持空白，实际电脑只在命令行或本地忽略配置中填写路径。

## 第三层：真实预览试剪

没有配音，使用原视频音频：

```bash
script-driven-mixer --config script_mixer.local.json integration-check \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --full-media-scan \
  --run-trial \
  --trial-duration 30
```

使用真实配音：

```bash
script-driven-mixer --config script_mixer.local.json integration-check \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --voice voice.wav \
  --full-media-scan \
  --run-trial
```

不运行Whisper：

```bash
script-driven-mixer --config script_mixer.local.json integration-check \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --voice voice.wav \
  --run-trial \
  --no-transcribe-trial
```

真实试剪会：

1. 使用本地素材库规划时间线。
2. 强制排除本机不存在的旧素材路径。
3. 验证时间线没有引用任何源视频40秒后的区间。
4. 根据是否提供配音选择：
   - 有配音：`mixed`。
   - 无配音：`source`。
5. 生成字幕。
6. 烧录优先级最高的可用字幕。
7. 调用FFmpeg生成MP4。
8. 记录规划耗时、渲染耗时和实时倍率。
9. 记录试剪前后GPU显存快照。

## 完整验收编排

推荐在最终真实电脑验收时运行跨平台编排脚本：

```bash
python scripts/script_mixer_acceptance.py \
  --config script_mixer.local.json \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --voice voice.wav
```

编排顺序：

```text
基础环境预检
→ 完整素材扫描
→ Ollama视觉分析
→ 语义向量构建
→ 再次增量检查
→ Whisper时间对齐
→ 真实30秒试剪
→ MP4渲染
→ 合并验收报告
```

大素材库可以先限制本次语义处理数量：

```bash
python scripts/script_mixer_acceptance.py \
  --config script_mixer.local.json \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --voice voice.wav \
  --enrich-limit 100 \
  --embedding-limit 500
```

没有本地Ollama模型时，跳过语义索引：

```bash
python scripts/script_mixer_acceptance.py \
  --config script_mixer.local.json \
  --media-root "D:/你的素材目录" \
  --script input.txt \
  --skip-semantic-index
```

该模式仍可验证扫描、40秒窗口、规则式检索、原声、字幕和FFmpeg渲染，但不能证明本地视觉模型与向量链正常。

## 可续跑策略

系统不把“续跑”理解为盲目跳过所有旧步骤。

当前策略：

- 环境检查很便宜，每次重新执行。
- 素材扫描通过文件指纹跳过未变化文件。
- 视觉分析跳过已有描述的镜头。
- 向量构建按镜头、模型和内容哈希跳过未变化向量。
- 已生成项目保留完整JSON、字幕和渲染计划。
- 每个检查完成后立即原子写入报告。
- 中途失败后重新执行，不要求删除数据库。

## 报告关键字段

```text
environment_ready       环境阻塞项是否为空
ready_for_real_trial    环境、素材和文案是否具备试剪条件
trial_completed         真实MP4是否已经成功生成
blockers                必须修复的问题
warnings                可降级运行但影响质量的问题
checks                  每项检查及修复建议
performance             各阶段耗时和渲染倍率
acceptance_session       完整编排脚本追加的语义准备统计
```

每个检查包含：

```text
check_id
status
message
duration_ms
blocker
details
remediation
```

状态定义：

- `pass`：通过。
- `warn`：可以继续，但质量或能力不完整。
- `fail`：失败；`blocker=true`时禁止视为完成。
- `skip`：本次没有提供相关输入或没有显式请求昂贵操作。

## 手工验收

自动报告无法判断所有审美和听感问题。最终还需人工确认：

- 视频可以正常播放。
- 音画同步可接受。
- 中文字幕没有方框、乱码或缺字。
- 配音清晰。
- 原声压低程度合理。
- 没有使用任何原视频40秒后的画面。
- 镜头匹配没有明显语义错误。
- 素材权利状态可用于目标发布场景。

手工结果填写在本地复制的验收清单中，不提交包含本机路径或私人素材信息的版本。

## 当前未覆盖

- 自动视觉判断字幕是否真的显示为正确汉字。
- 运行过程中的连续GPU显存峰值采样，目前记录试剪前后快照。
- 音画同步的自动感知评分。
- 真实素材版权状态自动判断。
- 达芬奇、Premiere和剪映工程导入验收。
