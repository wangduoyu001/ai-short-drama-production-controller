# 文案驱动本地混剪：时间线审核与返修

## 目标

自动粗剪完成后，允许人工只修改不合适的镜头，不重新生成整条时间线，也不改变已确认镜头。

项目新增：

```text
review.json
revision_log.json
rollback_log.json
revisions/
```

时间线片段新增字段：

```text
clip_id
locked
review_status
replacement_reason
candidate_rank
```

## 生成审核清单

```bash
script-driven-mixer --config script_mixer.local.json review-project \
  --project <项目ID或项目目录>
```

输出 `review.json`，包含：

- 每个片段的时间位置。
- 当前镜头ID和来源。
- 源入点与出点。
- 素材文件是否存在。
- 是否超过源视频40秒窗口。
- 匹配分数。
- 原候选排名。
- 可用候选数量。
- 锁定状态。
- 审核状态。
- 替换原因。
- 原视频音轨状态。

同时重新生成 `report.json`，避免返修后继续沿用旧报告。

## 锁定镜头

```bash
script-driven-mixer --config script_mixer.local.json lock-segment \
  --project <项目> \
  --segment S002
```

锁定后：

- `locked=true`
- `review_status=approved`
- 单镜头替换会被拒绝
- `replan-project` 必须原位保留该镜头

解除锁定：

```bash
script-driven-mixer --config script_mixer.local.json unlock-segment \
  --project <项目> \
  --segment S002
```

## 单镜头替换

基础替换：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --reason "画面与文案不匹配"
```

按关键词筛选：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --keyword "手机 创作" \
  --reason "需要手机创作画面"
```

指定景别：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --shot-type "特写"
```

要求有原视频音轨：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --require-audio
```

要求无音轨：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --require-silent
```

排除来源或镜头：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --exclude-source SRC_001 \
  --exclude-source SRC_002 \
  --exclude-clip CLP_001
```

选择筛选后的第二个候选：

```bash
script-driven-mixer --config script_mixer.local.json replace-segment \
  --project <项目> \
  --segment S002 \
  --candidate-rank 2
```

替换时自动约束：

- 不选择当前镜头。
- 不重复使用时间线中已有镜头。
- 不选择与前后相邻镜头相同的来源。
- 不选择本机不存在的素材。
- 不选择太短、无法合理适配目标时长的镜头。
- 不选择40秒窗口外的镜头。
- 不改变时间线入点、出点和片段总时长。

`--allow-missing-media` 只用于迁移排查，不适合实际渲染。

## 保留锁定镜头重新规划

```bash
script-driven-mixer --config script_mixer.local.json replan-project \
  --project <项目>
```

重新规划读取原项目已有的：

```text
script_units.json
visual_intents.json
candidates.json
```

它不会重新拆分文案，也不会改变配音时间轴。

执行规则：

- 锁定片段原位保留。
- 未锁定片段重新选择候选。
- 已锁定来源会参与后续多来源约束。
- 锁定片段前的镜头尽量避免与其来源相同。
- 重新规划后重新生成审核和QA报告。
- 时间结构变化导致锁定片段无法对齐时直接失败，不偷偷移动锁定镜头。

## 回退

```bash
script-driven-mixer --config script_mixer.local.json rollback-project \
  --project <项目>
```

可回退最近一次：

- 锁定。
- 解锁。
- 单镜头替换。
- 项目重新规划。

每次修改前，当前 `timeline.json` 会写入 `revisions/`。回退记录写入 `rollback_log.json`。

## 重渲染

```bash
script-driven-mixer --config script_mixer.local.json rerender-project \
  --project <项目> \
  --burn-subtitles
```

只生成FFmpeg命令：

```bash
script-driven-mixer --config script_mixer.local.json rerender-project \
  --project <项目> \
  --burn-subtitles \
  --dry-run
```

当前重渲染会覆盖：

```text
exports/final.mp4
```

不会创建 `final_v2`、`fixed` 或 `最新版`。

当前仍是整条视频重渲染。下一阶段将加入片段缓存，使未变化镜头可以复用，只重新处理发生变化的片段，再重新组装音频、字幕和最终视频。

## QA

返修后 `report.json` 重新检查：

- 唯一来源数量。
- 单来源时长和占比。
- 相邻同源。
- 低匹配镜头。
- 丢失素材。
- 40秒窗口越界。
- 原声音轨覆盖率。
- 配音状态。
- 字幕是否需要人工复核。
- 锁定、未审核和已替换数量。

存在阻塞项时：

```text
allow_final_export=false
```

仍可以用于人工预览和继续返修，但不能被视为正式可交付版本。
