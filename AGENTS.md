# Repository instructions / 仓库执行规则

## Mission / 目标

This repository produces a director-ready material package for AI short drama and AI comic-drama production. It does not claim to generate a finished film by itself.

本仓库交付的是可执行的导演物料包，不是“一键成片”演示。优先保证故事完整、资产一致、空间连续、动作可生成和返修可控。

## Working rules / 工作规则

1. Preserve the user's original source file. Never silently rewrite or overwrite the input novel, script, outline, or idea.
2. All structured field names must use `english_name 中文字段`.
3. Treat one episode and one generation clip as different levels:
   - `episode 单集`: normally 2-3 minutes unless the user specifies otherwise.
   - `generation_clip 生成片段`: 4-15 seconds, normally 10-15 seconds.
4. Build in this order:
   `chapter_intake -> story_events -> world_bible/style_bible -> asset_lock -> beat_map -> clip_plan -> shot_plan -> prompts -> qa -> export`.
5. Never create decorative or duplicate Markdown files. Repair must overwrite the existing target file. Do not create names such as `final_v2`, `fixed`, `new`, or `最新版`.
6. Use only the documented project files and `exports/` outputs. Do not add a new document unless it has a distinct production purpose and is added to the README contract.
7. Asset consistency outranks visual novelty. Lock face, age, body proportion, hairstyle, costume material, costume color, prop shape, scene layout, and spatial anchors before shot planning.
8. Every shot must retain source evidence and bind to event, beat, scene, character, prop, clip, start state, and end state.
9. Every action or fight shot must define start pose, movement path, attack line, contact point, force/result, screen direction, camera side, end pose, and fallback shot.
10. Keep the camera on the same side of the axis unless a neutral shot or explicit axis-crossing transition is planned.
11. Ask at most one consolidated clarification when a missing parameter blocks production. Otherwise use explicit defaults and record them as assumptions.
12. Do not claim that this repository directly calls Seedance, Kling, Jimeng, Veo, Sora, or another external generation service unless an actual integration exists.

## Output priorities / 输出优先级

The human-readable production package should make these items easy to find:

1. `script.md` - readable episode script and story direction.
2. `assets.md` - complete character, scene, and prop generation prompts.
3. `storyboard.md` - shot order, composition, camera, blocking, movement, force/contact, and continuity.
4. `prompts.md` - generation-ready image/video prompts.
5. `qa.md` - blockers, warnings, repair actions, and export permission.
6. `exports/` - platform-ready prompts and tables.

## Code changes / 代码修改

- Keep Python compatibility at 3.10 or newer.
- Do not add a runtime dependency unless the behavior cannot be implemented with the standard library.
- After changing Python or workflow contracts, run:

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
```

- A `BLOCKER` must prevent export.
- New tests must be deterministic and must not require network access.
