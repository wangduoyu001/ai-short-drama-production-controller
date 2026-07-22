from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import MediaClip


_SCHEMA = """
CREATE TABLE IF NOT EXISTS media_clips (
    clip_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_start REAL NOT NULL,
    source_end REAL NOT NULL,
    duration REAL NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    emotions_json TEXT NOT NULL DEFAULT '[]',
    shot_type TEXT NOT NULL DEFAULT 'unknown',
    camera_motion TEXT NOT NULL DEFAULT 'unknown',
    width INTEGER NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 0,
    quality_score REAL NOT NULL DEFAULT 0.5,
    has_watermark INTEGER NOT NULL DEFAULT 0,
    usable INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_media_clips_source_id ON media_clips(source_id);
CREATE INDEX IF NOT EXISTS idx_media_clips_usable ON media_clips(usable);
CREATE TABLE IF NOT EXISTS usage_history (
    project_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    clip_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    used_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, segment_id)
);
CREATE INDEX IF NOT EXISTS idx_usage_history_clip_id ON usage_history(clip_id);
"""


def _loads_list(value: str) -> list[str]:
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in loaded] if isinstance(loaded, list) else []


def _row_to_clip(row: sqlite3.Row) -> MediaClip:
    return MediaClip(
        clip_id=row["clip_id"],
        source_id=row["source_id"],
        source_path=row["source_path"],
        source_start=float(row["source_start"]),
        source_end=float(row["source_end"]),
        duration=float(row["duration"]),
        description=row["description"],
        tags=_loads_list(row["tags_json"]),
        emotions=_loads_list(row["emotions_json"]),
        shot_type=row["shot_type"],
        camera_motion=row["camera_motion"],
        width=int(row["width"]),
        height=int(row["height"]),
        quality_score=float(row["quality_score"]),
        has_watermark=bool(row["has_watermark"]),
        usable=bool(row["usable"]),
    )


class MediaCatalog:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(_SCHEMA)

    def upsert_clip(self, clip: MediaClip) -> None:
        if clip.duration <= 0 or clip.source_end <= clip.source_start:
            raise ValueError(f"Invalid clip time range: {clip.clip_id}")
        payload = asdict(clip)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO media_clips (
                    clip_id, source_id, source_path, source_start, source_end, duration,
                    description, tags_json, emotions_json, shot_type, camera_motion,
                    width, height, quality_score, has_watermark, usable
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(clip_id) DO UPDATE SET
                    source_id=excluded.source_id,
                    source_path=excluded.source_path,
                    source_start=excluded.source_start,
                    source_end=excluded.source_end,
                    duration=excluded.duration,
                    description=excluded.description,
                    tags_json=excluded.tags_json,
                    emotions_json=excluded.emotions_json,
                    shot_type=excluded.shot_type,
                    camera_motion=excluded.camera_motion,
                    width=excluded.width,
                    height=excluded.height,
                    quality_score=excluded.quality_score,
                    has_watermark=excluded.has_watermark,
                    usable=excluded.usable,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    payload["clip_id"],
                    payload["source_id"],
                    payload["source_path"],
                    payload["source_start"],
                    payload["source_end"],
                    payload["duration"],
                    payload["description"],
                    json.dumps(payload["tags"], ensure_ascii=False),
                    json.dumps(payload["emotions"], ensure_ascii=False),
                    payload["shot_type"],
                    payload["camera_motion"],
                    payload["width"],
                    payload["height"],
                    payload["quality_score"],
                    int(payload["has_watermark"]),
                    int(payload["usable"]),
                ),
            )

    def upsert_many(self, clips: Iterable[MediaClip]) -> int:
        count = 0
        for clip in clips:
            self.upsert_clip(clip)
            count += 1
        return count

    def list_clips(self, usable_only: bool = True, limit: int | None = None) -> list[MediaClip]:
        query = "SELECT * FROM media_clips"
        parameters: list[object] = []
        if usable_only:
            query += " WHERE usable = 1"
        query += " ORDER BY quality_score DESC, clip_id"
        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_row_to_clip(row) for row in rows]

    def recent_usage_counts(self) -> dict[str, int]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT clip_id, COUNT(*) AS count FROM usage_history GROUP BY clip_id"
            ).fetchall()
        return {row["clip_id"]: int(row["count"]) for row in rows}

    def record_usage(self, project_id: str, segments: Iterable[tuple[str, str, str]]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO usage_history(project_id, segment_id, clip_id, source_id)
                VALUES (?, ?, ?, ?)
                """,
                [(project_id, segment_id, clip_id, source_id) for segment_id, clip_id, source_id in segments],
            )


def clip_from_dict(payload: dict) -> MediaClip:
    source_start = float(payload.get("source_start", 0.0))
    source_end = float(payload.get("source_end", 0.0))
    duration = float(payload.get("duration", source_end - source_start))
    return MediaClip(
        clip_id=str(payload["clip_id"]),
        source_id=str(payload.get("source_id") or Path(str(payload["source_path"])).stem),
        source_path=str(payload["source_path"]),
        source_start=source_start,
        source_end=source_end,
        duration=duration,
        description=str(payload.get("description", "")),
        tags=[str(item) for item in payload.get("tags", [])],
        emotions=[str(item) for item in payload.get("emotions", [])],
        shot_type=str(payload.get("shot_type", "unknown")),
        camera_motion=str(payload.get("camera_motion", "unknown")),
        width=int(payload.get("width", 0)),
        height=int(payload.get("height", 0)),
        quality_score=float(payload.get("quality_score", 0.5)),
        has_watermark=bool(payload.get("has_watermark", False)),
        usable=bool(payload.get("usable", True)),
    )


def import_manifest(catalog: MediaCatalog, manifest_path: str | Path) -> int:
    source = Path(manifest_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("clips") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Manifest must be a JSON array or an object containing a clips array")
    clips = [clip_from_dict(item) for item in rows if isinstance(item, dict)]
    return catalog.upsert_many(clips)
