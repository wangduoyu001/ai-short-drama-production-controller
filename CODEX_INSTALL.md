# CODEX_INSTALL / Codex安装说明

本仓库是 `Codex Skill / Codex技能`。Codex / WorkBuddy 负责导演分析，Python 负责 QA / 质检、repair / 返修、export / 导出。

## 安装

```bash
git clone https://github.com/wangduoyu001/ai-short-drama-production-controller.git
cd ai-short-drama-production-controller
python -m pip install -e .
python scripts/install_for_codex.py
```

## v0.3.1 主流程

v0.3.1 使用 `clip_first / 片段优先`：先拆 4-15 秒 generation_clip / 生成片段，再生成 beat_map / 剧情节拍表 和 shots / 分镜列表。

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
clip_id 片段编号
clip_type 片段类型
clip_duration_seconds 片段时长秒数
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

## v0.3.1 必查结构

```text
clip_plan 片段计划
beat_map 剧情节拍表
director_read 导演读本
approval_gates 确认闸门
storyboard_grid_ascii 分镜总览简笔图
source_text_ref 原文引用位置
evidence_quote 原文证据句
invented_flag 是否AI补充
```

每个 clip / 片段 必须有：

```text
clip_id 片段编号
clip_type 片段类型
duration_seconds 时长秒数
model_duration_limit 模型时长限制
beat_range 节拍范围
shot_density 镜头密度
shot_count_target 目标镜头数
```

每个 beat / 节拍 必须有：

```text
beat_id 节拍编号
clip_id 片段编号
clip_type 片段类型
clip_duration_seconds 片段时长秒数
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

## clip-first / 片段优先规则

- 每个 generation_clip / 生成片段 必须控制在 4-15 秒。
- 场景数量由原文决定，不再默认 1 个场景。
- 全局人物数量由原文决定，不再默认 2-3 人。
- 单镜最多调度 3 个核心人物。
- fight_clip / 打戏片段 默认高镜头密度：10-24 镜 / 10-15 秒。

## Skill 入口

Codex 必须优先读取：

```text
skills/ai_short_drama_production_controller/SKILL.md
```

然后再运行主流程。不要把 v0.1 / v0.2 当主流程。旧入口还活着，就像地板下传来键盘声，听着就不吉利。
