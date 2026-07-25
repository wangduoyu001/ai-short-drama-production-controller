# AI 短剧导演系统升级规划

> 状态：规划文档，不代表已经实现  
> 仓库：`wangduoyu001/ai-short-drama-production-controller`  
> 分支：`main`  
> 适用范围：AI短剧 / AI漫剧导演生产系统  
> 不包含范围：LingJi 第二大脑、机会雷达、Obsidian 记忆、聊天记录采集、AnySearch 搜索层

## 0. 升级目标

当前项目已经具备 AI 短剧生产控制器的基础能力：

- 剧本输入
- 事件链解析
- 人物 / 场景 / 道具提取
- asset_lock 资产锁定
- beat_map 剧情节拍
- clip_plan 生成片段计划
- shot_plan 分镜计划
- QA Gate
- repair 定向返修
- export 导出
- Codex Skill 调用入口

下一阶段升级目标不是做一个“一键生成大片”的玄学按钮。

升级目标是：

```text
从 AI 短剧物料整理器
升级为
AI 导演生产系统
```

核心能力要从“整理提示词”升级为“管理生产链路”。

最终系统应该能做到：

```text
剧本
↓
Story Beat 剧情节拍
↓
Coverage Planner 镜头覆盖规划
↓
Shot Planner 分镜规划
↓
Asset Manager 资产锁定
↓
Continuity Memory 连续性记忆
↓
Workflow Planner 工作流规划
↓
Provider Router 模型调度
↓
QC Agent 质量检查
↓
Auto Repair 自动返修
↓
Timeline / Export 导出
```

一句话：

> 以后 Prompt 只是输出物，不是系统核心。

---

# 1. 升级原则

## 1.1 不推翻现有结构

当前 README 中已经确认的生产层级继续保留：

```text
episode 单集
  -> scene 场
    -> generation_clip 生成片段
      -> shot 镜头
```

升级必须基于现有结构扩展，不重新发明一套层级。

## 1.2 不把 LingJi 逻辑塞进导演系统

导演系统只负责短剧生产：

- 剧本
- 节拍
- 镜头
- 资产
- 分镜
- 视频生成计划
- QC
- 返修
- 导出

不负责：

- 个人第二大脑
- AI 聊天记录记忆
- Obsidian Vault
- 赚钱机会评分
- 每日简报归档
- AnySearch 搜索层
- MemoryGateway
- Qdrant 记忆索引

这些归 LingJi。别把两个仓库缝成一个赛博章鱼，维护起来会很像替章鱼穿裤子。

## 1.3 先结构化，再自动化，再画布化

升级顺序必须是：

```text
数据结构
↓
CLI / Skill 生产能力
↓
QA / Repair
↓
Provider / Workflow
↓
UI / 画布
```

不要先做炫酷画布。画布没有真实数据支撑，就是一个很有设计感的空壳。

## 1.4 所有能力必须可验收

每个升级点必须有：

- 输入
- 输出
- 文件落点
- QA 检查
- repair 行为
- export 行为
- 测试或自检命令

没有验收标准的功能先不做。

---

# 2. 版本路线图

## v0.6：导演数据结构升级

目标：让项目从 Prompt 整理升级为结构化导演数据。

重点模块：

- `shot.schema.json`
- `beat.schema.json`
- `asset.schema.json`
- `continuity.schema.json`
- `coverage.schema.json`
- `workflow.schema.json`

交付物：

```text
docs/schemas/
├── beat.schema.json
├── shot.schema.json
├── asset.schema.json
├── continuity.schema.json
├── coverage.schema.json
└── workflow.schema.json
```

验收标准：

- 每个 shot 必须能追溯到 source_quote / event_id / beat_id / clip_id。
- 每个 shot 必须绑定 scene_id、character_id、prop_id。
- 每个 shot 必须有 entry_pose、exit_pose、motion_path。
- 打斗 shot 必须包含 attack_line、defense_line、contact_point、force_direction、body_response、reset_position。
- QA 能检查缺失字段并阻断 export。

不做内容：

- 不接视频 API。
- 不做复杂 UI。
- 不做自动发布。

---

## v0.7：Coverage Planner 镜头覆盖规划

目标：让系统自动判断一个剧情节拍是否拍得完整。

新增模块：

```text
Coverage Planner
├── beat_id
├── required_shots
├── existing_shots
├── missing_shots
├── recommended_templates
├── priority
└── qc_result
```

第一批检查规则：

- 是否存在 Establishing Shot 环境交代镜头。
- 是否存在 Character Introduction 人物建立镜头。
- 是否存在 Reaction Shot 反应镜头。
- 是否存在 Detail Shot 细节镜头。
- 是否存在 Transition 转场镜头。
- 是否存在 Climax 高潮镜头。
- 是否存在 Ending Hook 结尾钩子。

对话场专项检查：

- 正打
- 反打
- 双人关系镜头
- 反应镜头
- 环境插入镜头

动作场专项检查：

- 预备姿态
- 出招
- 接触点
- 受力反馈
- 复位
- 结果镜头

交付物：

```text
project.yaml 中新增 coverage_plan
outputs/coverage_report.md
```

验收标准：

- 任意 beat 缺少关键镜头时，QA 给出 warning 或 blocker。
- 系统能推荐缺失镜头模板。
- repair 可以定向补一个 missing shot，而不是重做整场。

---

## v0.8：Continuity Memory 连续性记忆

目标：解决人物瞬移、道具消失、越轴、光线乱跳、服装变化等问题。

新增模块：

```text
Scene State
Shot Memory
Continuity Rules
```

Scene State 记录：

- 场景空间方向
- 人物位置
- 人物朝向
- 主光源方向
- 天气状态
- 关键道具状态
- 轴线方向
- 当前镜头运动方向

Shot Memory 记录：

- shot 起始状态
- shot 结束状态
- 人物 exit_pose
- 道具变化
- 镜头结束画面
- 下一个镜头接续要求

交付物：

```text
project.yaml 中新增 scene_state / shot_memory
outputs/continuity_report.md
```

验收标准：

- QA 能检查 screen_direction 是否冲突。
- QA 能检查人物位置是否突然变化。
- QA 能检查关键道具是否丢失。
- QA 能检查上一镜 exit_pose 与下一镜 entry_pose 是否冲突。

---

## v0.9：Workflow Library 工作流库

目标：把导演经验沉淀成可复用工作流，而不是堆 Prompt。

新增模块：

```text
Workflow Library
├── workflow_id
├── 适用类型
├── 推荐 Beat 模板
├── 推荐 Shot 模板
├── 推荐 Asset 要求
├── 推荐 Provider
├── QC 规则
├── Auto Repair 策略
└── version
```

第一批工作流：

- 武侠打斗工作流
- 古装对话工作流
- AI 漫剧开场工作流
- 爆点反转工作流
- 商品带货短视频工作流
- TikTok 广告工作流

交付物：

```text
workflows/
├── wuxia_fight.workflow.json
├── costume_dialogue.workflow.json
├── comic_opening.workflow.json
├── reversal_hook.workflow.json
├── product_short_video.workflow.json
└── tiktok_ad.workflow.json
```

验收标准：

- init 时可以选择 workflow。
- workflow 能影响 beat_map、clip_plan、shot_plan 的生成。
- QA 能基于 workflow 检查必需镜头。
- export 能标注使用的 workflow 版本。

---

## v1.0：Provider Router 模型调度层

目标：让 Kling、Seedance、Runway、ComfyUI 等底层模型可替换。

新增模块：

```text
Provider Router
├── provider_id
├── supported_input
├── supported_duration
├── aspect_ratio
├── cost_estimate
├── strengths
├── weaknesses
├── fallback_provider
└── last_verified
```

统一输入：

```text
shot_id
provider
duration
aspect_ratio
input_type
first_frame
tail_frame
prompt
negative_prompt
seed
locked_assets
```

统一输出：

```text
shot_id
provider
status
video_path
cost
generation_time
qc_status
error_message
```

交付物：

```text
providers/
├── base.py
├── comfyui.py
├── kling.py
├── seedance.py
├── runway.py
└── mock.py
```

验收标准：

- 先实现 mock provider，不直接接真实付费 API。
- 同一个 shot 可以切换 provider 生成请求。
- Provider 失败后可以走 fallback。
- 每个 provider 的调用结果进入 QA / Repair 流程。

---

## v1.1：QC Agent 与 Auto Repair 升级

目标：让系统能自动判断哪里错了，以及应该怎么修。

QC 检查项：

- 人脸漂移
- 服装变化
- 道具丢失
- 武器变形
- 场景错乱
- 人物站位错误
- 越轴
- 镜头运动错误
- 光线不连续
- 现代物件误入
- 缺少关键元素

Repair 策略：

```text
轻微问题 -> 局部编辑
中等问题 -> 保留首帧重新生成
严重问题 -> 重做该 shot
连续失败 -> 更换 provider
资产错误 -> 回到 asset_lock
分镜错误 -> 回到 shot_plan
```

新增锁定机制：

- Shot Lock
- Asset Lock
- Scene Lock

交付物：

```text
outputs/qa.md
outputs/repair_plan.md
outputs/repair_history.md
```

验收标准：

- export 前 QA 自动运行。
- 有 BLOCKER 时禁止 export。
- repair 可以只修一个 shot。
- repair 不允许生成 `final_v2`、`fixed`、`最新版` 这类重复文件。
- 单次定向返修只改变一个主要变量。

---

## v1.2：ComfyUI 后台执行层

目标：把 ComfyUI 定位成后台执行器，而不是让用户直接面对节点地狱。

新增模块：

```text
ComfyUI Executor
Workflow Planner
Workflow Validator
```

Workflow Planner 输入：

- shot schema
- asset ids
- provider constraints
- workflow type
- output target

Workflow Validator 检查：

- 节点是否存在
- 模型是否存在
- 输入路径是否存在
- 输出路径是否可写
- 资产引用是否完整
- workflow 是否符合当前 shot 类型

交付物：

```text
comfy/
├── planner.py
├── validator.py
├── executor.py
└── templates/
```

验收标准：

- 可以从 shot 生成 mock ComfyUI workflow。
- 可以验证 workflow 缺失字段。
- 不要求第一阶段真实跑云端 ComfyUI。

---

## v1.3：Director Agent 多 Agent 架构

目标：把一个巨大 Prompt 拆成多个小 Agent，各自负责明确任务。

Agent 划分：

```text
Director Agent 导演总控
├── Script Agent 剧本分析
├── Beat Agent 剧情节拍
├── Coverage Agent 镜头覆盖
├── Shot Agent 分镜规划
├── Asset Agent 资产匹配
├── Prompt Agent 提示词转换
├── Provider Agent 模型调度
├── QC Agent 质量检查
└── Repair Agent 自动返修
```

交付物：

```text
agents/
├── director.py
├── script_agent.py
├── beat_agent.py
├── coverage_agent.py
├── shot_agent.py
├── asset_agent.py
├── prompt_agent.py
├── provider_agent.py
├── qc_agent.py
└── repair_agent.py
```

验收标准：

- 每个 Agent 有明确输入输出。
- Agent 之间通过结构化 JSON 交接。
- 不允许 Agent 直接改其他阶段输出。
- Director Agent 只负责任务编排，不直接生成所有内容。

---

## v1.4：导演画布与手机审核

目标：把结构化生产链展示成可操作的导演工作台。

画布节点：

- 剧本节点
- 场景节点
- 角色资产节点
- 道具资产节点
- Beat 节点
- Shot 节点
- 首帧节点
- 尾帧节点
- 视频生成节点
- 音频节点
- QC 节点
- 返修节点
- 导出节点

手机端优先能力：

- 查看项目
- 查看分镜
- 查看 QA
- 标记问题
- 提交返修意见

手机端暂不优先：

- 复杂节点连线
- 大量参数编辑
- 复杂资产管理

验收标准：

- 手机能正常打开项目状态。
- 手机能查看 shot / QA / repair。
- 手机能提交返修意见。
- 桌面画布节点必须对应真实数据，不做假按钮。

---

# 3. 文件结构升级建议

建议逐步形成：

```text
ai-short-drama-production-controller/
├── docs/
│   ├── UPGRADE_PLAN.md
│   ├── FUTURE_DEVELOPMENT_TODO.md
│   └── schemas/
│       ├── beat.schema.json
│       ├── shot.schema.json
│       ├── asset.schema.json
│       ├── continuity.schema.json
│       ├── coverage.schema.json
│       └── workflow.schema.json
├── workflows/
│   ├── wuxia_fight.workflow.json
│   ├── costume_dialogue.workflow.json
│   ├── comic_opening.workflow.json
│   ├── reversal_hook.workflow.json
│   ├── product_short_video.workflow.json
│   └── tiktok_ad.workflow.json
├── providers/
│   ├── base.py
│   ├── mock.py
│   ├── comfyui.py
│   ├── kling.py
│   ├── seedance.py
│   └── runway.py
├── comfy/
│   ├── planner.py
│   ├── validator.py
│   ├── executor.py
│   └── templates/
├── agents/
│   ├── director.py
│   ├── script_agent.py
│   ├── beat_agent.py
│   ├── coverage_agent.py
│   ├── shot_agent.py
│   ├── asset_agent.py
│   ├── prompt_agent.py
│   ├── provider_agent.py
│   ├── qc_agent.py
│   └── repair_agent.py
└── short_drama_controller/
```

---

# 4. 第一阶段 Codex 执行建议

第一阶段只做文档和 schema，不碰外部 API。

建议 Codex 任务：

```text
任务：执行 AI 短剧导演系统 v0.6 升级

仓库：wangduoyu001/ai-short-drama-production-controller

要求：
1. 不接入任何真实视频 API。
2. 不修改现有 CLI 行为，除非测试需要。
3. 新增 docs/schemas/ 目录。
4. 新增以下 schema 草案：
   - beat.schema.json
   - shot.schema.json
   - asset.schema.json
   - continuity.schema.json
   - coverage.schema.json
   - workflow.schema.json
5. schema 必须覆盖 README 中现有字段：
   - source_quote
   - event_id
   - beat_id
   - clip_id
   - scene_id
   - character_id
   - prop_id
   - entry_pose
   - exit_pose
   - motion_path
   - attack_line
   - defense_line
   - contact_point
   - force_direction
   - body_response
   - reset_position
   - fallback_shot
6. 更新 doctor 或新增 schema 自检命令，验证 schema 文件存在。
7. 更新 README 的“主流程结构”部分，引用 docs/UPGRADE_PLAN.md 和 docs/FUTURE_DEVELOPMENT_TODO.md。
8. 保持 QA Gate 和 repair 规则不退化。
9. 完成后运行现有 doctor 命令。
```

---

# 5. 风险控制

## 5.1 最大风险：系统膨胀

不要一次性实现：

- Provider Router
- ComfyUI
- Director Agent
- 画布
- 手机端
- 自动发布

这会直接把项目变成“每个方向都开了头，每个方向都不能用”。人类软件工程的保留节目，难看但常见。

## 5.2 最大原则：先让数据结构稳定

推荐顺序：

```text
schema
↓
QA
↓
repair
↓
workflow
↓
provider
↓
agent
↓
ui
```

## 5.3 不要过早接真实付费 API

真实 API 接入前必须先有：

- mock provider
- 成本记录
- fallback
- QA 阻断
- repair 记录
- 手动确认

否则花钱生成一堆不可控垃圾，听起来像创业，其实像给平台交保护费。

---

# 6. 当前优先级结论

当前最该做的是 v0.6 和 v0.7：

1. `shot.schema.json`
2. `beat.schema.json`
3. `asset.schema.json`
4. `continuity.schema.json`
5. `coverage.schema.json`
6. Coverage Planner
7. QA 字段检查
8. README 文档引用

暂缓：

- 真实 Kling / Runway / Seedance API
- 复杂导演画布
- 自动发布
- 商业用户系统
- 大规模多 Agent

---

# 7. 最终判断

本仓库下一阶段的正确升级路线是：

```text
物料包生成器
↓
结构化导演系统
↓
工作流驱动生产器
↓
Provider 可替换的视频调度层
↓
QC + Auto Repair 生产闭环
↓
导演画布与手机审核
```

只要这个路线保持住，Kling、Runway、Seedance、ComfyUI 都只是底层执行器。

真正的壁垒在：

- 剧情节拍
- 镜头规划
- 资产一致性
- 连续性记忆
- QA Gate
- 定向返修
- 工作流复用

也就是导演系统本身，而不是某个今天很火、明天又被另一个模型盖过去的视频生成平台。
