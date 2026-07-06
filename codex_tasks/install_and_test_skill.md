# Codex任务：安装并测试AI短剧生产控制器Skill

你现在在仓库根目录。请严格按以下步骤执行，不要擅自重构。

## 目标

安装并测试 AI Short Drama Production Controller Skill，确认 v0.2 主推荐流程可运行。

## 步骤

```bash
python -m pip install -e .
python scripts/install_for_codex.py
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

## 验收标准

必须存在：

```text
demo_v02/project.yaml
demo_v02/storyboard.md
demo_v02/prompts.md
demo_v02/qa.md
demo_v02/exports/v02_video_prompts.md
demo_v02/exports/v02_grid_prompts.md
demo_v02/exports/v02_shot_table.csv
demo_v02/exports/v02_sound_table.csv
```

## 不要做

- 不要重写 v0.1 入口。
- 不要删除 `v02_full_cli.py`。
- 不要把 `demo_v02/` 提交进仓库，除非用户明确要求。
- 不要复制第三方提示词模板原文。
- 不要把返修结果另存一堆新文件。

## 成功后回复

请用中文回复：

```text
Skill安装完成，v0.2主流程可运行。
已生成：project.yaml、storyboard.md、prompts.md、qa.md、exports。
```
