# AI短剧生产控制器 Skill / Codex Agent 专用协议

## 0. 定位

本仓库是 `Codex Skill / Codex技能`，不是普通 Python 生成器。

- Codex / WorkBuddy 负责导演分析、内容判断、改写和返修决策。
- Python 负责结构化、QA / 质检、repair / 返修、export / 导出。
- 不接入外部 LLM API。
- 禁止把 Python 模板输出当最终导演内容。

## 0.1 参考提示词边界

用户提供的提示词合集只用于学习结构，不是默认模板。

- 不得压缩用户原始提示词。
- 不得把参考合集里的来源名称、栏目名、样例题材写成项目名称或默认方向。
- 不得把参考样例的人物、场景、道具直接套到新项目。
- 只能学习写法结构：主体、身份、外貌、服装、材质、场景、道具、动作、构图、景别、机位、光线、色卡、连续性锁定、负面提示词、备用镜头。
- 生成新提示词时，必须根据当前项目原文、角色、场景、道具重新生成。
- 生图提示词、生视频提示词、三视图提示词、负面提示词、备用镜头必须分开。
- 禁止把高密度参考提示词压成“电影写实、低饱和、固定服装”这类泛化描述。

## 1. 唯一主流程

使用 v0.3.1 `clip_first / 片段优先` 流程。v0.1 / v0.2 / 旧 v0.3 只保留兼容，不作为主流程。

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
```

定向返修：

```bash
python -m short_drama_controller.v02_full_cli repair --project demo_v02 --shot SH003
```

单条提示词：

```bash
python -m short_drama_controller.v02_full_cli prompt --text "夜色中的破庙里，少年握着断刀，背对门口。他低声说：你终于来了。"
```

## 2. 固定交付物白名单

只允许生成：

```text
project.yaml
script.md
assets.md
storyboard.md
producer.md
sound.md
prompts.md
qa.md
exports/video_prompts.md
exports/grid_prompts.md
exports/shot_table.csv
exports/sound_table.csv
exports/producer_table.csv
```

禁止生成：

```text
final / 最终版 / v2 / fixed / new / report / summary / 优化建议 / 修复记录
```

返修必须覆盖旧文件，不准另存副本。

## 3. v0.3.1 核心结构

Codex 处理用户剧本时，必须先确认并生成：

```text
source_text 原文
clip_plan 片段计划
beat_map 剧情节拍表
director_read 导演读本
assets 资产锁定
shots 分镜列表
sound_plan 声音设计计划
producer_plan 制片执行计划
qa_report 质检返修文档
```

每个 `clip / 片段` 必须包含：

```text
clip_id 片段编号
clip_type 片段类型
duration_seconds 时长秒数
model_duration_limit 模型时长限制
scene_hint 场景建议
characters 相关角色
beat_range 节拍范围
shot_density 镜头密度
shot_count_target 目标镜头数
```

每个 `beat / 节拍` 必须包含：

```text
beat_id 节拍编号
clip_id 片段编号
clip_type 片段类型
clip_duration_seconds 片段时长秒数
source_quote 原文证据
visible_action 可见动作
dialogue 对白
conflict 冲突
emotion_shift 情绪变化
power_shift 权力变化
subtext 潜台词
shot_hint 镜头建议
scene_hint 场景建议
characters 相关角色
```

每个 `shot / 镜头` 必须绑定：

```text
clip_id 单段编号
clip_type 片段类型
clip_duration_seconds 片段时长秒数
beat_id 节拍编号
source_quote 原文节拍证据
scene_id 场景编号
on_screen_characters 在场人物
action_detail 动作细节
shot_size 景别
camera_movement 机位运动
screen_direction 画面方向
movement_arrow 运动箭头
camera_arrow 镜头箭头
sketch_ascii 简笔手绘图
```

## 4. clip-first / 片段优先规则

- 视频生成模型按 `generation_clip / 生成片段` 组织，不按 60-90 秒长段直接生成。
- 每个 generation_clip / 生成片段时长必须在 4-15 秒内。
- 单集 episode / 单集 可以有多个 clip / 片段。
- 全片场景数量由原文决定，不设 1 场景死限制。
- 全局人物数量由原文决定，不设 2-3 人死限制。
- 单个 shot / 镜头 最多调度 3 个核心人物；更多人物拆镜或作为 crowd / 群像。

镜头密度：

```text
dialogue_clip 对白片段：3-6镜 / 10-15秒
action_clip 动作片段：6-12镜 / 10-15秒
fight_clip 打戏片段：10-24镜 / 10-15秒
transition_clip 转场片段：1-4镜 / 4-8秒
emotion_clip 情绪片段：2-5镜 / 8-12秒
establishing_clip 建立空间片段：1-4镜 / 4-8秒
```

## 5. 硬规则 hard_rules

1. 必须保留完整 `source_text 原文`。
2. 不得把总结当原文。
3. 不得输出模板占位符：`情绪或动作推进`、`运动或情绪起点明确`、`运动结果或情绪落点明确`、`建立空间和轴线`、`手部或道具特写`。
4. `make_shot / 生成镜头` 必须从 `beat_map / 剧情节拍表` 和 `clip_plan / 片段计划` 读取内容。
5. `build_sketch / 生成简笔图` 必须从真实 shot 字段读取内容。
6. `image_prompt / 图片提示词` 只能写画面元素，不得写导演意图、潜台词、权力变化、观众感受。
7. storyboard 有人物时，image_prompt 禁止写“无人物 / empty scene / no character”。
8. 每个对白镜头必须明确谁开口、谁闭口、嘴型状态、空间锚点。
9. OS / 画外音 镜头必须全员闭口。
10. 高风险动作、道具接触、多人物静默交互、fight_clip / 打戏片段 必须启用 grid_prompt / 宫格提示词 或 motion_grid_ascii / 动作拆解六宫格。
11. QA 出 BLOCKER 时，禁止 export / 导出。
12. repair 必须真实修改问题字段，不得只重写 qa.md。
13. targeted repair / 定向返修 必须支持只修某个 shot，不得无故重写全项目。

## 6. 常见失败模式与防御

### failure_01 模板填表

症状：action_detail 写“情绪或动作推进”。

防御：标记 BLOCKER，回到 beat_map，用 source_quote 重写 visible_action。

### failure_02 旧长片规划

症状：仍按 60-90秒、8-12镜、1场景、2-3人写死。

防御：标记 BLOCKER，重建 clip_plan，按 4-15秒 generation_clip 组织。

### failure_03 打戏密度过低

症状：15秒打戏只有 3-6 个镜头。

防御：按 fight_clip 打戏片段 扩展到 10-24 镜，并启用 motion_grid_ascii 动作拆解六宫格。

### failure_04 提示词与分镜矛盾

症状：shot 有人物，image_prompt 写无人物。

防御：标记 BLOCKER，按 on_screen_characters 重写 image_prompt。

### failure_05 多人物混乱

症状：角色超过 3 个仍挤在同一镜头。

防御：拆成 master_shot 主镜头、reaction_shot 反应镜头、insert_shot 插入镜头。

### failure_06 多场景错绑

症状：原文换场景，但所有 shot 都绑定同一 scene_id。

防御：每个 beat 提取 scene_hint；每个 shot 必须绑定 scene_id。

### failure_07 repair 空转

症状：repair 后 QA 问题一模一样。

防御：repair 后重新 QA；如果同 code 未减少，输出 BLOCKER 并说明具体字段未改。

## 7. Agent 执行循环

```text
read source_text 原文
↓
build clip_plan 片段计划
↓
build beat_map 剧情节拍表
↓
build director_read 导演读本
↓
build shots 分镜列表
↓
run qa 质检
↓
repair targeted 定向返修 或 repair full 全量返修
↓
run qa again 再次质检
↓
export 导出
```

不得跳过 QA。
不得在 BLOCKER 未解决时导出。
不得生成白名单外 md。

## 8. Codex 输出风格

- 中文为主。
- 英文专业词必须带中文解释。
- 少解释，多执行。
- 不写无用总结文档。
- 不要把“建议”当交付物。
- 输出内容必须能直接用于导演、抽卡师、后期、视频生成平台。
