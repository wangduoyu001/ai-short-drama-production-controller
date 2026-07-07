# AI Short Drama Production Controller / AI短剧生产控制器

面向 AI 短剧生产的流程控制 Skill / 技能。它不是“一键生成短剧”的玄学按钮，而是把参考片、剧本、小说片段、口述创意或半成品 Prompt / 生成提示词，整理成导演可用的标准化生产物料包。

## core_features 核心功能

- `scope_gate 范围闸门`：一开始限制项目大小，防止项目爆炸。
- `source_text 原文`：保留故事原文，避免 AI 只写总结。
- `source_evidence 原文证据链`：每个镜头标明原文引用、证据句、是否为导演补足，降低 AI 幻觉。
- `approval_gates 确认闸门`：剧本、资产、分镜、提示词、导出都默认 pending / 待确认。
- `asset_lock 资产锁定`：控制人物脸、服装、道具、场景、色卡一致性。
- `dialogue_control 对白控制`：区分 OS / 画外音与出口对白，控制嘴型。
- `director_read 导演读本`：判断场景功能、场景转折、观众视角、权力变化、潜台词。
- `director_intent 导演意图`：每个镜头服务一个明确观众感受，不堆“电影感”空词。
- `storyboard_ascii 简笔分镜图`：输出分镜总览图、对白覆盖图、单镜头简笔图、动作六宫格。
- `clip_contract 单段镜头合同`：每段只拍当前任务，后续剧情不能提前演完。
- `producer_plan 制片执行计划`：管理时长、素材、平台、风险、审批节点、成本和返修预算。
- `sound_plan 声音设计计划`：管理对白、旁白、环境音、拟音、动作音、音乐和静默。
- `project_state_capsule 项目状态胶囊`：保存真实生成状态，下一段基于实际结尾继续。
- `qa_gate 质检闸门`：PASS / 通过、WARN / 警告、BLOCKER / 阻塞。
- `repair_replace 返修替换`：返修后覆盖当前项目文件，不制造垃圾文档。
- `prompt_mode 单条提示词模式`：只生成一条可复制提示词，不创建项目目录。
- `export_pack 平台导出`：导出视频提示词、宫格提示词、镜头表、声音表、制片表。

## install 安装

```bash
python -m pip install -e .
```

## v0.2.3 quick_start 快速开始

当前主推荐入口：

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
python -m short_drama_controller.v02_full_cli grid --project demo_v02 --shot SH005
```

单条提示词模式：

```bash
python -m short_drama_controller.v02_full_cli prompt --text "夜色中的破庙里，少年握着断刀，背对门口。他低声说：你终于来了。"
```

暂时不优先依赖 `short-drama-controller-v02` 快捷命令，避免安装入口被旧缓存影响。

## v0.2.3 output 项目输出

```text
demo_v02/
├─ project.yaml
├─ script.md
├─ assets.md
├─ storyboard.md
├─ producer.md
├─ sound.md
├─ prompts.md
├─ qa.md
└─ exports/
   ├─ video_prompts.md
   ├─ grid_prompts.md
   ├─ shot_table.csv
   ├─ sound_table.csv
   └─ producer_table.csv
```

## storyboard_rule 分镜图规则

`storyboard.md / 分镜执行文档` 必须包含：

```text
storyboard_grid_ascii 分镜总览简笔图
dialogue_coverage_ascii 对白覆盖图
sketch_ascii 简笔手绘图
movement_arrow 运动箭头
camera_arrow 镜头箭头
motion_grid_ascii 动作拆解六宫格（高风险镜头才需要）
```

## anti_hallucination_rule 防幻觉规则

每个镜头必须包含：

```text
source_text_ref 原文引用位置
evidence_quote 原文证据句
adaptation_note 改编说明
invented_flag 是否AI补充
source_confidence 原文置信度
unknown_policy 不确定处理规则
```

不确定内容必须标注为 `director_bridge 导演补足`，不能伪装成原文事实。

## document_rule 文档规则

只允许生成上面的固定物料包。修复、优化、返修后直接覆盖旧文档，禁止生成：

```text
final / 最终版 / v2 / fixed / new / summary / report
```

人类已经发明了足够多垃圾文档，不需要本仓库继续参与造纸。

## field_rule 字段规则

所有字段采用：

```text
english_name 中文字段
```

例如：

```text
character_id 角色编号
camera_movement 机位运动
motion_path 运动轨迹
continuity_locks 连续性锁定
ambience_sfx 环境底音
speaker_mode 发声模式
mouth_state 嘴型状态
director_intent 导演意图
clip_contract 单段镜头合同
producer_plan 制片执行计划
sound_plan 声音设计计划
```

## smoke_test 烟雾测试

```bash
python scripts/v02_smoke.py
```

GitHub Actions 会在 push / PR 时运行 v0.2 smoke test。
