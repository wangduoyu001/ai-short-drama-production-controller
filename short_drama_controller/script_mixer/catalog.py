from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .models import MediaClip, MediaSource


_SCHEMA = """
CREATE TABLE IF NOT EXISTS media_sources (
    source_id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    modified_ns INTEGER NOT NULL,
    fingerprint TEXT NOT NULL,
    duration REAL NOT NULL DEFAULT 0,
    indexed_duration REAL NOT NULL DEFAULT 0,
    ignored_tail_seconds REAL NOT NULL DEFAULT 0,
    width INTEGER NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 0,
    fps REAL NOT NULL DEFAULT 0,
    video_codec TEXT NOT NULL DEFAULT '',
    audio_codec TEXT NOT NULL DEFAULT '',
    has_audio INTEGER NOT NULL DEFAULT 0,
    rotation INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ready',
    error TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_media_sources_path ON media_sources(source_path);
CREATE INDEX IF NOT EXISTS idx_media_sources_fingerprint ON media_sources(fingerprint);
CREATE INDEX IF NOT EXISTS idx_media_sources_status ON media_sources(status);

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
    thumbnail_path TEXT NOT NULL DEFAULT '',
    has_audio INTEGER NOT NULL DEFAULT 0,
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
    keys = set(row.keys())
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
        thumbnail_path=row["thumbnail_path"] if "thumbnail_path" in keys else "",
        has_audio=bool(row["has_audio"]) if "has_audio" in keys else False,
    )


def _row_to_source(row: sqlite3.Row) -> MediaSource:
    keys = set(row.keys())
    duration = float(row["duration"])
    indexed_duration = (
        float(row["indexed_duration"])
        if "indexed_duration" in keys
        else duration
    )
    return MediaSource(
        source_id=row["source_id"],
        source_path=row["source_path"],
        filename=row["filename"],
        extension=row["extension"],
        file_size=int(row["file_size"]),
        modified_ns=int(row["modified_ns"]),
        fingerprint=row["fingerprint"],
        duration=duration,
        width=int(row["width"]),
        height=int(row["height"]),
        fps=float(row["fps"]),
        video_codec=row["video_codec"],
        audio_codec=row["audio_codec"],
        has_audio=bool(row["has_audio"]),
        rotation=int(row["rotation"]),
        indexed_duration=indexed_duration,
        ignored_tail_seconds=(
            float(row["ignored_tail_seconds"])
            if "ignored_tail_seconds" in keys
            else max(0.0, duration - indexed_duration)
        ),
        status=row["status"],
        error=row["error"],
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
            self._ensure_column(connection, "media_sources", "indexed_duration", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "media_sources", "ignored_tail_seconds", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "media_clips", "thumbnail_path", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "media_clips", "has_audio", "INTEGER NOT NULL DEFAULT 0")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_media_clips_has_audio ON media_clips(has_audio)"
            )
            connection.execute(
                """
                UPDATE media_sources
                SET indexed_duration = duration
                WHERE indexed_duration <= 0 AND duration > 0
                """
            )

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def get_source_by_path(self, source_path: str | Path) -> MediaSource | None:
        normalized = str(Path(source_path).resolve())
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM media_sources WHERE source_path = ?",
                (normalized,),
            ).fetchone()
        return _row_to_source(row) if row else None

    def get_source(self, source_id: str) -> MediaSource | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM media_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
        return _row_to_source(row) if row else None

    def list_sources(self, status: str | None = None) -> list[MediaSource]:
        query = "SELECT * FROM media_sources"
        parameters: list[object] = []
        if status is not None:
            query += " WHERE status = ?"
            parameters.append(status)
        query += " ORDER BY source_path"
        with self.connect() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [_row_to_source(row) for row in rows]

    @staticmethod
    def _upsert_source_connection(connection: sqlite3.Connection, source: MediaSource) -> None:
        payload = asdict(source)
        connection.execute(
            """
            INSERT INTO media_sources (
                source_id, source_path, filename, extension, file_size, modified_ns,
                fingerprint, duration, indexed_duration, ignored_tail_seconds,
                width, height, fps, video_codec, audio_codec,
                has_audio, rotation, status, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                source_path=excluded.source_path,
                filename=excluded.filename,
                extension=excluded.extension,
                file_size=excluded.file_size,
                modified_ns=excluded.modified_ns,
                fingerprint=excluded.fingerprint,
                duration=excluded.duration,
                indexed_duration=excluded.indexed_duration,
                ignored_tail_seconds=excluded.ignored_tail_seconds,
                width=excluded.width,
                height=excluded.height,
                fps=excluded.fps,
                video_codec=excluded.video_codec,
                audio_codec=excluded.audio_codec,
                has_audio=excluded.has_audio,
                rotation=excluded.rotation,
                status=excluded.status,
                error=excluded.error,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                payload["source_id"], payload["source_path"], payload["filename"],
                payload["extension"], payload["file_size"], payload["modified_ns"],
                payload["fingerprint"], payload["duration"], payload["indexed_duration"],
                payload["ignored_tail_seconds"], payload["width"], payload["height"],
                payload["fps"], payload["video_codec"], payload["audio_codec"],
                int(payload["has_audio"]), payload["rotation"], payload["status"],
                payload["error"],
            ),
        )

    def upsert_source(self, source: MediaSource) -> None:
        with self.connect() as connection:
            self._upsert_source_connection(connection, source)

    @staticmethod
    def _upsert_clip_connection(connection: sqlite3.Connection, clip: MediaClip) -> None:
        if clip.duration <= 0 or clip.source_end <= clip.source_start:
            raise ValueError(f"Invalid clip time range: {clip.clip_id}")
        payload = asdict(clip)
        connection.execute(
            """
            INSERT INTO media_clips (
                clip_id, source_id, source_path, source_start, source_end, duration,
                description, tags_json, emotions_json, shot_type, camera_motion,
                width, height, quality_score, has_watermark, usable, thumbnail_path, has_audio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                thumbnail_path=excluded.thumbnail_path,
                has_audio=excluded.has_audio,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                payload["clip_id"], payload["source_id"], payload["source_path"],
                payload["source_start"], payload["source_end"], payload["duration"],
                payload["description"], json.dumps(payload["tags"], ensure_ascii=False),
                json.dumps(payload["emotions"], ensure_ascii=False), payload["shot_type"],
                payload["camera_motion"], payload["width"], payload["height"],
                payload["quality_score"], int(payload["has_watermark"]),
                int(payload["usable"]), payload["thumbnail_path"], int(payload["has_audio"]),
            ),
        )

    def upsert_clip(self, clip: MediaClip) -> None:
        with self.connect() as connection:
            self._upsert_clip_connection(connection, clip)

    def upsert_many(self, clips: Iterable[MediaClip]) -> int:
        rows = list(clips)
        with self.connect() as connection:
            for clip in rows:
                self._upsert_clip_connection(connection, clip)
        return len(rows)

    def replace_source_clips(self, source: MediaSource, clips: Iterable[MediaClip]) -> int:
        rows = list(clips)
        with self.connect() as connection:
            self._upsert_source_connection(connection, source)
            connection.execute("DELETE FROM media_clips WHERE source_id = ?", (source.source_id,))
            for clip in rows:
                if clip.source_id != source.source_id:
                    raise ValueError(
                        f"Clip {clip.clip_id} belongs to {clip.source_id}, expected {source.source_id}"
                    )
                self._upsert_clip_connection(connection, clip)
        return len(rows)

    def delete_missing_sources(self, existing_paths: set[str], root: str | Path) -> int:
        normalized_root = Path(root).resolve()
        removed = 0
        with self.connect() as connection:
            rows = connection.execute("SELECT source_id, source_path FROM media_sources").fetchall()
            for row in rows:
                source_path = Path(row["source_path"])
                try:
                    is_under_root = source_path.is_relative_to(normalized_root)
                except (OSError, ValueError):
                    is_under_root = False
                if is_under_root and str(source_path) not in existing_paths:
                    connection.execute("DELETE FROM media_clips WHERE source_id = ?", (row["source_id"],))
                    connection.execute("DELETE FROM media_sources WHERE source_id = ?", (row["source_id"],))
                    removed += 1
        return removed

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
        thumbnail_path=str(payload.get("thumbnail_path", "")),
        has_audio=bool(payload.get("has_audio", False)),
    )


def import_manifest(catalog: MediaCatalog, manifest_path: str | Path) -> int:
    source = Path(manifest_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = payload.get("clips") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Manifest must be a JSON array or an object containing a clips array")
    clips = [clip_from_dict(item) for item in rows if isinstance(item, dict)]
    return catalog.upsert_many(clips)
