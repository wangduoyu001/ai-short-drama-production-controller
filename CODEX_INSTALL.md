# CODEX_INSTALL / Codex安装说明

你的使用方式是：Codex 拉取本仓库，然后把它当成 AI 短剧生产 Skill / 技能使用。

## 推荐方式

在 Codex 里执行：

```bash
git clone https://github.com/wangduoyu001/ai-short-drama-production-controller.git
cd ai-short-drama-production-controller
python -m pip install -e .
python scripts/install_for_codex.py
```

## 运行 v0.2 主推荐流程

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

## 固定交付物

运行后只允许生成以下物料包文件：

```text
project.yaml                 项目总控数据
script.md                    剧本拆解文档
assets.md                    资产锁定文档
storyboard.md                分镜执行文档
producer.md                  制片执行文档
sound.md                     声音设计文档
prompts.md                   生成提示词文档
qa.md                        质检返修文档
exports/video_prompts.md     视频提示词导出文档
exports/grid_prompts.md      宫格硬切提示词导出文档
exports/shot_table.csv       镜头执行表
exports/sound_table.csv      声音设计表
exports/producer_table.csv   制片执行表
```

修复、优化、返修后直接覆盖旧文件，禁止生成 `final / 最终版 / v2 / fixed / new` 副本文档。

## Skill入口

标准 Skill 文件在：

```text
skills/ai_short_drama_production_controller/SKILL.md
```

Codex 读取仓库时，应优先读取该文件，再运行 v0.2 主流程。

## 为什么不用只读根目录 SKILL.md

根目录 `SKILL.md` 是总说明；`skills/ai_short_drama_production_controller/SKILL.md` 是给 Codex 使用的安装级 Skill 入口。

## 当前主推荐入口

当前主推荐入口是：

```bash
python -m short_drama_controller.v02_full_cli
```

暂时不依赖 `short-drama-controller-v02` 快捷命令，避免安装入口被旧缓存影响。
