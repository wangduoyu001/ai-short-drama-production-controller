# AI短剧导演系统代码地图 v0.7

## 分层

```
core/
  workflow/    工作流
  story/       剧情结构
  assets/      资产
  storyboard/  分镜

agents/        智能角色编排
providers/     外部能力接口
cli/           命令入口
docs/          文档
tests/         测试
```

## 开发规则

新增功能优先进入核心模块，不直接堆叠在入口层。

所有模型调用必须经过 providers 层。
