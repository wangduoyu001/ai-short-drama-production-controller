from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ProviderKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    TTS = "tts"
    WORKFLOW = "workflow"
    ASSEMBLY = "assembly"


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    kind: ProviderKind
    enabled: bool = False
    endpoint: str | None = None
    capabilities: tuple[str, ...] = ()

    def validate(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("provider_id must not be empty")
        if self.enabled and self.kind is not ProviderKind.ASSEMBLY and not self.endpoint:
            raise ValueError(f"enabled provider requires endpoint: {self.provider_id}")


class ProviderRegistry:
    def __init__(self, providers: Iterable[ProviderSpec] = ()) -> None:
        self._providers: dict[str, ProviderSpec] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ProviderSpec, *, replace: bool = False) -> None:
        provider.validate()
        if provider.provider_id in self._providers and not replace:
            raise ValueError(f"provider already registered: {provider.provider_id}")
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> ProviderSpec:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise KeyError(f"unknown provider: {provider_id}") from exc

    def resolve(self, kind: ProviderKind, capability: str | None = None) -> ProviderSpec:
        matches = [
            provider
            for provider in self._providers.values()
            if provider.enabled
            and provider.kind is kind
            and (capability is None or capability in provider.capabilities)
        ]
        if not matches:
            suffix = f" with capability {capability}" if capability else ""
            raise LookupError(f"no enabled {kind.value} provider{suffix}")
        return sorted(matches, key=lambda item: item.provider_id)[0]

    def list(self, kind: ProviderKind | None = None) -> tuple[ProviderSpec, ...]:
        values = self._providers.values()
        if kind is not None:
            values = (provider for provider in values if provider.kind is kind)
        return tuple(sorted(values, key=lambda item: item.provider_id))

    def to_dict(self) -> dict[str, object]:
        return {
            "providers": [
                {
                    "provider_id": provider.provider_id,
                    "kind": provider.kind.value,
                    "enabled": provider.enabled,
                    "endpoint": provider.endpoint,
                    "capabilities": list(provider.capabilities),
                }
                for provider in self.list()
            ]
        }


def build_default_provider_registry() -> ProviderRegistry:
    return ProviderRegistry(
        (
            ProviderSpec("local-text", ProviderKind.TEXT, capabilities=("script", "review")),
            ProviderSpec("image-gateway", ProviderKind.IMAGE, capabilities=("character", "scene", "storyboard")),
            ProviderSpec("video-gateway", ProviderKind.VIDEO, capabilities=("image-to-video", "text-to-video")),
            ProviderSpec("speech-gateway", ProviderKind.TTS, capabilities=("dialogue", "narration")),
            ProviderSpec("workflow-gateway", ProviderKind.WORKFLOW, capabilities=("task-import", "task-status")),
            ProviderSpec("ffmpeg", ProviderKind.ASSEMBLY, enabled=True, capabilities=("concat", "mix")),
        )
    )
