from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class NodeStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class DirectorNode:
    node_id: str
    node_type: str
    title: str
    depends_on: tuple[str, ...] = ()
    status: NodeStatus = NodeStatus.PENDING
    attempts: int = 0
    artifacts: list[str] = field(default_factory=list)
    error: str | None = None

    def validate(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must not be empty")
        if not self.node_type.strip():
            raise ValueError(f"node_type must not be empty: {self.node_id}")
        if self.node_id in self.depends_on:
            raise ValueError(f"node cannot depend on itself: {self.node_id}")


class DirectorGraph:
    def __init__(self, nodes: Iterable[DirectorNode] = ()) -> None:
        self.nodes: dict[str, DirectorNode] = {}
        for node in nodes:
            self.add(node)

    def add(self, node: DirectorNode, *, replace: bool = False) -> None:
        node.validate()
        if node.node_id in self.nodes and not replace:
            raise ValueError(f"node already exists: {node.node_id}")
        self.nodes[node.node_id] = node

    def validate(self) -> None:
        missing = {
            dependency
            for node in self.nodes.values()
            for dependency in node.depends_on
            if dependency not in self.nodes
        }
        if missing:
            raise ValueError(f"missing node dependencies: {', '.join(sorted(missing))}")
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        temporary: set[str] = set()
        permanent: set[str] = set()
        ordered: list[str] = []

        def visit(node_id: str) -> None:
            if node_id in permanent:
                return
            if node_id in temporary:
                raise ValueError(f"director graph contains cycle at: {node_id}")
            temporary.add(node_id)
            for dependency in self.nodes[node_id].depends_on:
                if dependency not in self.nodes:
                    raise ValueError(f"missing node dependency: {dependency}")
                visit(dependency)
            temporary.remove(node_id)
            permanent.add(node_id)
            ordered.append(node_id)

        for node_id in sorted(self.nodes):
            visit(node_id)
        return tuple(ordered)

    def refresh(self) -> None:
        for node_id in self.topological_order():
            node = self.nodes[node_id]
            if node.status in {NodeStatus.RUNNING, NodeStatus.COMPLETED, NodeStatus.FAILED}:
                continue
            dependency_states = [self.nodes[item].status for item in node.depends_on]
            if any(state is NodeStatus.FAILED for state in dependency_states):
                node.status = NodeStatus.BLOCKED
            elif all(state is NodeStatus.COMPLETED for state in dependency_states):
                node.status = NodeStatus.READY
            else:
                node.status = NodeStatus.PENDING

    def ready_nodes(self) -> tuple[DirectorNode, ...]:
        self.refresh()
        return tuple(self.nodes[item] for item in self.topological_order() if self.nodes[item].status is NodeStatus.READY)

    def start(self, node_id: str) -> None:
        self.refresh()
        node = self.nodes[node_id]
        if node.status is not NodeStatus.READY:
            raise RuntimeError(f"node is not ready: {node_id} ({node.status.value})")
        node.status = NodeStatus.RUNNING
        node.attempts += 1
        node.error = None

    def complete(self, node_id: str, artifacts: Iterable[str] = ()) -> None:
        node = self.nodes[node_id]
        if node.status is not NodeStatus.RUNNING:
            raise RuntimeError(f"node is not running: {node_id}")
        node.status = NodeStatus.COMPLETED
        node.artifacts = list(artifacts)
        self.refresh()

    def fail(self, node_id: str, error: str) -> None:
        node = self.nodes[node_id]
        if node.status is not NodeStatus.RUNNING:
            raise RuntimeError(f"node is not running: {node_id}")
        node.status = NodeStatus.FAILED
        node.error = error
        self.refresh()

    def reset_failed(self, node_id: str) -> None:
        node = self.nodes[node_id]
        if node.status not in {NodeStatus.FAILED, NodeStatus.BLOCKED}:
            raise RuntimeError(f"node is not failed or blocked: {node_id}")
        node.status = NodeStatus.PENDING
        node.error = None
        self.refresh()

    def to_dict(self) -> dict[str, object]:
        self.validate()
        self.refresh()
        return {
            "node_order": list(self.topological_order()),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "title": node.title,
                    "depends_on": list(node.depends_on),
                    "status": node.status.value,
                    "attempts": node.attempts,
                    "artifacts": list(node.artifacts),
                    "error": node.error,
                }
                for node in (self.nodes[item] for item in self.topological_order())
            ],
        }


def build_default_director_graph() -> DirectorGraph:
    graph = DirectorGraph(
        (
            DirectorNode("source", "source", "原始内容"),
            DirectorNode("story", "story", "剧情与事件图谱", ("source",)),
            DirectorNode("script", "script", "剧本与节拍", ("story",)),
            DirectorNode("assets", "assets", "人物场景道具资产", ("script",)),
            DirectorNode("storyboard", "storyboard", "镜头与分镜", ("script", "assets")),
            DirectorNode("image", "render", "分镜图生产", ("storyboard", "assets")),
            DirectorNode("video", "render", "镜头视频生产", ("image",)),
            DirectorNode("audio", "audio", "对白旁白与声音", ("script",)),
            DirectorNode("review", "review", "人工审核与返修", ("video", "audio")),
            DirectorNode("assembly", "assembly", "成片合成", ("review",)),
            DirectorNode("export", "export", "交付导出", ("assembly",)),
        )
    )
    graph.refresh()
    return graph
