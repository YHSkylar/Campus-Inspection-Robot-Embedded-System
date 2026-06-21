from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from app.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


@contextmanager
def connect() -> Iterable[sqlite3.Connection]:
    db_path = settings.database_path
    if db_path.parent != Path("."):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]


def query_one(sql: str, params: tuple[Any, ...] = ()) -> Optional[dict[str, Any]]:
    rows = query(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    with connect() as conn:
        cur = conn.execute(sql, params)
        return int(cur.lastrowid)


def execute_many(sql: str, rows: list[tuple[Any, ...]]) -> None:
    with connect() as conn:
        conn.executemany(sql, rows)


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS known_faces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT,
                image_path TEXT,
                updated_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                robot_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                route_name TEXT NOT NULL,
                route_points TEXT NOT NULL,
                speed REAL NOT NULL,
                frequency TEXT,
                start_time TEXT,
                end_time TEXT,
                status TEXT NOT NULL,
                dispatch_status TEXT NOT NULL,
                conflict_policy TEXT NOT NULL,
                completed_nodes TEXT NOT NULL,
                trajectory TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                robot_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                priority INTEGER NOT NULL,
                status TEXT NOT NULL,
                report_status TEXT NOT NULL,
                location TEXT,
                orientation TEXT,
                snapshot_url TEXT,
                local_alert INTEGER NOT NULL,
                voice_broadcast INTEGER NOT NULL,
                sample_retained INTEGER NOT NULL DEFAULT 0,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS disposal_records (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                action TEXT NOT NULL,
                executor TEXT NOT NULL,
                result TEXT NOT NULL,
                reason TEXT,
                robot_feedback TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS device_status (
                id TEXT PRIMARY KEY,
                robot_id TEXT NOT NULL,
                battery INTEGER NOT NULL,
                localization TEXT NOT NULL,
                sensor_status TEXT NOT NULL,
                cpu_usage REAL NOT NULL,
                memory_usage REAL NOT NULL,
                signal_strength INTEGER NOT NULL,
                online INTEGER NOT NULL,
                mode TEXT NOT NULL,
                abnormal_flags TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS maintenance_records (
                id TEXT PRIMARY KEY,
                operation TEXT NOT NULL,
                operator TEXT NOT NULL,
                status TEXT NOT NULL,
                version_before TEXT,
                version_after TEXT,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                sensitive INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute("DROP TABLE IF EXISTS robots")
        known_face_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(known_faces)").fetchall()
        }
        if "image_path" not in known_face_columns:
            conn.execute("ALTER TABLE known_faces ADD COLUMN image_path TEXT")
        if "updated_at" not in known_face_columns:
            conn.execute("ALTER TABLE known_faces ADD COLUMN updated_at TEXT")

    seed_defaults()


def seed_defaults() -> None:
    now = utc_now()
    default_users = [
        ("u-admin", "admin", "admin123", "admin", now),
        ("u-center", "center", "center123", "control_center", now),
        ("u-duty", "duty", "duty123", "duty_manager", now),
        ("u-security", "security", "security123", "security", now),
        ("u-maintainer", "maintainer", "maintainer123", "maintainer", now),
    ]
    default_known_faces = [
        ("admin", "系统管理员", "admin", now),
        ("center", "控制中心人员", "control_center", now),
        ("duty", "值班主管", "duty_manager", now),
        ("security", "安保人员", "security", now),
        ("maintainer", "维护工程师", "maintainer", now),
    ]
    execute_many(
        """
        INSERT OR IGNORE INTO users (id, username, password, role, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        default_users,
    )
    execute_many(
        """
        DELETE FROM known_faces
        WHERE id = ? AND name = ? AND role = ?
          AND (image_path IS NULL OR image_path = '')
        """,
        [
            ("admin", "系统管理员", "admin"),
            ("center", "控制中心人员", "control_center"),
            ("duty", "值班主管", "duty_manager"),
            ("security", "安保人员", "security"),
            ("maintainer", "维护工程师", "maintainer"),
        ],
    )
    execute_many(
        """
        INSERT OR IGNORE INTO known_faces (id, name, role, created_at)
        VALUES (?, ?, ?, ?)
        """,
        default_known_faces,
    )
    execute(
        """
        DELETE FROM known_faces
        WHERE image_path IS NULL OR image_path = ''
        """
    )
    execute(
        """
        UPDATE known_faces
        SET updated_at = COALESCE(updated_at, created_at)
        WHERE updated_at IS NULL OR updated_at = ''
        """
    )
