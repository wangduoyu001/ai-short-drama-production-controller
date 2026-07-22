from __future__ import annotations

import re
from typing import Protocol

from .models import CandidateClip, MediaClip, VisualIntent


class VectorSearchProvider(Protocol):
    def score(self, intent: VisualIntent, clip: MediaClip) -> float:
        ...


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", text.casefold())
    words = {item for item in normalized.split() if item}
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    words.update(chinese[index : index + 2] for index in range(max(0, len(chinese) - 1)))
    words.update(chinese[index : index + 3] for index in range(max(0, len(chinese) - 2)))
    return {item for item in words if item}


def _overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left))


class HybridRetriever:
    """Lexical, structured metadata and optional vector semantic retriever."""

    def __init__(
        self,
        vector_provider: VectorSearchProvider | None = None,
        prefer_source_audio: bool = False,
    ):
        self.vector_provider = vector_provider
        self.prefer_source_audio = prefer_source_audio

    def score_clip(
        self,
        intent: VisualIntent,
        clip: MediaClip,
        usage_count: int = 0,
    ) -> CandidateClip:
        query_tokens = _tokens(" ".join(intent.all_queries))
        description_tokens = _tokens(clip.description)
        tag_tokens = _tokens(" ".join(clip.tags))
        emotion_tokens = _tokens(" ".join(clip.emotions))
        negative_tokens = _tokens(" ".join(intent.negative_tags))
        shot_tokens = _tokens(" ".join(intent.preferred_shots))

        semantic = _overlap_score(query_tokens, description_tokens | tag_tokens)
        tag_match = _overlap_score(query_tokens, tag_tokens)
        emotion_match = _overlap_score(_tokens(" ".join(intent.emotion)), emotion_tokens)
        shot_match = _overlap_score(shot_tokens, _tokens(clip.shot_type))
        vector_score = self.vector_provider.score(intent, clip) if self.vector_provider else 0.0
        quality = max(0.0, min(1.0, clip.quality_score))

        if self.vector_provider is not None and vector_score > 0:
            score = (
                semantic * 0.24
                + tag_match * 0.12
                + emotion_match * 0.09
                + shot_match * 0.05
                + quality * 0.12
                + max(0.0, min(1.0, vector_score)) * 0.38
            )
        else:
            score = (
                semantic * 0.43
                + tag_match * 0.20
                + emotion_match * 0.13
                + shot_match * 0.08
                + quality * 0.16
            )

        reasons: list[str] = []
        if semantic > 0:
            reasons.append(f"semantic={semantic:.2f}")
        if tag_match > 0:
            reasons.append(f"tag={tag_match:.2f}")
        if emotion_match > 0:
            reasons.append(f"emotion={emotion_match:.2f}")
        if shot_match > 0:
            reasons.append(f"shot={shot_match:.2f}")
        if vector_score > 0:
            reasons.append(f"vector={vector_score:.2f}")
        if self.prefer_source_audio and clip.has_audio:
            score += 0.06
            reasons.append("source_audio_bonus=0.06")

        if clip.has_watermark:
            score -= 0.35
            reasons.append("watermark_penalty")
        if not clip.usable:
            score -= 1.0
            reasons.append("unusable")
        if usage_count:
            penalty = min(0.30, usage_count * 0.025)
            score -= penalty
            reasons.append(f"history_penalty={penalty:.2f}")
        negative_overlap = _overlap_score(
            negative_tokens,
            description_tokens | tag_tokens | emotion_tokens,
        )
        if negative_overlap:
            score -= negative_overlap * 0.45
            reasons.append(f"negative_penalty={negative_overlap:.2f}")
        if clip.width and clip.height and clip.width > clip.height:
            score -= 0.02
            reasons.append("horizontal_crop_needed")

        return CandidateClip(
            clip=clip,
            score=round(max(-1.0, min(1.0, score)), 4),
            reasons=reasons,
        )

    def retrieve(
        self,
        intent: VisualIntent,
        clips: list[MediaClip],
        usage_counts: dict[str, int] | None = None,
        limit: int = 40,
    ) -> list[CandidateClip]:
        usage_counts = usage_counts or {}
        candidates = [
            self.score_clip(intent, clip, usage_counts.get(clip.clip_id, 0))
            for clip in clips
            if clip.usable and not clip.has_watermark
        ]
        candidates.sort(
            key=lambda item: (item.score, item.clip.quality_score),
            reverse=True,
        )
        return candidates[:limit]
