# Repository instructions / 仓库执行规则

## Mission / 目标

This repository produces a director-ready material package for AI short drama and AI comic-drama production. It does not claim to generate a finished film by itself.

本仓库交付的是可执行的导演物料包，不是“一键成片”演示。优先保证故事完整、资产一致、空间连续、动作可生成和返修可控。

`short_drama_controller/script_mixer/` 是独立的本地信息流粗剪子系统。它可以根据用户文案和本地素材目录生成时间线及预览成片，但不得把该能力描述成已经完成短剧生成平台集成，也不得改变主生产链的输出契约。

## Working rules / 工作规则

1. Preserve the user's original source file. Never silently rewrite or overwrite the input novel, script, outline, idea, narration, or media file.
2. All structured field names must use `english_name 中文字段` in human-facing production documents. Python internal models may use stable English identifiers.
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

## Script mixer rules / 文案混剪规则

1. The user input is narration text. Convert text into timed semantic units and visual intents before searching media.
2. Do not search only by source filename or by the untouched full sentence. Use literal queries, metaphor queries, positive tags, negative constraints, emotion, shot type, and optional vector scores.
3. Original media is read-only. Never delete, rename, move, overwrite, or transcode in place.
4. Do not hard-code local software, model, media, cache, or drive paths in source code. Use runtime discovery and local ignored configuration.
5. FFmpeg, FFprobe, Ollama, Whisper, ComfyUI, embedding models, and vision models are optional adapters. Planning must remain testable without them.
6. A 30-second timeline should target at least 8 unique source videos, prohibit adjacent same-source clips, and report any relaxed constraint.
7. Low match scores, insufficient source diversity, missing media, watermark risk, or source-ratio violations must appear in `report.json` and must not be silently treated as final export quality.
8. Multiple-source mixing, low textual similarity, or short clips are not proof of copyright compliance. Preserve source traceability.

## Output priorities / 输出优先级

The human-readable production package should make these items easy to find:

1. `script.md` - readable episode script and story direction.
2. `assets.md` - complete character, scene, and prop generation prompts.
3. `storyboard.md` - shot order, composition, camera, blocking, movement, force/contact, and continuity.
4. `prompts.md` - generation-ready image/video prompts.
5. `qa.md` - blockers, warnings, repair actions, and export permission.
6. `exports/` - platform-ready prompts and tables.

The script mixer project should make these items easy to find:

1. `script_units.json` - timed narration units.
2. `visual_intents.json` - literal, metaphor, tag, emotion, and shot requirements.
3. `candidates.json` - candidate media and score reasons.
4. `timeline.json` - source timecodes and final timeline positions.
5. `report.json` - source diversity, match quality, warnings, and export state.
6. `render_plan.json` - exact local render command.

## Code changes / 代码修改

- Keep Python compatibility at 3.10 or newer.
- Do not add a runtime dependency unless the behavior cannot be implemented with the standard library.
- After changing Python or workflow contracts, run:

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v02 doctor
script-driven-mixer doctor
```

- A `BLOCKER` must prevent export.
- New tests must be deterministic and must not require network access, installed media software, real models, or private local files.
