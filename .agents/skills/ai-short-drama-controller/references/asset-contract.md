# Asset contract / 资产生成契约

## Core principle / 核心原则

资产提取必须先理解完整剧情并推演未来镜头，再决定哪些内容值得制作资产。

**镜头决定资产，不是剧本名词决定资产。**

资产只服务于：

- 保持主要人物一致性
- 保持核心场景连续性
- 支撑关键动作、站位和镜头调度
- 支撑跨镜头或跨集复用
- 支撑明显状态变化

不得看到人物、场景或道具名称就机械提取。只出现一次、没有识别需求、不影响连续性的内容，默认不建立正式资产。

## Mandatory decision order / 强制判断顺序

生成任何资产提示词前，必须依次完成：

1. 理解故事核心冲突、人物关系、核心场面和视觉重点。
2. 推演实际会拍摄的主要镜头、景别、机位、人物站位和空间调度。
3. 判断对象是否有清晰识别需求。
4. 判断对象是否需要跨镜头保持一致。
5. 判断对象是否反复使用或存在明显状态变化。
6. 判断制作资产能否减少后续生成错误并覆盖足够多镜头。
7. 删除低价值、一次性、可临时生成的内容。
8. 输出明确的制作清单、状态、视角、数量和理由。

不得跳过镜头推演，直接按人物、场景、道具分类罗列。

## Asset value test / 资产价值判断

每个候选内容必须综合判断：

- `recognition_need 识别需求`：是否出现特写、近景或清晰中景，观众是否需要认出它。
- `shot_reuse 镜头复用`：预计服务多少镜头，是否跨场景或跨集反复出现。
- `continuity_need 连续性需求`：外观变化是否会破坏人物、空间或动作连续性。
- `state_change 状态变化`：是否存在完好/破损、空置/载人、平静/战斗、白天/夜晚等明显变化。
- `spatial_value 空间价值`：是否承担人物活动、站位、运动路线和多机位拍摄。
- `production_roi 制作回报`：制作一张或一组资产，能否明显减少返工、提高一致性并覆盖多个镜头。

无法证明实际价值的内容，默认不制作。

## Asset levels / 资产等级

### `S` Core asset / 核心资产

适用于承担核心剧情、服务大量镜头、需要多机位、多状态或人物长期活动的对象。

必须建立完整资产族，包括：

- 基础标准状态
- 必要多视角
- 关键剧情状态
- 人物使用状态
- 多人物组合状态
- 群体或编队状态
- 空间关系图
- 高频镜头参考图

### `A` Important asset / 重要资产

适用于多次清晰出镜、承担重要剧情、需要一定一致性或少量关键状态变化的对象。

制作标准资产，并补充必要状态和常用视角。

### `B` Limited asset / 普通资产

适用于出镜有限，但临时生成容易产生明显偏差的对象。

只制作 1-2 张基础参考图，不进行过度扩展。

### `C` No formal asset / 无需制作

适用于只出现一次、没有近景识别需求、不承担关键动作、不影响连续性、可直接在镜头中生成或可由已有资产组合完成的内容。

C 级内容不得生成正式资产提示词。

## Character rules / 人物资产规则

正式人物资产只适用于：

- 主角、重要配角、主要反派
- 多次出现且存在清晰中近景或特写
- 有独立对白、关键动作或重要情绪表演
- 需要跨镜头保持脸、年龄、体型、发型和服装一致

默认人物资产格式，除非用户明确指定其他格式：

- horizontal `16:9 横向`
- pure white background / 纯白背景
- left 35%: front head-and-shoulders close-up / 左侧35%正面大头照
- right 65%: full-body front, right profile, and back views / 右侧65%正面、右侧面、背面三视图
- bottom 13%: thin detail strip / 下方13%薄细节带
- whole body visible, no cropping / 全身完整，不裁脚、不裁头

Detail strip should show only production-relevant details, such as:

- face and eye details
- hairstyle and hair accessory
- costume fabric, seam, fastener, armor, or embroidery
- footwear
- signature prop or weapon
- compact color swatches when requested

Identity locks:

- same face
- same apparent age
- same body proportion
- same hairstyle
- same costume construction
- same costume materials and colors
- same signature marks
- same weapon dimensions and materials

### Crowd and background people / 群体人物规则

以下内容通常不建立单体人物资产：

- 只出现在远景或大全景中的普通士兵
- 路人、百姓、群众、侍卫、水兵、船工
- 无台词、无独立动作、无需观众识别的背景人物

这类内容只需要定义：

- 群体类型和阵营
- 大致人数
- 统一服装和色彩规则
- 年龄与体型范围
- 队形和空间位置
- 动作和运动方向

如果群体中某人出现清晰中近景、独立对白或关键动作，才将该人物单独升级为正式人物资产。

## Scene rules / 场景资产规则

正式场景资产适用于：

- 承担大量剧情
- 人物反复活动
- 需要复杂站位和空间调度
- 需要正反打、运动镜头或多方向拍摄
- 场景结构错误会破坏连续性
- 存在关键环境变化

场景资产必须明确：

- 空间规模
- 固定建筑和物体布局
- 入口、出口、通道和障碍
- 人物活动区域
- 前景、中景、后景
- 常用机位和摄影机移动路线
- 光线方向和实景光源
- 主要材质和色调
- 相邻空间关系

核心场景不能只制作一张无人空景。必须根据剧情判断是否还需要：

- 标准空场景
- 主要人物进入后的状态
- 多人物站位状态
- 战斗前、中、后状态
- 白天、夜晚、浓雾、火光等关键环境状态
- 人物主观视角
- 高频正反打方向

场景资产与成片镜头必须区分：基础空间图用于锁定布局，人物使用状态图和镜头资产用于锁定高频组合关系。

## Core carrier rules / 核心载体规则

不得因为某对象形式上属于“道具”，就降低其资产等级。

船只、马车、战车、机关、特殊建筑、关键武器、法器、机械装置、人物长期活动的平台，如果承担大量镜头，应作为核心载体建立资产族。

例如草船资产族可包括：

- 空船基础结构
- 正面、侧面、俯视
- 甲板布局
- 诸葛亮、鲁肃与士兵就位状态
- 士兵击鼓和划桨位置
- 浓雾航行状态
- 接近曹营状态
- 遭遇箭雨状态
- 船舷逐渐插箭状态
- 满箭返航状态
- 多船编队状态
- 靠岸状态
- 船头看船尾、船尾看船头、船舷近景等实用视角

核心载体不能只制作一张空结构图。

## Prop rules / 普通道具规则

普通酒杯、信件、令牌、玉玺、箭矢、桌椅、碗筷等，只出现一次且不影响连续性时，不建立正式资产，直接写入对应镜头提示词。

只有满足以下条件时才升级为资产：

- 外观高度独特
- 多次清晰出镜
- 参与关键动作
- 是重要视觉线索
- 需要多个镜头保持完全一致
- 临时生成极易出错

剧情意义重要，不等于必须建立资产。

## Asset family / 资产族

当同一对象存在多个剧情阶段、状态或高频组合时，必须统一归入同一资产族管理，不得拆成多个无关联资产。

资产族包括：

- `base_asset 基础资产`：稳定外观、结构、比例和材质
- `state_asset 状态资产`：关键剧情阶段的明显变化
- `combination_asset 组合资产`：人物、场景、载体之间反复使用的固定关系
- `shot_asset 镜头资产`：高频人物、站位、场景和机位组合的参考图

镜头资产只在能服务多个镜头时制作，不得为每个单独镜头建立一份资产。

## Stable IDs / 稳定编号

Use stable IDs:

- `C01-C99` characters / 人物
- `S01-S99` scenes / 场景
- `P01-P99` props and carriers / 道具与载体
- `F01-F99` asset families / 资产族
- `G01-G99` crowd groups / 群体规则
- `A01-A99` combination or shot assets / 组合或镜头资产

## Prompt completeness / 提示词完整性

Every prompt must be complete, standalone, and directly usable by an image model.

每个提示词必须独立包含：画面风格、主体、外观、材质、色彩、构图、背景、光线、画幅、禁止项。不得依赖“沿用上一条”“同上”或隐藏母版。

Do not turn a reference sheet into a poster, cinematic key art, interface mockup, or decorative illustration layout.

## Negative constraints / 禁止项

Unless the user asks for them, prohibit:

- text, watermark, logo, UI frame, decorative border
- duplicate body parts or duplicate weapons
- inconsistent face or costume
- cropped body
- perspective distortion that prevents reference use
- motion blur
- movie poster composition
- atmosphere that hides spatial layout
- random extra characters or props that damage continuity

## Required output / 强制输出格式

资产阶段必须输出以下六部分，不得只给模糊建议：

### 1. `story_and_shot_understanding 剧情与镜头理解`

简要说明：

- 核心冲突
- 主要人物
- 核心叙事空间
- 重要视觉场面
- 预计大量出现的镜头类型
- 本次资产制作重点

不得长篇复述剧情。

### 2. `required_assets 必须制作的资产`

每项必须包含：

- 资产名称
- 稳定 ID
- 类型
- 等级 S/A/B
- 剧情作用
- 预计服务镜头
- 识别景别
- 是否需要保持一致
- 是否建立资产族
- 是否需要多状态
- 是否需要多视角
- 是否需要人物组合图
- 建议图片数量
- 必须生成的具体图片
- 制作理由

“必须生成的具体图片”必须逐项明确，不得只写“多视角”“多个状态”。

### 3. `core_asset_families 核心资产族`

每项必须包含：

- 资产族名称与 ID
- 基础状态
- 关键剧情状态
- 人物使用状态
- 组合站位
- 常用机位
- 群体或编队状态
- 建议生成顺序

### 4. `crowd_handling 群体元素处理`

每项必须包含：

- 群体名称与 ID
- 使用场景
- 主要景别
- 是否需要单体资产：默认否
- 服装规则
- 数量和队形
- 动作规则
- 镜头中如何生成

### 5. `excluded_assets 无需制作的内容`

每项必须包含：

- 内容名称
- 不制作原因
- 镜头中如何处理

必须主动排除容易被错误资产化的一次性物品、路人、群众和普通道具。

### 6. `production_order 最终制作顺序`

按优先级输出：

- 第一批：拍摄前必须完成的核心资产
- 第二批：进入分镜后补充的重要资产
- 第三批：根据实际镜头再制作的资产
- 无需制作：直接在镜头生成时处理

## QA gate / 输出前自检

输出前必须检查：

- 是否先推演镜头，再决定资产
- 是否遗漏核心叙事空间和核心载体
- 是否只做空场景，遗漏人物使用状态
- 是否遗漏关键状态变化
- 是否遗漏多人物固定站位
- 是否遗漏群体、编队和运动方向
- 是否为远景士兵、路人或群众错误制作单体资产
- 是否把只出现一次的普通道具过度资产化
- 是否存在重复资产
- 是否明确列出每张需要生成的图片
- 是否用较少资产覆盖较多有效镜头

最终目标：

**用最少、最准确、最可复用的资产，支撑最多的有效镜头。**

## Prompt delivery / 提示词交付

When delivering generation prompts:

- one asset per complete prompt
- include the asset ID and name outside the generation prompt only when useful
- do not include explanations inside the prompt
- do not output a master prompt that requires manual assembly
