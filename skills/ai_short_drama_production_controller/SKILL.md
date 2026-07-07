# AI短剧生产控制器 Skill / Codex Agent 专用协议

## 0. 定位

本仓库是 `Codex Skill / Codex技能`，不是普通 Python 生成器。

- Codex / WorkBuddy 负责导演分析、内容判断、改写和返修决策。
- Python 负责结构化、QA / 质检、repair / 返修、export / 导出。
- 不接入外部 LLM API，不新增 OpenAI / Claude / Ollama 调用。
- 禁止把 Python 模板输出当最终导演内容。

## 1. 唯一主流程

使用 v0.3 beat_map / 剧情节拍驱动流程。v0.1 / v0.2 只保留兼容，不作为主流程。

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
```

单条提示词模式：

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

返修必须覆盖旧文件，不准另存副本。人类已经发明了够多垃圾文档，不需要本项目再添砖加瓦。

## 3. Codex 必须先生成的结构

Codex 处理用户剧本时，必须先确认并生成这些结构，再允许导出：

```text
source_text 原文
beat_map 剧情节拍表
director_read 导演读本
assets 资产锁定
shots 分镜列表
sound_plan 声音设计计划
producer_plan 制片执行计划
qa_report 质检返修文档
```

每个 beat / 节拍 必须包含：

```text
beat_id 节拍编号
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

每个 shot / 镜头 必须绑定：

```text
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

## 4. 硬规则 hard_rules

1. 必须保留完整 `source_text 原文`。
2. 不得把总结当原文。
3. 不得输出模板占位符：`情绪或动作推进`、`运动或情绪起点明确`、`运动结果或情绪落点明确`、`建立空间和轴线`、`手部或道具特写`。
4. `make_shot / 生成镜头` 必须从 `beat_map / 剧情节拍表` 读取内容。
5. `build_sketch / 生成简笔图` 必须从真实 shot 字段读取内容。
6. `image_prompt / 图片提示词` 只能写画面元素，不得写导演意图、潜台词、权力变化、观众感受。
7. storyboard 有人物时，image_prompt 禁止写“无人物 / empty scene / no character”。
8. 每个对白镜头必须明确谁开口、谁闭口、嘴型状态、空间锚点。
9. OS / 画外音 镜头必须全员闭口。
10. 多人物镜头必须明确主次关系，最多同时调度 3 个核心人物；超过 3 个要拆镜头。
11. 多场景项目必须给每个 beat 和 shot 绑定 scene_id，禁止所有镜头默认塞进第一个场景。
12. 高风险动作、道具接触、多人物静默交互必须启用 grid_prompt / 宫格提示词。
13. QA 出 BLOCKER 时，禁止 export / 导出。
14. repair 必须真实修改问题字段，不得只重写 qa.md。
15. targeted repair / 定向返修 必须支持只修某个 shot，不得无故重写全项目。

## 5. 常见失败模式与防御

### failure_01 模板填表

症状：action_detail 写“情绪或动作推进”。

防御：标记 BLOCKER，回到 beat_map，用 source_quote 重写 visible_action。

### failure_02 景别重复

症状：连续 3 个同类景别。

防御：repair 必须重排景别，且重新生成 sketch_ascii。

### failure_03 提示词与分镜矛盾

症状：shot 有人物，image_prompt 写无人物。

防御：标记 BLOCKER，按 on_screen_characters 重写 image_prompt。

### failure_04 图片提示词抽象污染

症状：image_prompt 写“让观众感觉、潜台词、权力变化”。

防御：移到 director_read 或 video_prompt，image_prompt 只保留画面。

### failure_05 对白密度过低

症状：60-90秒只有 1-2 句对白且无动作信息。

防御：给 WARN，压缩时长或增加 OS / 动作节拍，不许水镜头。

### failure_06 多人物混乱

症状：角色超过 3 个仍挤在同一镜头。

防御：拆成 master_shot / 主镜头、reaction_shot / 反应镜头、insert_shot / 插入镜头。

### failure_07 多场景错绑

症状：原文换场景，但所有 shot 都绑定同一 scene_id。

防御：每个 beat 提取 scene_hint；每个 shot 必须绑定 scene_id。

### failure_08 repair 空转

症状：repair 后 QA 问题一模一样。

防御：repair 后重新 QA；如果同 code 未减少，输出 BLOCKER 并说明具体字段未改。

## 6. Agent 执行循环

Codex / WorkBuddy 必须按这个循环执行：

```text
read source_text 原文
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

## 7. targeted repair / 定向返修协议

当用户说“只修 SH003”或 QA 指向单镜头时，优先执行定向返修：

```bash
python -m short_drama_controller.v02_full_cli repair --project demo_v02 --shot SH003
```

定向返修只允许修改：

```text
指定 shot
该 shot 对应 beat
受该 shot 影响的 storyboard_grid / 导出表 / qa
```

不得重写全部角色、全部场景、全部剧本。

## 8. 多场景多人物规则

- scene / 场景 数量 > 1 时，每个 beat 必须有 scene_hint。
- shot.scene_id 必须来自 beat.scene_hint 或原文证据。
- character / 角色 数量 > 2 时，每个 beat 必须列出相关角色。
- 每个 shot 最多同时调度 3 个核心人物。
- 第 4 个及以上人物只能作为 crowd / 群像 或拆到下一镜。
- 正反打只服务两人冲突；三人以上必须先 master_shot 建立空间。

## 9. Codex 输出风格

- 中文为主。
- 英文专业词必须带中文解释。
- 少解释，多执行。
- 不写无用总结文档。
- 不要把“建议”当交付物。
- 输出内容必须能直接用于导演、抽卡师、后期、视频生成平台。
