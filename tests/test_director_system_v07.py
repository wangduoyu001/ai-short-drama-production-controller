from __future__ import annotations

import pytest

from short_drama_controller.director_system import (
    NodeStatus,
    ProviderKind,
    StoryEvent,
    StoryGraph,
    build_default_director_graph,
    build_default_provider_registry,
    default_agent_team,
)
from short_drama_controller.version import PACKAGE_VERSION


def test_single_version() -> None:
    assert PACKAGE_VERSION == "0.7.0"


def test_default_director_graph_is_acyclic_and_starts_ready() -> None:
    graph = build_default_director_graph()
    assert graph.topological_order()[0] == "source"
    assert [node.node_id for node in graph.ready_nodes()] == ["source"]


def test_director_graph_progression_and_blocking() -> None:
    graph = build_default_director_graph()
    graph.start("source")
    graph.complete("source", ["source.sha256"])
    assert graph.nodes["story"].status is NodeStatus.READY

    graph.start("story")
    graph.fail("story", "invalid event graph")
    assert graph.nodes["script"].status is NodeStatus.BLOCKED

    graph.reset_failed("story")
    assert graph.nodes["story"].status is NodeStatus.READY


def test_story_graph_context_and_cycle_detection() -> None:
    graph = StoryGraph()
    graph.add(StoryEvent("E1", "C1", "开端", "第一段原文"))
    graph.add(StoryEvent("E2", "C1", "冲突", "第二段原文", depends_on=("E1",)))
    graph.add(StoryEvent("E3", "C2", "升级", "第三段原文", depends_on=("E2",)))
    assert [event.event_id for event in graph.context_for("E3", depth=1)] == ["E2", "E3"]

    cyclic = StoryGraph()
    cyclic.add(StoryEvent("A", "C1", "A", "A", depends_on=("B",)))
    cyclic.add(StoryEvent("B", "C1", "B", "B", depends_on=("A",)))
    with pytest.raises(ValueError, match="cycle"):
        cyclic.validate()


def test_provider_registry_and_agent_team() -> None:
    registry = build_default_provider_registry()
    assembly = registry.resolve(ProviderKind.ASSEMBLY, "concat")
    assert assembly.provider_id == "ffmpeg"
    with pytest.raises(LookupError):
        registry.resolve(ProviderKind.VIDEO)

    roles = {agent.role.value for agent in default_agent_team()}
    assert roles == {"director", "writer", "asset", "storyboard", "production", "reviewer"}
