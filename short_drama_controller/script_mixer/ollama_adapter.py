from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .intent import IntentProvider, RuleBasedIntentProvider
from .models import ScriptUnit, VisualIntent


class OllamaError(RuntimeError):
    pass


@dataclass(slots=True)
class OllamaModel:
    name: str
    capabilities: list[str] = field(default_factory=list)
    family: str = ""
    parameter_size: str = ""
    quantization_level: str = ""

    def supports(self, capability: str) -> bool:
        return capability.casefold() in {item.casefold() for item in self.capabilities}


@dataclass(slots=True)
class VisionClipAnalysis:
    description: str
    subjects: list[str]
    scene: str
    actions: list[str]
    emotions: list[str]
    tags: list[str]
    shot_type: str
    camera_motion: str
    has_watermark: bool
    quality_score: float


class OllamaClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 90.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._model_cache: dict[str, OllamaModel] = {}

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                data = response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OllamaError(f"Ollama request failed: {method} {path}: {exc}") from exc
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as exc:
            raise OllamaError(f"Ollama returned invalid JSON: {method} {path}") from exc
        if not isinstance(parsed, dict):
            raise OllamaError(f"Ollama response root must be an object: {method} {path}")
        if parsed.get("error"):
            raise OllamaError(str(parsed["error"]))
        return parsed

    def is_available(self, timeout: float = 2.0) -> bool:
        try:
            self._request("GET", "/api/tags", timeout=timeout)
        except OllamaError:
            return False
        return True

    def list_model_names(self) -> list[str]:
        payload = self._request("GET", "/api/tags")
        names: list[str] = []
        for item in payload.get("models") or []:
            if not isinstance(item, dict):
                continue
            name = item.get("model") or item.get("name")
            if name:
                names.append(str(name))
        return list(dict.fromkeys(names))

    def show_model(self, name: str) -> OllamaModel:
        if name in self._model_cache:
            return self._model_cache[name]
        payload = self._request("POST", "/api/show", {"model": name, "verbose": False})
        details = payload.get("details") or {}
        model = OllamaModel(
            name=name,
            capabilities=[str(item) for item in payload.get("capabilities") or []],
            family=str(details.get("family") or ""),
            parameter_size=str(details.get("parameter_size") or ""),
            quantization_level=str(details.get("quantization_level") or ""),
        )
        self._model_cache[name] = model
        return model

    @staticmethod
    def _name_priority(name: str, capability: str) -> tuple[int, str]:
        lowered = name.casefold()
        if capability == "vision":
            patterns = ("qwen3-vl", "qwen2.5-vl", "qwen2-vl", "gemma", "minicpm-v", "llava")
        else:
            patterns = ("qwen3", "qwen2.5", "glm", "gemma", "llama", "mistral")
        for index, pattern in enumerate(patterns):
            if pattern in lowered:
                return index, lowered
        return len(patterns), lowered

    def select_model(
        self,
        capability: str = "completion",
        preferred: str = "",
    ) -> OllamaModel | None:
        names = self.list_model_names()
        if preferred:
            exact = next((name for name in names if name == preferred), None)
            if not exact:
                exact = next((name for name in names if name.casefold() == preferred.casefold()), None)
            if exact:
                model = self.show_model(exact)
                if model.supports(capability):
                    return model
                raise OllamaError(f"Configured model {preferred} does not support {capability}")
            raise OllamaError(f"Configured Ollama model is not installed: {preferred}")

        candidates: list[OllamaModel] = []
        for name in names:
            try:
                model = self.show_model(name)
            except OllamaError:
                continue
            if model.supports(capability):
                candidates.append(model)
        if not candidates:
            return None
        if capability == "completion":
            candidates.sort(
                key=lambda item: (
                    item.supports("vision"),
                    *self._name_priority(item.name, capability),
                )
            )
        else:
            candidates.sort(key=lambda item: self._name_priority(item.name, capability))
        return candidates[0]

    def generate(
        self,
        model: str,
        prompt: str,
        schema: dict[str, Any] | str | None = None,
        images: list[str] | None = None,
        system: str = "",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }
        if schema is not None:
            payload["format"] = schema
        if images:
            payload["images"] = images
        if system:
            payload["system"] = system
        response = self._request("POST", "/api/generate", payload, timeout=timeout)
        content = response.get("response")
        if not isinstance(content, str):
            raise OllamaError("Ollama generate response does not contain text content")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama did not return valid structured JSON") from exc
        if not isinstance(parsed, dict):
            raise OllamaError("Ollama structured output root must be an object")
        return parsed


_INTENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "literal_queries": {"type": "array", "items": {"type": "string"}},
        "metaphor_queries": {"type": "array", "items": {"type": "string"}},
        "positive_tags": {"type": "array", "items": {"type": "string"}},
        "negative_tags": {"type": "array", "items": {"type": "string"}},
        "emotion": {"type": "array", "items": {"type": "string"}},
        "preferred_shots": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "literal_queries",
        "metaphor_queries",
        "positive_tags",
        "negative_tags",
        "emotion",
        "preferred_shots",
    ],
}


_VISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "subjects": {"type": "array", "items": {"type": "string"}},
        "scene": {"type": "string"},
        "actions": {"type": "array", "items": {"type": "string"}},
        "emotions": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": {"type": "string"}},
        "shot_type": {"type": "string"},
        "camera_motion": {"type": "string"},
        "has_watermark": {"type": "boolean"},
        "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "description",
        "subjects",
        "scene",
        "actions",
        "emotions",
        "tags",
        "shot_type",
        "camera_motion",
        "has_watermark",
        "quality_score",
    ],
}


def _string_list(payload: dict[str, Any], key: str, limit: int = 12) -> list[str]:
    values = payload.get(key)
    if not isinstance(values, list):
        return []
    result = [str(item).strip() for item in values if str(item).strip()]
    return list(dict.fromkeys(result))[:limit]


class OllamaIntentProvider:
    def __init__(
        self,
        client: OllamaClient,
        model: str,
        fallback: IntentProvider | None = None,
    ):
        self.client = client
        self.model = model
        self.fallback = fallback or RuleBasedIntentProvider()

    def generate(self, unit: ScriptUnit) -> VisualIntent:
        prompt = (
            "你是短视频素材检索规划器。把文案转换成可在真实视频素材库中搜索的画面要求。"
            "不要复述文案，不要写摄影散文。直接画面必须是可见人物、动作、地点或物体；"
            "隐喻画面必须能表达抽象含义；负向标签用于排除语义冲突画面。\n"
            f"文案角色：{unit.role}\n"
            f"文案：{unit.text}\n"
            "返回严格符合JSON Schema的对象，每个数组保持精简。"
        )
        try:
            payload = self.client.generate(
                model=self.model,
                prompt=prompt,
                schema=_INTENT_SCHEMA,
                system="只输出结构化画面检索意图，不输出解释。",
            )
            intent = VisualIntent(
                unit_id=unit.unit_id,
                literal_queries=_string_list(payload, "literal_queries"),
                metaphor_queries=_string_list(payload, "metaphor_queries"),
                positive_tags=_string_list(payload, "positive_tags"),
                negative_tags=_string_list(payload, "negative_tags"),
                emotion=_string_list(payload, "emotion", limit=6),
                preferred_shots=_string_list(payload, "preferred_shots", limit=6),
            )
            if not intent.literal_queries and not intent.metaphor_queries:
                raise OllamaError("Ollama returned an empty visual intent")
            return intent
        except OllamaError:
            return self.fallback.generate(unit)


class OllamaVisionProvider:
    def __init__(self, client: OllamaClient, model: str):
        self.client = client
        self.model = model

    def analyze(self, image_path: str | Path) -> VisionClipAnalysis:
        image = Path(image_path)
        if not image.is_file():
            raise FileNotFoundError(f"Thumbnail not found: {image}")
        encoded = base64.b64encode(image.read_bytes()).decode("ascii")
        prompt = (
            "分析这张视频关键帧，用于短视频素材检索。只描述画面中可见事实。"
            "识别主体、场景、动作、可表达的情绪、景别、可能的镜头运动线索、"
            "明显水印或大面积文字，并给出0到1的可用画质分。"
            "不要猜人物真实身份，不要根据文件名补充画面中不存在的信息。"
        )
        payload = self.client.generate(
            model=self.model,
            prompt=prompt,
            schema=_VISION_SCHEMA,
            images=[encoded],
            system="只输出严格结构化的画面分析结果。",
            timeout=max(self.client.timeout, 180.0),
        )
        return VisionClipAnalysis(
            description=str(payload.get("description") or "").strip(),
            subjects=_string_list(payload, "subjects"),
            scene=str(payload.get("scene") or "").strip(),
            actions=_string_list(payload, "actions"),
            emotions=_string_list(payload, "emotions", limit=6),
            tags=_string_list(payload, "tags"),
            shot_type=str(payload.get("shot_type") or "unknown").strip(),
            camera_motion=str(payload.get("camera_motion") or "unknown").strip(),
            has_watermark=bool(payload.get("has_watermark", False)),
            quality_score=max(0.0, min(1.0, float(payload.get("quality_score", 0.5)))),
        )
