# v0.2 主推荐入口

v0.2 已作为当前主推荐流程。由于保留 v0.1 方便回滚，旧命令仍然存在。

## 推荐运行方式

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

## v0.2 已补齐

- 更强说话人识别与角色绑定。
- shot_size_jump 景别跳变 QA。
- speaker_spatial_anchor 说话人空间锚点强校验。
- source_coverage 原文覆盖检查。
- project.yaml schema 校验。
- v02 full smoke workflow。

## 说明

`short-drama-controller-v02` 的 pyproject 入口后续可指向 `v02_full_cli`。当前最稳运行方式是 `python -m short_drama_controller.v02_full_cli`。
