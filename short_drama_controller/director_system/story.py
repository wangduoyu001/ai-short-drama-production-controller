from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class StoryEvent:
    event_id: str
    chapter_id: str
    summary: str
    source_quote: str
    characters: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    props: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id must not be empty")
        if not self.chapter_id.strip():
            raise ValueError(f"chapter_id must not be empty: {self.event_id}")
        if not self.summary.strip():
            raise ValueError(f"summary must not be empty: {self.event_id}")
        if not self.source_quote.strip():
            raise ValueError(f"source_quote must not be empty: {self.event_id}")
        if self.event_id in self.depends_on:
            raise ValueError(f"event cannot depend on itself: {self.event_id}")


@dataclass
class StoryGraph:
    events: dict[str, StoryEvent] = field(default_factory=dict)

    def add(self, event: StoryEvent, *, replace: bool = False) -> None:
        event.validate()
        if event.event_id in self.events and not replace:
            raise ValueError(f"event already exists: {event.event_id}")
        self.events[event.event_id] = event

    def extend(self, events: Iterable[StoryEvent]) -> None:
        for event in events:
            self.add(event)

    def validate(self) -> None:
        missing = {
            dependency
            for event in self.events.values()
            for dependency in event.depends_on
            if dependency not in self.events
        }
        if missing:
            raise ValueError(f"missing event dependencies: {', '.join(sorted(missing))}")
        self.topological_order()

    def topological_order(self) -> tuple[str, ...]:
        temporary: set[str] = set()
        permanent: set[str] = set()
        ordered: list[str] = []

        def visit(event_id: str) -> None:
            if event_id in permanent:
                return
            if event_id in temporary:
                raise ValueError(f"story graph contains cycle at: {event_id}")
            temporary.add(event_id)
            event = self.events[event_id]
            for dependency in event.depends_on:
                if dependency not in self.events:
                    raise ValueError(f"missing event dependency: {dependency}")
                visit(dependency)
            temporary.remove(event_id)
            permanent.add(event_id)
            ordered.append(event_id)

        for event_id in sorted(self.events):
            visit(event_id)
        return tuple(ordered)

    def chapter_events(self, chapter_id: str) -> tuple[StoryEvent, ...]:
        return tuple(
            self.events[event_id]
            for event_id in self.topological_order()
            if self.events[event_id].chapter_id == chapter_id
        )

    def context_for(self, event_id: str, *, depth: int = 2) -> tuple[StoryEvent, ...]:
        if event_id not in self.events:
            raise KeyError(f"unknown event: {event_id}")
        selected: set[str] = {event_id}
        frontier = {event_id}
        for _ in range(max(depth, 0)):
            next_frontier: set[str] = set()
            for current in frontier:
                next_frontier.update(self.events[current].depends_on)
            selected.update(next_frontier)
            frontier = next_frontier
            if not frontier:
                break
        order = self.topological_order()
        return tuple(self.events[item] for item in order if item in selected)

    def to_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "event_order": list(self.topological_order()),
            "events": [
                {
                    "event_id": event.event_id,
                    "chapter_id": event.chapter_id,
                    "summary": event.summary,
                    "source_quote": event.source_quote,
                    "characters": list(event.characters),
                    "locations": list(event.locations),
                    "props": list(event.props),
                    "depends_on": list(event.depends_on),
                    "tags": list(event.tags),
                }
                for event in (self.events[item] for item in self.topological_order())
            ],
        }
