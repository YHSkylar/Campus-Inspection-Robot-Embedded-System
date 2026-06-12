from __future__ import annotations

from contextlib import closing
import json
import sqlite3
from pathlib import Path

from .models import AbnormalEvent, DeviceStatus, DisposalRecord, SensorSnapshot, dataclass_to_jsonable


class SQLiteRepository:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sensor_data (
                    data_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    robot_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    data_value TEXT,
                    location TEXT
                );

                CREATE TABLE IF NOT EXISTS abnormal_event (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    robot_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    occurred_at TEXT NOT NULL,
                    location TEXT NOT NULL,
                    image_path TEXT,
                    status TEXT NOT NULL DEFAULT 'unhandled',
                    reported INTEGER NOT NULL DEFAULT 0,
                    source TEXT,
                    bearing REAL NOT NULL DEFAULT 0,
                    details TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS disposal_record (
                    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    handler_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    action_time TEXT NOT NULL,
                    remark TEXT
                );

                CREATE TABLE IF NOT EXISTS device_status (
                    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    robot_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    battery_level REAL NOT NULL,
                    cpu_usage REAL NOT NULL,
                    memory_usage REAL NOT NULL,
                    temperature REAL NOT NULL,
                    sensor_status TEXT NOT NULL,
                    comm_signal INTEGER NOT NULL,
                    mode TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def save_sensor_snapshot(self, snapshot: SensorSnapshot) -> None:
        rows: list[tuple[int, int, str, str, str, str]] = []
        location = snapshot.pose.to_location_text()
        if snapshot.smoke_thermal is not None:
            rows.append(
                (
                    snapshot.robot_id,
                    snapshot.task_id,
                    snapshot.timestamp.isoformat(),
                    "smoke_thermal",
                    json.dumps(dataclass_to_jsonable(snapshot.smoke_thermal), ensure_ascii=False),
                    location,
                )
            )
        if snapshot.electrical is not None:
            rows.append(
                (
                    snapshot.robot_id,
                    snapshot.task_id,
                    snapshot.timestamp.isoformat(),
                    "electrical",
                    json.dumps(dataclass_to_jsonable(snapshot.electrical), ensure_ascii=False),
                    location,
                )
            )
        if snapshot.camera_frame is not None:
            rows.append(
                (
                    snapshot.robot_id,
                    snapshot.task_id,
                    snapshot.timestamp.isoformat(),
                    "camera",
                    json.dumps(dataclass_to_jsonable(snapshot.camera_frame), ensure_ascii=False),
                    location,
                )
            )
        if rows:
            with closing(self._connect()) as conn:
                conn.executemany(
                    """
                    INSERT INTO sensor_data (robot_id, task_id, timestamp, data_type, data_value, location)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.commit()

    def save_event(self, event: AbnormalEvent) -> int:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """
                INSERT INTO abnormal_event
                (robot_id, task_id, event_type, severity, confidence, occurred_at, location,
                 image_path, status, reported, source, bearing, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.robot_id,
                    event.task_id,
                    event.event_type,
                    event.severity,
                    event.confidence,
                    event.occurred_at.isoformat(),
                    event.location,
                    event.image_path,
                    event.status,
                    int(event.reported),
                    event.source,
                    event.bearing_deg,
                    json.dumps(event.details, ensure_ascii=False),
                ),
            )
            event_id = int(cursor.lastrowid)
            conn.commit()
        return event_id

    def update_event_reported(self, event_id: int, reported: bool) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE abnormal_event SET reported = ? WHERE event_id = ?",
                (int(reported), event_id),
            )
            conn.commit()

    def update_event_status(self, event_id: int, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE abnormal_event SET status = ? WHERE event_id = ?",
                (status, event_id),
            )
            conn.commit()

    def list_unreported_events(self) -> list[AbnormalEvent]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT event_id, robot_id, task_id, event_type, severity, confidence, occurred_at,
                       location, image_path, status, reported, source, bearing, details
                FROM abnormal_event
                WHERE reported = 0
                ORDER BY occurred_at ASC, event_id ASC
                """
            ).fetchall()
        return self._rows_to_events(rows)

    def list_events(self) -> list[AbnormalEvent]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT event_id, robot_id, task_id, event_type, severity, confidence, occurred_at,
                       location, image_path, status, reported, source, bearing, details
                FROM abnormal_event
                ORDER BY occurred_at ASC, event_id ASC
                """
            ).fetchall()
        return self._rows_to_events(rows)

    def _rows_to_events(self, rows) -> list[AbnormalEvent]:
        events: list[AbnormalEvent] = []
        for row in rows:
            events.append(
                AbnormalEvent(
                    event_id=row[0],
                    robot_id=row[1],
                    task_id=row[2],
                    event_type=row[3],
                    severity=row[4],
                    confidence=row[5],
                    occurred_at=_parse_datetime(row[6]),
                    location=row[7],
                    image_path=row[8] or "",
                    status=row[9],
                    reported=bool(row[10]),
                    source=row[11] or "",
                    bearing_deg=row[12] or 0.0,
                    details=json.loads(row[13] or "{}"),
                )
            )
        return events

    def save_disposal_record(self, record: DisposalRecord) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO disposal_record (event_id, handler_id, action, action_time, remark)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    record.event_id,
                    record.handler_id,
                    record.action,
                    record.action_time.isoformat(),
                    record.remark,
                ),
            )
            conn.commit()

    def save_device_status(self, status: DeviceStatus) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO device_status
                (robot_id, timestamp, battery_level, cpu_usage, memory_usage, temperature,
                 sensor_status, comm_signal, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    status.robot_id,
                    status.timestamp.isoformat(),
                    status.battery_level,
                    status.cpu_usage,
                    status.memory_usage,
                    status.temperature,
                    json.dumps(status.sensor_status, ensure_ascii=False),
                    status.comm_signal,
                    status.mode,
                ),
            )
            conn.commit()


def _parse_datetime(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value)
