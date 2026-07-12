# AI Short Drama Production Controller / AI短剧生产控制器

版本：`0.5.0`

> Compatibility entry / 兼容入口
>
> Codex 的正式 Skill 位于：
> `.agents/skills/ai-short-drama-controller/SKILL.md`
>
> 本文件保留给旧工作流、人工阅读和其他 Agent 框架使用。不要在这里维护第二套互相冲突的规则。

## purpose 目的

将小说、已有剧本、故事大纲、口述创意或半成品提示词转换为可执行的 AI 短剧/漫剧导演物料包。交付内容包括剧本、资产锁定、生成片段、故事板、视频提示词、QA 和返修方案，不声称直接生成最终视频。

## core_hierarchy 核心层级

```text
episode 单集（通常2-3分钟）
  -> scene 场
    -> generation_clip 生成片段（4-15秒，通常10-15秒）
      -> shot 镜头
```

禁止把 15 秒生成片段误写成完整一集。

## entrypoint 入口

```text
short_drama_controller.v02_full_cli:main
```

```bash
python -m pip install -e .
short-drama-controller-v02 doctor
short-drama-controller-v02 init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
short-drama-controller-v02 qa --project demo_v02
short-drama-controller-v02 repair --project demo_v02 [--shot SH003]
short-drama-controller-v02 export --project demo_v02
```

## hard_rules 硬规则

1. All structured fields use `english_name 中文字段`.
2. Preserve the user's source input.
3. Only execute the stage explicitly requested by the user.
4. Full workflow order:
   `chapter_intake -> story_events -> world_bible/style_bible -> asset_lock -> beat_map -> clip_plan -> shot_plan -> prompts -> qa -> export`.
5. 分镜不能从原文直接硬切，必须经过事件链、节拍表和生成片段规划。
6. 每个 shot 必须绑定 source、event、beat、clip、scene、character、prop、start state 和 end state。
7. 资产一致性优先于视觉花哨，必须锁定脸、年龄、身材、发型、服装、材质、颜色、武器、场景结构和空间锚点。
8. 对白场景必须明确人物站位、视线、轴线和安全机位区。
9. 动作镜头必须明确起势、步法、运动线、攻击线、防守线、接触点、受力方向、结果和复位站位。
10. 高风险镜头必须提供 fallback shot 备用镜头。
11. Repair must overwrite the target output, not create `v2/final/fixed/最新版` copies.
12. Any `BLOCKER` must prevent export.
13. Do not create decorative or duplicate Markdown files.
14. Do not claim external model integration unless code for that integration exists.

## codex_usage Codex使用

Open the repository in Codex and explicitly invoke:

```text
$ai-short-drama-controller
```

The Skill disables implicit invocation so ordinary conversation does not accidentally start the entire production workflow.

## test_rule 测试规则

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
```

Tests must be deterministic and must not require network access.

## copyright_safety 版权安全

When input is a reference film, learn only structure, rhythm, shot logic, character function, and reusable production patterns. Do not copy exact names, dialogue, plot, character identity, or worldbuilding.
