# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.4.0`

## purpose 目的

Use this skill to control AI short drama production workflows. It converts scripts, novel chapters, rough ideas, or partial prompts into a constrained, producible short-drama project with locked assets, storyboard plans, platform prompts, QA reports, and repair actions.

使用本 Skill 时，必须优先稳定性，不追求“一键大片”。任何输入都要先做章节解析、事件链、资产锁定、节拍表、分镜计划，再生成提示词和导出包。

## entrypoint 入口

`short-drama-controller-v02` 必须指向：

```text
short_drama_controller.v02_full_cli:main
```

主流程命令：

```bash
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02
short-drama-controller-v02 export --project demo_v02
```

## hard_rules 硬规则

1. All output fields must use `english_name 中文字段`.
2. Always run `scope_gate 范围闸门` first.
3. 小说章节输入后必须先生成 `chapter_intake / story_events / characters / scenes / props / world_bible / style_bible / asset_lock`。
4. 分镜必须基于 `story_events -> beat_map -> shot_plan`，不能从原文直接硬切。
5. 每个 shot 必须绑定 `source_quote / event_id / beat_id / scene_id / character_id / prop_id`。
6. `coverage_qa 关键实体覆盖QA` 必须检查主要人物、主要场景、关键道具、核心事件。
7. 只要存在 `BLOCKER`，`export` 必须禁止导出。
8. `qa.md` 必须记录 `allow_export 允许导出`。
9. 导出视频提示词文件名统一为 `exports/video_prompts.md`，禁止混用 `v02_video_prompts.md`。
10. Repair must replace the target file, not create endless repaired copies.

## role_card_rule 角色卡规则

每个主要角色必须包含：身份、年龄感、外貌、发型、服装、标志物、性格/表演方式、禁止变化项、正面/侧面/背面三视图提示词、表情/动作参考提示词。

## world_style_rule 世界观与风格规则

对玄幻、民俗、打戏、悬疑类文本必须生成：世界观规则、力量体系、禁忌、视觉关键词、色卡、光影规则、镜头语言、场景美术规则。

## action_rule 动作/打戏规则

如果文本包含追逐、攻击、打击、妖物、武器、受伤、死亡等内容，必须生成 `action_choreography 动作编排表`，包含：起始姿态、结束姿态、攻击线/移动线、接触点、速度、结果、风险等级、备用镜头、宫格硬切提示词。

## qa_rule 质检规则

`coverage_qa` 必须把以下情况标记为 `BLOCKER`：

```text
主要人物缺失
主要场景缺失
关键道具缺失
核心事件缺失
原文存在明确场景但只生成泛化场景
原文明显有多人互动但只识别 1 个角色
```

## test_rule 测试规则

必须通过：

```bash
pytest -q
```

smoke test 必须使用临时目录或允许传入 `--out`，不得删除仓库固定目录。

## copyright_safety 版权安全

When input is a reference film, learn only structure, rhythm, shot logic, character function, and reusable production pattern. Do not copy exact names, dialogue, plot, character identity, or worldbuilding.
