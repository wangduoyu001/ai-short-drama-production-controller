# CODEX_INSTALL / Codex安装说明

本仓库是 `Codex Skill / Codex技能`。Codex / WorkBuddy 负责导演分析，Python 负责 QA / 质检、repair / 返修、export / 导出。

## 安装

```bash
git clone https://github.com/wangduoyu001/ai-short-drama-production-controller.git
cd ai-short-drama-production-controller
python -m pip install -e .
python scripts/install_for_codex.py
```

## v0.3 主流程

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
```

## targeted repair / 定向返修

只修一个镜头时使用：

```bash
python -m short_drama_controller.v02_full_cli repair --project demo_v02 --shot SH003
```

定向返修只应该修改指定 shot / 镜头、对应 beat / 节拍、QA / 质检和导出结果，不应无故重写全项目。

## 单条提示词模式

```bash
python -m short_drama_controller.v02_full_cli prompt --text "夜色中的破庙里，少年握着断刀，背对门口。他低声说：你终于来了。"
```

该模式不创建项目目录，不生成 md 文档，只在终端输出：

```text
image_prompt 图片提示词
video_prompt 视频提示词
sound_prompt 声音提示词
negative_prompt 负面提示词
fallback_prompt 备用提示词
```

## 固定交付物白名单

完整流程只允许生成：

```text
project.yaml
script.md
assets.md
storyboard.md
producer.md
sound.md
prompts.md
qa.md
exports/video_prompts.md
exports/grid_prompts.md
exports/shot_table.csv
exports/sound_table.csv
exports/producer_table.csv
```

禁止生成 `final / 最终版 / v2 / fixed / new / report / summary / 优化建议 / 修复记录`。

## v0.3 必查结构

```text
beat_map 剧情节拍表
director_read 导演读本
approval_gates 确认闸门
storyboard_grid_ascii 分镜总览简笔图
source_text_ref 原文引用位置
evidence_quote 原文证据句
invented_flag 是否AI补充
```

每个 beat / 节拍 必须有：

```text
beat_id 节拍编号
source_quote 原文证据
visible_action 可见动作
dialogue 对白
conflict 冲突
emotion_shift 情绪变化
power_shift 权力变化
subtext 潜台词
shot_hint 镜头建议
scene_hint 场景建议
characters 相关角色
```

## 多场景多人物规则

- 多场景项目中，每个 beat / 节拍 必须有 `scene_hint 场景建议`。
- 每个 shot / 镜头 必须绑定 `scene_id 场景编号`。
- 每个 beat / 节拍 必须有 `characters 相关角色`。
- 单镜最多调度 3 个核心人物，超过 3 个应拆镜或标为 crowd / 群像。

## Skill 入口

Codex 必须优先读取：

```text
skills/ai_short_drama_production_controller/SKILL.md
```

然后再运行主流程。不要把 v0.1 / v0.2 当主流程。人类项目最怕旧入口还活着，像软件坟地里伸出来的手。
