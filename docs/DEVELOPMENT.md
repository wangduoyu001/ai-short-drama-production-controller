# 开发指南

## 唯一入口

```bash
short-drama-controller
```

禁止新增带版本号的命令、CLI 文件或并行主流程。

## 模块边界

- `director_system/story.py`：长文本章节事件图谱与上下文提取。
- `director_system/agents.py`：导演团队角色、输入和输出契约。
- `director_system/graph.py`：节点依赖、状态、重试和阻塞。
- `director_system/providers.py`：模型与媒体服务注册、能力路由。
- `cli.py`：参数解析和用户入口，不承载业务逻辑。
- `v06_unified_workflow.py`：现有生产编排兼容实现，后续逐模块迁入无版本号核心模块。

## 新增 Provider

1. 使用唯一 `provider_id`。
2. 指定 `ProviderKind`。
3. 声明 capabilities。
4. 默认 `enabled=False`。
5. 接入真实网络前必须增加离线假发送器测试。
6. 不得在日志、任务清单或回执中保存密钥。

## 新增节点

1. 节点必须有稳定 `node_id`。
2. 依赖必须形成有向无环图。
3. 失败节点必须阻塞所有下游节点。
4. 只有 `running` 节点可以完成或失败。
5. 返修必须重置失败节点，不得复制出平行版本文件。

## 测试

```bash
pytest -q
short-drama-controller doctor
short-drama-controller graph-template
```

测试不得调用公网、GPU、模型下载或付费接口。
