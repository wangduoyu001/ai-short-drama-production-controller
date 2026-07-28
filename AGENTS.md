# Repository instructions / 仓库执行规则

## Mission / 目标

本仓库交付可执行的 AI 短剧导演物料、节点化生产任务图和可恢复的生产状态。只有真实 Provider、媒体 QA、人工审核和合成全部通过后，才能声称生成最终成片。

## Working rules / 工作规则

1. Preserve the user's original source file. Never silently rewrite or overwrite the input novel, script, outline, or idea.
2. All structured field names must use `english_name 中文字段` where existing project contracts require bilingual fields.
3. Treat one episode and one generation clip as different levels:
   - `episode 单集`: normally 2-3 minutes unless specified otherwise.
   - `generation_clip 生成片段`: 4-15 seconds, normally 10-15 seconds.
4. Build in this order:
   `source -> story_graph -> script -> asset_lock -> beat_map -> shot_plan -> production_tasks -> review -> assembly -> qa -> export`.
5. The repository has one public version and one command: `short-drama-controller`.
6. Workflow stages must remain independently replaceable, resumable and testable.
7. Never create decorative or duplicate files such as `final_v2`, `fixed`, `new` or `最新版`.
8. Asset consistency outranks visual novelty. Lock face, age, body proportion, hairstyle, costume, prop shape, scene layout and spatial anchors before shot planning.
9. Every shot must retain source evidence and bind to event, beat, scene, character, prop, clip, start state and end state.
10. Action shots must define movement path, attack/contact line, force/result, screen direction, camera side, end pose and fallback shot.
11. Keep the camera on the same side of the axis unless a neutral shot or explicit axis-crossing transition exists.
12. `planned` means task manifests exist. It does not mean media was generated.
13. Paid APIs, GPU startup, model downloads, publishing and destructive actions remain disabled by default.
14. Resume must reject changed source text unless a new workflow state is deliberately created.
15. Failed final assembly must produce a blocker. Never substitute the first clip as a completed episode.
16. All model and media integrations must pass through the Provider registry.
17. Directly copied or substantially adapted permissive source must preserve required attribution and license notices.
18. Do not copy code whose license conflicts with the repository's intended use or required branding policy.
19. Network tests must use injected fake senders and must not contact real services.
20. Local manager sync may only target loopback HTTP hosts and the documented plan-import endpoint.

## Output priorities / 输出优先级

1. `script.md`
2. `assets.md`
3. `storyboard.md`
4. `prompts.md`
5. `workflow.json`
6. `production_tasks.json`
7. `assembly_plan.json`
8. `manager_import.json`
9. `qa.md`
10. `exports/`

## Code changes / 代码修改

- Keep Python compatibility at 3.10 or newer.
- Avoid runtime dependencies unless standard-library implementation is impractical.
- New task or workflow states must be deterministic JSON and safe for resume.
- Workflow contracts and Python stage definitions must stay synchronized.
- A `BLOCKER` must prevent export or final-media completion.
- New tests must be deterministic and offline.

After changing code or contracts, run:

```bash
pytest -q
short-drama-controller doctor
short-drama-controller graph-template
```
