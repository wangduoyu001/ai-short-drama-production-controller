---
name: ai-short-drama-controller
description: 将小说、剧本、创意或半成品提示词转换为可执行的AI短剧/漫剧导演物料包。用于剧本改写、分集、10-15秒生成片段拆分、人物场景道具资产锁定、故事板、打戏动作设计、视频提示词、QA和返修；不用于直接声称生成最终视频。
---

# AI Short Drama Production Controller / AI短剧生产控制器

## Purpose / 用途

把用户输入转换为可阅读、可生图、可生成视频、可返修的导演物料包。稳定性、一致性和可执行性优先于华丽描述。

## Invocation boundary / 调用边界

Use this skill when the user asks for one or more of these tasks:

- 小说、剧本或创意改写为AI短剧/漫剧剧本
- 2-3分钟单集拆分为多个4-15秒生成片段
- 人物、场景、道具资产提取与生成提示词
- 故事板、镜头执行表、机位、人物调度、动作轨迹
- 武侠、追逐、打斗或复杂动作设计
- Seedance、即梦、可灵、Veo等平台的视频提示词
- 质检、返修、失败镜头降级和导出物料

Do not use this skill to:

- 声称已经调用外部视频模型并生成成片
- 下载或复制受版权保护的完整影视作品
- 在用户只问一个简单概念时强行启动整套生产流程

## Stage discipline / 阶段纪律

Only execute the stage the user requested.

用户只要求剧本时，只交付剧本；只要求资产时，只交付资产；只要求视频提示词时，只交付视频提示词。除非用户明确要求全流程，不得自动生成整套文件。

Stages:

1. `rewrite 剧本改写`
2. `assets 资产提取`
3. `clips 生成片段拆分`
4. `storyboard 故事板`
5. `prompts 生成提示词`
6. `qa 质检返修`
7. `export 导出`

## Input handling / 输入处理

Classify the input internally as one of:

- `novel 小说`
- `script 已有剧本`
- `outline 大纲`
- `idea 创意`
- `partial_prompt 半成品提示词`

Do not force a valid script back through a novel-adaptation template.

Ask at most one consolidated clarification only when a missing parameter blocks the requested stage. Otherwise use these defaults and label them as assumptions:

- `language 语言`: 中文
- `aspect_ratio 画幅`: 16:9 横屏
- `episode_duration 单集时长`: 2-3分钟
- `generation_clip_duration 生成片段`: 10-15秒；模型或动作需要时可缩短至4-9秒
- `style 风格`: 根据题材推断的电影化风格，不擅自套固定画风
- `output_mode 输出模式`: 只输出当前阶段所需内容

## Mandatory production model / 强制生产层级

Never confuse an episode with a generation clip.

```text
episode 单集（通常2-3分钟）
  -> scene 场
    -> generation_clip 生成片段（4-15秒）
      -> shot 镜头（一个片段内可包含多个跳切镜头）
```

A 15-second generation limit means one generation clip, not one complete episode.

## Workflow / 工作流

When the user requests the full workflow, execute in this order:

1. Preserve the source input.
2. Build `chapter_intake 章节解析` and `story_events 事件链`.
3. Rewrite a readable script with clear temporal continuity, conflict, hook, and scene-state changes.
4. Build `world_bible 世界观` and `style_bible 风格圣经` only when the story requires them.
5. Extract and lock characters, scenes, and props.
6. Build `beat_map 剧情节拍表`.
7. Build `clip_plan 生成片段计划`.
8. Build `shot_plan 分镜计划`.
9. Generate image, first-frame, video, end-frame, sound, negative, and fallback prompts.
10. Run QA. Do not export while a `BLOCKER` exists.
11. Repair by replacing the target file or target shot, never by creating duplicate versions.

## Script rules / 剧本规则

- Use present tense.
- Past information must use `【闪回】` and `【闪回结束】`, triggered by a visible object, sound, or action.
- Mark each new scene with day/night, interior/exterior, location, environment sound, spatial positions, and obstacles when relevant.
- Dialogue must be directly speakable. Use `OS 内心独白` and `VO 画外音` only when necessary.
- Do not replace visible dramatic action with narration.
- Every scene must end with a changed situation, relationship, knowledge state, power balance, or emotional state.
- Preserve source causality. Do not compress a life-stage jump into a confusing montage merely to make the script shorter.

## Asset rules / 资产规则

Read [asset-contract.md](references/asset-contract.md) before generating asset prompts.

- Every asset prompt must be complete and standalone. Do not rely on a hidden master prompt.
- Lock identity, age, body proportion, hairstyle, costume, materials, colors, props, and scene layout.
- Character, scene, and prop prompts must use stable IDs.
- Do not insert user instructions, layout commentary, or explanations into the actual generation prompt.

## Storyboard rules / 故事板规则

Read [storyboard-contract.md](references/storyboard-contract.md) before generating a storyboard or shot plan.

Every shot must define:

- source evidence
- clip and shot ID
- duration
- shot size and camera angle
- camera position and camera movement
- axis line and safe camera side
- character start/end positions
- screen direction and eyeline
- movement path
- entry pose and exit pose
- foreground/midground/background
- prop anchor
- continuity locks
- first frame, end frame, and fallback

Do not place consecutive near-identical shots together. Prefer meaningful jump cuts between distinct shot-size groups or functional viewpoints.

## Action and fight rules / 动作与打戏规则

Read [action-contract.md](references/action-contract.md) before handling fights, pursuit, falls, weapon use, crowd action, or complex movement.

- Design visible physical mechanics, not full-screen effects.
- One shot should communicate one clear action node.
- Define attack line, defense line, contact point, force direction, body response, footwork, and reset position.
- Keep weapon reach and fighting style distinct.
- Use wide shots to establish geography, medium shots for exchanges, and close inserts for contact, grip, footwork, reaction, or damage.
- Complex actions must have a simpler fallback shot that preserves the story result.

## Repository execution / 仓库执行

When this repository is available, prefer its deterministic pipeline instead of manually fabricating project files.

```bash
python -m pip install -e .
short-drama-controller-v02 doctor
short-drama-controller-v02 init --input <source-file> --out <project-dir> --title <title>
short-drama-controller-v02 qa --project <project-dir>
short-drama-controller-v02 repair --project <project-dir> [--shot SH003]
short-drama-controller-v02 export --project <project-dir>
```

For direct chat input, write the text to an operating-system temporary UTF-8 file, run `init`, and remove the temporary file after project creation. Never leave temporary source copies in the repository.

## Output control / 输出控制

- Keep human-facing output concise and production-oriented.
- Do not dump internal analysis.
- Do not produce decorative summaries, self-evaluations, repeated checklists, or redundant Markdown.
- When the user requests copy-paste prompts, put only the finished prompts in the answer or requested file.
- All structured professional fields use `english_name 中文字段`.
- Repair replaces the old content. Never create `v2`, `final`, `fixed`, or `最新版` duplicates.

## QA / 质检

Before export verify:

- source events are covered
- major characters, scenes, and props are present
- asset locks are complete
- clip duration stays within model limits
- spatial continuity and axis rules are valid
- dialogue speaker and mouth state match
- action shots include start, contact/result, and end states
- first/end frames connect adjacent clips
- risky shots have fallback prompts
- no `BLOCKER` remains
