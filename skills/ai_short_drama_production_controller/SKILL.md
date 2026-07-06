# AI短剧生产控制器 Skill / 技能说明

## 技能名称

AI Short Drama Production Controller / AI短剧生产控制器

## 用途

本 Skill / 技能不是一键生成视频。它的交付物不是最终视频，而是导演对剧本进行拆分整理后的标准化生产物料包。

用户给一个剧本、小说片段、口述创意或参考片拆解后，本 Skill / 技能需要交付：剧本拆解、资产锁定、分镜设计、生成提示词、质检返修、平台导出表。

## 主入口

默认使用 v0.2 full pipeline / v0.2完整流程：

```bash
python -m short_drama_controller.v02_full_cli init --input examples/input_script.md --out demo_v02 --title 镖局收徒Demo
python -m short_drama_controller.v02_full_cli qa --project demo_v02
python -m short_drama_controller.v02_full_cli repair --project demo_v02
python -m short_drama_controller.v02_full_cli export --project demo_v02
```

## 安装

```bash
python -m pip install -e .
python scripts/install_for_codex.py
```

## 语言规则

所有英文专业词必须同时带中文解释。禁止只写英文术语。

正确示例：

```text
QA / 质检
source_text / 原文
source_coverage / 原文覆盖检查
pipeline / 流程
fallback_shot / 备用镜头
prompt / 生成提示词
asset_lock / 资产锁定
```

错误示例：

```text
QA
source coverage
pipeline
fallback
prompt
```

## 硬规则

1. 必须保留 `source_text 原文`。
2. 必须执行 `source_coverage 原文覆盖检查`。
3. `dialogue 对白` 必须绑定到已提取角色。
4. `spoken_dialogue 出口对白` 必须有明确的 `speaker_spatial_anchor 说话人空间锚点`。
5. `OS 画外音 / 内心独白 / 旁白` 镜头必须让画面人物全员闭口。
6. 每个镜头必须包含景别、机位、运镜、运动轨迹、连续性锁定、备用镜头、声音字段。
7. 高风险动作镜头可使用 `grid_cut_mode 宫格硬切模式` 和 `black_frame_anchor 黑屏冻结锚`。
8. 返修必须直接替换旧文档，禁止生成 final、v2、fixed、new 等副本。
9. 禁止新增无意义 Markdown / md文档。
10. 禁止复制第三方提示词模板原文，只能提炼规则。

## 交付物定义

用户给剧本后，最终只允许交付以下文档和表格。除非用户明确要求，禁止新增其它 md 文档。

```text
project.yaml                 项目总控数据
script.md                    剧本拆解文档
assets.md                    资产锁定文档
storyboard.md                分镜执行文档
prompts.md                   生成提示词文档
qa.md                        质检返修文档
exports/video_prompts.md     视频提示词导出文档
exports/grid_prompts.md      宫格硬切提示词导出文档
exports/shot_table.csv       镜头执行表
exports/sound_table.csv      声音设计表
```

## 禁止生成的文档

禁止生成以下类型文件：

```text
最终方案.md
最终版.md
优化建议.md
分析报告.md
项目总结.md
制作计划.md
下一步.md
修复记录.md
qa_final.md
prompts_v2.md
storyboard_fixed.md
assets_new.md
```

如果某一环节有问题，修改后必须覆盖原文件，不能另存新文档。

## 六个核心文档要求

### project.yaml 项目总控数据

用途：给系统读取的唯一结构化母文件。

必须包含：项目名、原文、制作范围、角色列表、场景列表、道具列表、对白列表、分镜列表、质检状态。

### script.md 剧本拆解文档

用途：保存原文、改写剧本、对白表、OS / 画外音标记、原文覆盖状态。

要求：原文必须完整保留，不能只写总结。

### assets.md 资产锁定文档

用途：锁定角色、场景、道具，服务角色一致性。

必须包含：脸型、发型、服装、道具、颜色、场景结构、固定物件、禁止变化。

### storyboard.md 分镜执行文档

用途：导演分镜表。

必须包含：镜头编号、对应原文、镜头目的、景别、机位、运镜、轴线、人物站位、动作轨迹、起始姿态、结束姿态、备用镜头。

### prompts.md 生成提示词文档

用途：集中保存图片提示词、视频提示词、声音提示词、负面提示词、宫格提示词。

要求：不要单独再拆 video_prompt、sound_prompt、grid_prompt 等新 md 文档。

### qa.md 质检返修文档

用途：保存质检状态、问题列表、返修动作。

状态只能是：PASS / 通过，WARN / 警告，BLOCKER / 阻塞。

## 覆盖替换规则

当用户要求修复、优化、返修、重跑时：

1. 直接覆盖旧的 `script.md 剧本拆解文档`。
2. 直接覆盖旧的 `assets.md 资产锁定文档`。
3. 直接覆盖旧的 `storyboard.md 分镜执行文档`。
4. 直接覆盖旧的 `prompts.md 生成提示词文档`。
5. 直接覆盖旧的 `qa.md 质检返修文档`。
6. 直接覆盖旧的 `exports/` 导出文件。

禁止生成：`xxx_new.md`、`xxx_final.md`、`xxx_v2.md`、`xxx_fixed.md`。

## QA / 质检闸门

v0.2 QA / 质检必须检查：

- `project_schema 项目结构校验`
- `source_coverage 原文覆盖检查`
- `speaker_binding 说话人绑定`
- `speaker_spatial_anchor 说话人空间锚点`
- `shot_size_jump 景别跳变`
- `camera_movement 机位运动`
- `motion_path 运动轨迹`
- `sound_design 声音设计字段`
- `mouth_state 嘴型状态`

## 推荐制作范围

除非用户明确扩大范围，默认使用：

```text
duration_seconds 时长秒数: 60-90
shot_count 镜头数量: 8-12
character_count 角色数量: 2-3
main_scene_count 主场景数量: 1
dialogue_rounds 对话轮数: 2-3
action_level 动作等级: low_to_medium 低到中
```

## 工作流

```text
input 输入
↓
extract_assets 资产提取
↓
bind_dialogue_to_characters 说话人绑定
↓
build_shots 分镜生成
↓
attach_sound_and_prompts 音效与提示词生成
↓
validate QA质检
↓
repair_project 返修并覆盖旧文件
↓
export_project 导出生产文件
```

## Codex / 编程代理行为要求

Codex / 编程代理使用本仓库时：

1. 先读本文件。
2. 再读 `CODEX_INSTALL.md Codex安装说明`。
3. 默认使用 `python -m short_drama_controller.v02_full_cli`。
4. 不要把 v0.1 当主流程，除非调试兼容性。
5. 未经用户明确要求，不要把生成项目目录提交进仓库。
6. 不要新增白名单之外的 md 文档。
7. 修复旧环节时直接覆盖旧文档。
