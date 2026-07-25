# Repository instructions / 仓库执行规则

## Mission / 目标

This repository produces a director-ready material package and an owned, resumable production task graph for AI short drama and AI comic-drama production.

本仓库交付可执行的导演物料包与自有生产任务图。只有真实 Provider、媒体 QA 和合成全部通过后，才能声称生成了最终成片。

## Working rules / 工作规则

1. Preserve the user's original source file. Never silently rewrite or overwrite the input novel, script, outline, or idea.
2. All structured field names must use `english_name 中文字段`.
3. Treat one episode and one generation clip as different levels:
   - `episode 单集`: normally 2-3 minutes unless the user specifies otherwise.
   - `generation_clip 生成片段`: 4-15 seconds, normally 10-15 seconds.
4. Build in this order:
   `chapter_intake -> story_events -> world_bible/style_bible -> asset_lock -> beat_map -> clip_plan -> shot_plan -> prompts -> production_tasks -> assembly_plan -> qa -> export`.
5. The top-level `novel-to-drama.v1` workflow is a single user entrypoint, but implementation stages must remain independently replaceable and resumable.
6. Never create decorative or duplicate Markdown files. Repair must overwrite the existing target file. Do not create names such as `final_v2`, `fixed`, `new`, or `最新版`.
7. Use only the documented project files and `exports/` outputs. Do not add a new document unless it has a distinct production purpose and is added to the README contract.
8. Asset consistency outranks visual novelty. Lock face, age, body proportion, hairstyle, costume material, costume color, prop shape, scene layout, and spatial anchors before shot planning.
9. Every shot must retain source evidence and bind to event, beat, scene, character, prop, clip, start state, and end state.
10. Every action or fight shot must define start pose, movement path, attack line, contact point, force/result, screen direction, camera side, end pose, and fallback shot.
11. Keep the camera on the same side of the axis unless a neutral shot or explicit axis-crossing transition is planned.
12. Ask at most one consolidated clarification when a missing parameter blocks production. Otherwise use explicit defaults and record them as assumptions.
13. Do not claim that this repository directly calls Seedance, Kling, Jimeng, Veo, Sora, ComfyUI, TTS, or another external service unless an actual integration exists and its tests pass.
14. `planned` means task manifests exist. It does not mean images, video, audio, or final media were generated.
15. Paid APIs, GPU startup, model downloads, public publishing, and destructive actions must remain disabled by default and require explicit confirmation.
16. Resume must reject changed source text unless the user deliberately starts a new workflow state.
17. Completed external tasks may be skipped; failed tasks may retry up to their declared maximum. Never silently replace a failed final assembly with the first clip.
18. Directly copied or substantially adapted permissive source must preserve attribution and license notices in `THIRD_PARTY_NOTICES.md`.
19. Do not copy AGPL, source-available, closed-source, or commercially restricted core code into this repository without an explicit compatible licensing decision.
20. Comfy Cloud Manager sync may only target loopback HTTP hosts and only the production-plan import endpoint.
21. Manager sync must not send API keys, tokens, execution flags, remote URLs, provider task IDs, generated media, or the original source novel.
22. Save `manager_import.json` only after the manager proves `dry_run_only=true` and all execution flags are false.

## Output priorities / 输出优先级

The human-readable production package should make these items easy to find:

1. `script.md` - readable episode script and story direction.
2. `assets.md` - complete character, scene, and prop generation prompts.
3. `storyboard.md` - shot order, composition, camera, blocking, movement, force/contact, and continuity.
4. `prompts.md` - generation-ready image/video prompts.
5. `workflow.json` - top-level stage state, source hash, attempts, blockers, and evidence.
6. `production_tasks.json` - render/audio/assembly task dependency graph and variant selection state.
7. `assembly_plan.json` - deterministic final assembly contract.
8. `manager_import.json` - optional local manager dry-run import receipt.
9. `qa.md` - blockers, warnings, repair actions, and export permission.
10. `exports/` - platform-ready prompts and tables.

## Code changes / 代码修改

- Keep Python compatibility at 3.10 or newer.
- Do not add a runtime dependency unless the behavior cannot be implemented with the standard library.
- New task or workflow states must be deterministic JSON and safe for resume.
- Workflow contracts and Python stage definitions must stay synchronized.
- Network tests must use injected fake senders; tests must not contact a real local or remote service.
- After changing Python or workflow contracts, run:

```bash
pytest -q
python scripts/v02_smoke.py
short-drama-controller-v06 doctor
```

- A `BLOCKER` must prevent export or final-media completion.
- New tests must be deterministic and must not require network access.
