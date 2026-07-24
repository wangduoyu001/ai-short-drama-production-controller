# AI 短剧导演系统未来开发待办事项

> 状态：规划待办，不代表已经实现  
> 仓库：`wangduoyu001/ai-short-drama-production-controller`  
> 分支：`main`  
> 边界：本文只记录 AI 短剧 / AI 漫剧导演系统相关任务，不记录 LingJi 的第二大脑、机会雷达、聊天记忆、Obsidian 记忆库等内部任务。

## 0. 本文用途

本文用于沉淀 AI 短剧导演系统后续开发任务，重点覆盖：

- 剧本到剧情节拍
- 剧情节拍到镜头
- 角色 / 场景 / 道具资产锁定
- 分镜结构化
- 生成片段规划
- 镜头连续性
- 视频模型调度
- ComfyUI 执行层
- QC 质检
- 自动返修
- Codex Skill 生产契约
- 可视化导演画布

本文不写 LingJi 的内部开发任务，例如统一第二大脑、Obsidian 记忆、聊天记录采集、赚钱机会评分、AnySearch 默认搜索层、MemoryGateway、Qdrant 记忆索引等。那些内容必须放到 `wangduoyu001/lingji`。

---

# 1. P0：导演系统核心生产链

## 1.1 明确生产层级

- [ ] 保持当前核心层级：`episode -> scene -> generation_clip -> shot`。
- [ ] 明确 4-15 秒限制作用于 `generation_clip`，不是整集。
- [ ] 所有分镜必须基于：`story_events -> beat_map -> clip_plan -> shot_plan`。
- [ ] 每个 shot 必须绑定 source_quote、event_id、beat_id、clip_id、scene_id、character_id、prop_id、entry_pose、exit_pose、motion_path。
- [ ] 打斗镜头必须额外绑定 attack_line、defense_line、contact_point、force_direction、body_response、reset_position、fallback_shot。

## 1.2 从 Prompt 驱动升级为结构化驱动

- [ ] 不再把 Prompt 当核心资产。
- [ ] Prompt 只作为 Shot / Workflow 的最终输出物。
- [ ] 系统核心资产升级为：Story Beat、Shot Schema、Asset ID、Continuity Memory、Workflow Library、QC Rules。
- [ ] 所有生成提示词必须能从结构化数据重新生成。

---

# 2. P0：Story Beat 剧情节拍模块

## 2.1 Story Beat 数据结构

- [ ] 新增或完善 `beat_map` 数据结构。
- [ ] 每个 beat 记录剧情目的、人物状态变化、情绪变化、冲突点、推荐镜头数量、是否动作戏、是否特效、是否对白。
- [ ] 每个 beat 必须能追溯到 source_quote / story_event。
- [ ] 每个 beat 必须能生成一组 coverage shots。

## 2.2 Beat Library 剧情节拍库

- [ ] 建立 `Beat Library`。
- [ ] 第一批模板包括：初次登场、冲突建立、对峙、战斗开始、战斗高潮、战斗结束、真相揭露、情绪反转、高潮结尾、下一集钩子。
- [ ] 每个 Beat 模板记录推荐镜头数量、推荐景别、推荐运镜、推荐音效、推荐 QC 项。
- [ ] Beat Library 用于帮助导演 Agent 复用导演经验，而不是每次从零开始。

---

# 3. P0：Shot Schema 镜头结构

## 3.1 Shot 必填字段

- [ ] 标准化 `shot.schema.json`。
- [ ] 每个 shot 必须包含：shot_id、scene_id、beat_id、clip_id、duration、shot_type、lens、camera_angle、camera_movement、blocking、dialogue、sound、assets、continuity、qc_rules。
- [ ] 每个 shot 必须记录首帧建议和尾帧建议。
- [ ] 每个 shot 必须记录入场姿态和结束姿态。
- [ ] 每个 shot 必须记录屏幕运动方向，避免越轴和空间错乱。

## 3.2 镜头覆盖率检查

- [ ] 对每个 beat 自动检查是否缺少 establishing、action、reaction、detail、cutaway、transition。
- [ ] 对对话场自动检查是否有正反打、反应镜头、环境交代镜头。
- [ ] 对动作场自动检查是否有攻击前准备、出招、接触、受力、复位、结果镜头。
- [ ] 缺少关键覆盖镜头时标记为 QA Warning 或 Blocker。

---

# 4. P0：资产锁定系统

## 4.1 Asset ID 规则

- [ ] 统一资产 ID：CHAR_、SCENE_、PROP_、VOICE_、MUSIC_、SFX_、VFX_、SHOT_、WORKFLOW_。
- [ ] 资产命名规则采用：`类型_名称_版本`。
- [ ] 支持 LOCKED 标记，锁定后生成阶段不得随意改变。
- [ ] 每个资产必须保存正面 / 侧面 / 背面 / 表情 / 服装 / 材质 / 负面约束。

## 4.2 人物资产

- [ ] 角色资产必须包含脸部参考、三视图、服装、年龄、体型、发型、常用表情、禁改项。
- [ ] 支持多人同场时的区分特征。
- [ ] 重要人物需要大头贴 + 三视图 + 细节色卡。
- [ ] 人物资产必须能跨场景复用。

## 4.3 场景资产

- [ ] 场景资产必须记录空间方向、出入口、主视觉区域、光线、天气、时代元素、禁用现代元素。
- [ ] 重要场景保存主图、俯视图、角色站位图、关键道具位置。
- [ ] 场景必须支持连续镜头复用。

## 4.4 道具资产

- [ ] 道具资产必须记录外观、材质、尺寸、持有者、状态变化。
- [ ] 武器类道具必须记录攻击线、防守线、受力方向、是否可变形。
- [ ] 关键道具必须加入 QC 检查。

---

# 5. P0：Continuity Memory 连续性记忆

## 5.1 场景状态

- [ ] 新增 `Scene State`。
- [ ] 记录人物位置、朝向、光线、天气、道具状态、空间方向、镜头轴线。
- [ ] 每个镜头结束后更新 scene state。
- [ ] 下一镜头生成前读取 scene state。

## 5.2 Shot Memory 镜头记忆

- [ ] 每个 shot 自动保存景别、焦段、机位、人物状态、道具状态、结尾动作。
- [ ] 下一 shot 自动读取上一 shot 的 exit_pose 和 movement_direction。
- [ ] 支持动作承接，避免人物瞬移、方向错乱、道具消失。

## 5.3 越轴与空间检查

- [ ] 增加 screen_direction 检查。
- [ ] 增加人物相对位置检查。
- [ ] 增加场景方向检查。
- [ ] 对战争、打斗、对话场强制启用连续性检查。

---

# 6. P1：Workflow Library 工作流库

## 6.1 工作流模板

- [ ] 建立 `workflow_library.json`。
- [ ] 第一批工作流包括：武侠打斗、古装对话、漫剧开场、爆点反转、商品带货短视频、TikTok 广告。
- [ ] 每个 workflow 记录适用类型、推荐 beat、推荐 shot、推荐资产、推荐模型、QC 规则、返修策略。
- [ ] Workflow 负责组织生产流程，Prompt 只是末端输出。

## 6.2 Workflow 版本管理

- [ ] 每个 workflow 必须有版本号。
- [ ] 修改 workflow 后保留变更原因。
- [ ] 不允许出现 `final_v2`、`最新版`、`修正版` 这种文件名灾难。版本要可读、可追溯、可回滚。

---

# 7. P1：Provider Router 视频模型调度

## 7.1 统一 Provider 接口

- [ ] 建立统一 Video Provider 接口。
- [ ] 支持 Kling、Seedance、Runway、ComfyUI、即梦、豆包等 Provider。
- [ ] 每个 Provider 接收统一 Shot 输入，输出统一任务结果。
- [ ] 底层模型变化不能影响导演逻辑。

## 7.2 Provider 选择策略

- [ ] 根据镜头类型选择 Provider。
- [ ] 对动作戏、对话、人物特写、环境镜头分别设定推荐 Provider。
- [ ] 支持失败后自动 fallback。
- [ ] 记录每个 Provider 的成本、速度、成功率、常见失败原因。

## 7.3 成本控制

- [ ] 每个 shot 记录生成成本。
- [ ] 每个 clip 记录总成本。
- [ ] 每个 episode 记录总成本。
- [ ] 超出预算时禁止继续批量生成，先进入人工确认。

---

# 8. P1：ComfyUI 执行层

## 8.1 ComfyUI 作为后台执行器

- [ ] 将 ComfyUI 定位为后台执行层，不让普通用户直接面对复杂节点。
- [ ] 前台只展示导演画布、参数配置、资产选择和结果状态。
- [ ] 支持从 Shot / Workflow 自动生成或选择 ComfyUI workflow。

## 8.2 Workflow Planner

- [ ] 新增 Workflow Planner。
- [ ] 输入：shot schema + asset ids + provider constraints。
- [ ] 输出：可执行的 ComfyUI workflow 或外部 Provider request。
- [ ] 增加 Workflow Validator，检查节点缺失、模型缺失、输入缺失、路径错误。

---

# 9. P1：QC Agent 质量检查

## 9.1 QC 检查项

- [ ] 检查人脸是否漂移。
- [ ] 检查服装是否变化。
- [ ] 检查道具是否丢失。
- [ ] 检查武器是否变形。
- [ ] 检查场景是否错乱。
- [ ] 检查人物站位是否错误。
- [ ] 检查是否越轴。
- [ ] 检查镜头运动是否符合设定。
- [ ] 检查光线是否连续。
- [ ] 检查是否出现现代物件。
- [ ] 检查是否缺少关键元素。

## 9.2 QA Gate

- [ ] export 前必须自动运行 QA。
- [ ] 只要存在 BLOCKER，禁止导出。
- [ ] QA 报告必须记录 qa_status、allow_export、blocker_count、warning_count。
- [ ] QA 失败时必须给出返修建议，不只报错。单纯报错就像医院只告诉你“你有问题”，废话艺术。

---

# 10. P1：Auto Repair 自动返修

## 10.1 返修策略

- [ ] 轻微问题：局部编辑。
- [ ] 中等问题：保留首帧重新生成。
- [ ] 严重问题：重做该 shot。
- [ ] 连续失败：更换 Provider。
- [ ] 资产错误：回到资产节点修正。
- [ ] 分镜错误：回到 Shot Planner。

## 10.2 Shot Lock / Asset Lock / Scene Lock

- [ ] 增加 Shot Lock，返修时只允许修改指定 shot。
- [ ] 增加 Asset Lock，返修时锁定人物、服装、道具、场景。
- [ ] 增加 Scene Lock，返修时保持空间方向、光线、场景布局。
- [ ] 单次定向返修只改变一个主要变量。

---

# 11. P1：Director Agent 多 Agent 架构

## 11.1 Agent 拆分

- [ ] Director Agent：导演总控。
- [ ] Script Agent：剧本分析。
- [ ] Beat Agent：剧情节拍。
- [ ] Shot Agent：分镜规划。
- [ ] Asset Agent：资产匹配。
- [ ] Prompt Agent：提示词转换。
- [ ] Provider Agent：模型调度。
- [ ] QC Agent：质量检查。
- [ ] Repair Agent：自动返修。

## 11.2 Agent 约束

- [ ] 不允许一个 Agent 同时负责全部流程。
- [ ] 每个 Agent 必须有输入、输出、失败条件和验收标准。
- [ ] Agent 之间通过结构化 JSON 交接，不通过大段自然语言糊墙。

---

# 12. P2：导演画布与 UI

## 12.1 画布节点

- [ ] 支持右键添加节点。
- [ ] 节点类型包括：剧本节点、场景节点、角色资产节点、道具资产节点、镜头节点、首帧节点、尾帧节点、视频生成节点、音频节点、QC 节点、返修节点、导出节点。
- [ ] 节点可选择模型、输入参数、资产引用和执行状态。
- [ ] 画布节点必须对应真实数据，不做纯展示假按钮。

## 12.2 右侧 AI 对话框

- [ ] AI 能理解当前画布结构。
- [ ] AI 能根据用户指令新增、修改、连接节点。
- [ ] AI 不能越过 QA Gate 直接导出。
- [ ] AI 的每次修改必须有 diff / change summary。

## 12.3 手机端可用性

- [ ] 修复手机端打不开或主界面不可用问题。
- [ ] 手机端优先支持查看项目、查看分镜、审核 QA、提交返修意见。
- [ ] 手机端不优先做复杂画布编辑。

---

# 13. P2：声音与音频模块

## 13.1 角色声音

- [ ] 每个主要角色绑定 voice_id。
- [ ] 支持声音资产与角色资产统一管理。
- [ ] 台词必须记录语气、速度、停顿和情绪。

## 13.2 环境音与音效

- [ ] 每个 shot 记录 environment sound。
- [ ] 重要动作记录 SFX。
- [ ] 打斗镜头必须记录接触音、兵器音、脚步、衣料、呼吸。
- [ ] 音效作为生产物料，不再依赖剪辑阶段临时补。

---

# 14. P2：directorskills 知识库接入

## 14.1 导演知识召回

- [ ] 接入 `directorskills` 作为导演专业知识库。
- [ ] 按阶段召回 3-5 个相关技能，不一次性塞满上下文。
- [ ] 优先接入 directing-masterclass、shot-design、master-shots-v1/v2/v3、sound-design。
- [ ] 召回结果必须转成 Shot / Beat / Coverage 建议，而不是直接展示知识文本。

## 14.2 生产规则固化

- [ ] 固化人物站位、运动方向、景别跳切、焦段、15 秒视频段、对白、环境音、资产一致性规则。
- [ ] 这些规则进入导演系统，不进入 LingJi 的机会雷达。

---

# 15. P2：导出与下游执行

## 15.1 导出物

- [ ] 支持导出分集剧本。
- [ ] 支持导出资产清单。
- [ ] 支持导出镜头执行表。
- [ ] 支持导出故事板。
- [ ] 支持导出视频提示词。
- [ ] 支持导出声音提示词。
- [ ] 支持导出 QC 报告。
- [ ] 支持导出返修清单。

## 15.2 下游兼容

- [ ] 兼容 Kling。
- [ ] 兼容 Seedance。
- [ ] 兼容 Runway。
- [ ] 兼容 ComfyUI。
- [ ] 兼容剪辑工具的人工导入流程。

---

# 16. 不允许混入导演系统的内容

以下内容不要写进导演系统开发待办，必须放入 LingJi 仓库：

- 统一第二大脑
- Obsidian 记忆入口
- AI 聊天记录采集
- MemoryGateway
- HybridRetriever
- Qdrant 记忆索引
- AnySearch 默认搜索层
- 赚钱机会评分
- 每日 AI 简报归档
- 文档更新队列
- LingJi Control 桌面状态页
- 机会验证闭环
- 个人记忆 Core / 候选 / 拒绝 / supersede

导演系统可以调用 LingJi 提供的上下文和工具情报，但不实现 LingJi 的记忆和机会系统。

---

# 17. 下一步执行顺序

## 第一批执行

- [ ] 标准化 `shot.schema.json`。
- [ ] 建立 `Beat Library`。
- [ ] 建立 `Asset ID` 规范。
- [ ] 建立 `Continuity Memory` 与 `Scene State`。
- [ ] 完善 QA Gate 和 BLOCKER 规则。

## 第二批执行

- [ ] 建立 `Workflow Library`。
- [ ] 建立 `Provider Router`。
- [ ] 增加 `Shot Lock` / `Asset Lock` / `Scene Lock`。
- [ ] 增加 `QC Agent` 输出结构。
- [ ] 增加 `Auto Repair` 返修策略。

## 第三批执行

- [ ] 接入 ComfyUI 作为后台执行层。
- [ ] 规划 Director Agent 多 Agent 架构。
- [ ] 建立导演画布节点系统。
- [ ] 接入 directorskills 知识库。
- [ ] 增加手机端审核和返修流程。

---

# 18. 当前结论

AI 短剧导演系统的长期定位是：

```text
AI 短剧 / AI 漫剧生产控制器
+ 导演分镜系统
+ 资产锁定系统
+ 视频模型调度层
+ QC 质检与自动返修系统
```

它负责剧本、节拍、镜头、资产、视频生成、质检、返修和导出。

它不负责 LingJi 的记忆、机会雷达、每日简报和第二大脑。

两个仓库边界必须保持清楚。否则项目会膨胀成一个“什么都想做、什么都做不完”的人类经典软件纪念碑。
