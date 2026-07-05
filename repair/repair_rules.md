# repair_rules 返修规则

## repair_actions 返修动作
- ADD 补充：补缺失字段。
- REMOVE 删除：删除高风险内容。
- SPLIT 拆分：拆复杂镜头或长对白。
- MERGE 合并：合并冗余人物、场景、镜头。
- DOWNGRADE 降级：降低动作、机位、场景复杂度。
- LOCK 锁定：锁角色、场景、道具、机位。
- REWRITE 重写：重写剧本、分镜、Prompt。
- FLAG 标记：标记人工检查。

## replacement_policy 替换策略
返修直接覆盖 script.md、assets.md、storyboard.md、prompts.md、qa.md，不生成一堆修复副本。
