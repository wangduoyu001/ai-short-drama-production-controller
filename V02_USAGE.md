# v0.2 使用说明

v0.2 作为独立核心模块存在，避免直接打乱 v0.1 主入口。安装后可使用独立命令：

```bash
python -m pip install -e .

short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 export --project demo_v02
short-drama-controller-v02 grid --project demo_v02 --shot SH005
```

也可以不安装，直接运行：

```bash
python -m short_drama_controller.v02_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
```

## v0.2 新增重点

- `v02_dialogue.py`：OS / 出口对白拆分，单说话主体正反打。
- `v02_assets.py`：角色、场景、道具提取，生成基础锁定字段。
- `v02_storyboard.py`：8-12镜结构，含主镜头、正反打、插入镜头、反应镜头、结尾钩子。
- `v02_prompts.py`：图片提示词、视频提示词、宫格硬切提示词。
- `v02_qa.py`：检查资产锁、运动轨迹、机位、嘴型、场景音效。
- `v02_repair.py`：返修缺失字段并覆盖当前项目文件。
- `v02_exporters.py`：导出视频提示词、宫格提示词、分镜表、音效表。
- `v02_cli.py`：独立命令入口。

## 视频提示词新增音效字段

每个镜头都必须包含：

- `ambience_sfx 环境底音`
- `foley_sfx 拟音`
- `prop_sfx 道具音`
- `action_sfx 动作音`
- `music_note 音乐建议`
- `silence_note 静默说明`

## 黑屏冻结锚使用边界

黑屏冻结锚只用于 `grid_cut_mode 宫格硬切模式`。普通单镜头不强制使用。它的作用是让宫格图更容易按子格硬切，而不是把整张拼图一起动。

## 导出文件

运行 `export` 后会生成：

```text
exports/
├─ v02_video_prompts.md
├─ v02_grid_prompts.md
├─ v02_shot_table.csv
└─ v02_sound_table.csv
```

## 质量原则

- v0.2 暂不覆盖 v0.1 默认入口。
- 先保证模块职责清晰，再逐步合并。
- 必须通过 `tests/test_v02_smoke.py` 的基础流程测试后再继续扩展。
