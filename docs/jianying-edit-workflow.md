# 剪映人工修改工作流

## 最终目标

系统负责：

```text
扫描素材
→ 每个源视频只处理前40秒
→ 理解文案和画面
→ 自动粗剪
→ 语音对齐和字幕
→ 输出预览
→ 输出可编辑镜头、原声、配音、字幕和候选
→ 尝试创建剪映草稿
```

用户最后在剪映中：

```text
拖动镜头边缘
→ 调整切点
→ 替换候选画面
→ 调整原声、配音和字幕
→ 添加音乐、转场和特效
→ 正式导出
```

自动粗剪不是最终审美裁决。系统优先保证剩余问题容易修改，而不是声称概率模型永远不会犯错。

## 安装

Windows推荐由Codex在仓库根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_jianying_windows.ps1
```

允许脚本通过winget安装FFmpeg：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_jianying_windows.ps1 -InstallMissingTools
```

等价的手工安装命令：

```bash
python -m pip install -e ".[jianying]"
script-driven-mixer init-config --out script_mixer.local.json
script-driven-mixer --config script_mixer.local.json init-db
script-driven-mixer --config script_mixer.local.json integration-check
script-driven-mixer --config script_mixer.local.json jianying-status
```

`pyJianYingDraft`是剪映草稿生成的可选依赖。标准编辑包不依赖它。

## 剪映草稿目录

在剪映专业版中打开：

```text
全局设置 → 草稿位置
```

将该目录填入本地配置：

```json
{
  "edit_package": {
    "jianying_draft_root": "D:/JianyingPro Drafts"
  }
}
```

或者运行时指定：

```bash
--draft-root "D:/JianyingPro Drafts"
```

检查：

```bash
script-driven-mixer --config script_mixer.local.json jianying-status
```

## 一键生成

有真实配音：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 `
  -MediaRoot "D:\视频素材" `
  -Script "input.txt" `
  -Voice "voice.wav" `
  -DraftRoot "D:\JianyingPro Drafts"
```

没有配音，使用原视频声音：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_jianying_project.ps1 `
  -MediaRoot "D:\视频素材" `
  -Script "input.txt" `
  -DraftRoot "D:\JianyingPro Drafts"
```

第一次只想验证链路，不运行Ollama视觉分析和向量：

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

执行内容：

```text
增量扫描
→ 可选视觉分析
→ 可选向量构建
→ 文案和配音时间轴
→ 自动粗剪
→ final.mp4预览
→ 固定帧率代理
→ 原声分段
→ 配音WAV
→ 字幕
→ 备用候选
→ 剪映草稿
```

## 已有项目重新导出剪映包

返修时间线后：

```bash
script-driven-mixer --config script_mixer.local.json export-jianying-package \
  --project <项目ID> \
  --draft-root "D:/JianyingPro Drafts"
```

不生成草稿，只要稳定编辑包：

```bash
script-driven-mixer --config script_mixer.local.json export-jianying-package \
  --project <项目ID> \
  --no-draft
```

草稿必须成功，否则命令失败：

```bash
script-driven-mixer --config script_mixer.local.json export-jianying-package \
  --project <项目ID> \
  --draft-root "D:/JianyingPro Drafts" \
  --require-draft
```

默认不要求草稿成功。草稿不兼容时，标准编辑包仍然完整可用。

## 输出结构

```text
outputs/script_mixer/<项目ID>/exports/
├─ final.mp4
└─ jianying_package/
   ├─ video/
   │  ├─ S001_SRC001_5.000-8.000.mp4
   │  ├─ S002_SRC008_2.000-5.000.mp4
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
   │  │  ├─ C01_....mp4
   │  │  ├─ C02_....mp4
   │  │  └─ C03_....mp4
   │  └─ ...
   ├─ metadata/
   │  ├─ package_manifest.json
   │  ├─ timeline.csv
   │  └─ ffmpeg_commands.json
   └─ 剪映导入与修改说明.txt
```

## 为什么镜头可以自由拉动

系统选择的原区间例如：

```text
5秒 ～ 8秒
```

默认导出代理：

```text
4秒 ～ 9秒
```

剪映中实际使用：

```text
代理文件内 1秒 ～ 4秒
```

因此保留：

```text
前1秒余量
后1秒余量
```

你可以在剪映中把镜头边缘向前或向后拖动，而不需要重新打开原始长视频。

余量不会突破每个源视频前40秒的总规则。例如选中区间为38～40秒时：

```text
导出区间：37～40秒
后余量：0秒
```

不会为了方便拖动，偷偷把40秒后的内容塞回来。

## 如何减少卡帧、跳帧和黑帧

编辑包中的镜头全部重新编码为：

```text
固定帧率
H.264
统一分辨率
统一画幅
统一像素格式yuv420p
从精确帧位置重新解码
```

不是使用只在关键帧附近准确的无损复制截取。

这主要解决：

- 手机可变帧率导致时间线漂移。
- 不同编码和帧率拼接卡顿。
- 非关键帧起切导致黑帧或花屏。
- 时间戳异常造成首帧停顿。

它不能保证画面语义和动作切点永远完美，所以仍保留余量、候选和剪映草稿。

## 剪映中的轨道

草稿成功时包含：

```text
视频轨：AI粗剪视频
音频轨：原声
音频轨：配音
字幕轨：字幕
```

原声和配音是独立轨道，可以单独调音量、删除或移动。

当前画面镜头是独立片段，不是压平后的整条MP4。可以：

- 拖动镜头边缘。
- 改变镜头起止位置。
- 移动镜头顺序。
- 删除镜头。
- 从候选目录拖入其他画面。
- 修改字幕。
- 调整配音和原声。

## 草稿打不开怎么办

剪映草稿格式属于私有格式，新版本可能改变或加密。自动生成草稿失败时：

1. 打开 `jianying_package/video/`。
2. 按S001、S002顺序全部拖入剪映视频轨。
3. 导入 `audio/narration.wav`。
4. 需要原声时导入 `audio/Sxxx_source.wav`。
5. 导入 `subtitles/captions.srt`。
6. 使用 `metadata/timeline.csv` 检查时间和余量。
7. 从 `candidates/Sxxx/` 拖入备用镜头替换。

标准编辑包只依赖普通MP4、WAV、SRT和CSV，剪映升级不会让它整体失效。

## 增量复用

编辑包按以下内容生成哈希：

```text
源文件路径、大小和修改时间
源入点和出点
前后余量
目标画幅、帧率和编码
音频规格
```

再次导出时：

- 未变化镜头直接复用。
- 已替换镜头重新导出。
- 已变化候选重新导出。
- 配音未变化时复用。

强制重做：

```bash
--force-package
```

只查看将执行的FFmpeg命令：

```bash
--package-dry-run
```

## 推荐人工流程

```text
1. 先看final.mp4判断整体节奏
2. 打开剪映草稿
3. 调整切早、切晚的镜头边缘
4. 从候选目录替换语义不合适的镜头
5. 修改字幕错字和断句
6. 调整配音、原声和音乐
7. 添加转场和视觉效果
8. 剪映正式导出
```

## 当前真实边界

- 自动画面匹配不能保证100%符合导演判断。
- Whisper可提供较准的词级时间，但仍需要人工检查错字和断句。
- 固定帧率代理显著减少技术性卡帧，但不能修复原素材本身已经损坏的帧。
- 剪映草稿兼容性取决于本机剪映版本。
- 草稿生成成功不等于剪映所有版本都一定能打开。
- 标准编辑包是长期稳定底座。
- 素材版权仍需人工确认。
