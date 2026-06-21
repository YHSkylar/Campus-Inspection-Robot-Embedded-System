from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import HTTPException, status

from app.config import settings
from app.db import dumps, execute, loads, query, query_one, utc_now


MODE_ALIASES = {
    "定点": "fixed",
    "定点巡检": "fixed",
    "fixed": "fixed",
    "定时": "scheduled",
    "定时巡检": "scheduled",
    "scheduled": "scheduled",
    "随机": "random",
    "随机巡检": "random",
    "random": "random",
    "规划路径": "planned_path",
    "路径规划": "planned_path",
    "planned_path": "planned_path",
}

EVENT_ALIASES = {
    "火警": "fire",
    "火焰": "fire",
    "明火": "fire",
    "火灾": "fire",
    "燃烧": "fire",
    "fire": "fire",
    "flame": "fire",
    "烟雾": "smoke",
    "烟": "smoke",
    "smoke": "smoke",
    "haze": "smoke",
    "障碍": "obstacle",
    "障碍物": "obstacle",
    "路障": "obstacle",
    "obstacle": "obstacle",
    "barrier": "obstacle",
    "边界": "boundary",
    "越界": "boundary",
    "边线": "boundary",
    "boundary": "boundary",
    "border": "boundary",
    "人员": "unauthorized_person",
    "人员告警": "unauthorized_person",
    "人脸": "unauthorized_person",
    "未授权人员": "unauthorized_person",
    "陌生人": "unauthorized_person",
    "unauthorized_person": "unauthorized_person",
    "unauthorized person": "unauthorized_person",
    "person": "unauthorized_person",
    "human": "unauthorized_person",
    "非法入侵": "unauthorized_person",
    "入侵": "unauthorized_person",
    "人员入侵": "unauthorized_person",
    "intrusion": "unauthorized_person",
}

EVENT_PRIORITY = {
    "fire": 1,
    "smoke": 2,
    "obstacle": 3,
    "boundary": 4,
    "unauthorized_person": 5,
}

SUPPORTED_EVENT_TYPE_LIST = tuple(EVENT_PRIORITY)
SUPPORTED_EVENT_TYPES = set(SUPPORTED_EVENT_TYPE_LIST)

IMAGE_EVENT_RULES = {
    "fire": {
        "keywords": {
            "fire",
            "flame",
            "flames",
            "burning",
            "blaze",
            "open_fire",
            "火",
            "火焰",
            "火警",
            "明火",
            "火苗",
            "火灾",
            "燃烧",
            "着火",
        },
        "feature_keys": {
            "flame_score",
            "fire_score",
            "fire_probability",
            "flame_probability",
            "flame_detected",
            "fire_detected",
            "open_flame",
            "fire_pixel_ratio",
            "red_area_ratio",
            "orange_area_ratio",
            "yellow_area_ratio",
            "hot_spot_score",
            "thermal_fire_score",
        },
    },
    "smoke": {
        "keywords": {"smoke", "haze", "gray haze", "烟", "烟雾", "浓烟", "灰雾"},
        "feature_keys": {"smoke_score", "gray_area_ratio", "haze_density", "smoke_density"},
    },
    "obstacle": {
        "keywords": {
            "obstacle",
            "barrier",
            "blockage",
            "blocked",
            "roadblock",
            "debris",
            "障碍",
            "障碍物",
            "路障",
            "阻挡",
            "堵塞",
        },
        "feature_keys": {
            "obstacle_score",
            "blocked_area_ratio",
            "obstruction_score",
            "obstacle_count",
        },
    },
    "boundary": {
        "keywords": {
            "boundary",
            "border",
            "edge",
            "line",
            "fence",
            "restricted_boundary",
            "边界",
            "越界",
            "边线",
            "围栏",
            "警戒线",
        },
        "feature_keys": {
            "boundary_score",
            "boundary_overlap",
            "border_line_score",
            "out_of_bounds_score",
        },
    },
}

PERSON_KEYWORDS = {
    "person",
    "human",
    "face",
    "stranger",
    "unknown_face",
    "unauthorized",
    "人员",
    "人脸",
    "陌生人",
    "未授权",
    "闯入",
}

PERSON_FEATURE_KEYS = {
    "person_score",
    "human_score",
    "face_score",
    "face_detected",
    "face_count",
    "human_count",
    "unknown_face",
    "unknown_face_score",
    "unauthorized_face_score",
    "stranger_score",
}

SENSITIVE_DATA_TYPES = {"logs", "maintenance"}


class RobotSystemService:
    def normalize_mode(self, mode: str) -> str:
        normalized = MODE_ALIASES.get(mode)
        if not normalized:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="巡检模式仅支持定点/定时/随机/规划路径",
            )
        return normalized

    def normalize_event_type(self, event_type: str) -> str:
        normalized = EVENT_ALIASES.get(event_type)
        if not normalized:
            normalized = EVENT_ALIASES.get(event_type.strip().lower())
        if not normalized:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="危险事件类型仅支持火焰、烟雾、障碍、边界、未授权人员",
            )
        return normalized

    def log(
        self,
        category: str,
        message: str,
        level: str = "INFO",
        sensitive: bool = False,
    ) -> None:
        execute(
            """
            INSERT INTO logs (id, level, category, message, sensitive, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.new_id("log"), level, category, message, int(sensitive), utc_now()),
        )

    def new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid4().hex[:12]}"

    def snapshot_public_url(self, filename: str) -> str:
        return f"/snapshots/{filename}"

    def save_uploaded_snapshot(
        self, content: bytes, filename: str, prefix: str = "snapshot"
    ) -> dict[str, Any]:
        if not content:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="empty snapshot body")

        raw_suffix = Path(filename or "snapshot.jpg").suffix.lower()
        suffix = raw_suffix if raw_suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} else ".jpg"
        safe_prefix = "".join(
            char if char.isalnum() or char in {"-", "_"} else "_"
            for char in str(prefix or "snapshot")
        ).strip("_") or "snapshot"

        settings.snapshot_path.mkdir(parents=True, exist_ok=True)
        stored_name = f"{safe_prefix}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}{suffix}"
        stored_path = settings.snapshot_path / stored_name
        stored_path.write_bytes(content)
        public_url = self.snapshot_public_url(stored_name)
        return {
            "snapshot_url": public_url,
            "image_url": public_url,
            "local_path": str(stored_path),
            "filename": stored_name,
            "size_bytes": len(content),
        }

    def row_to_task(self, row: dict[str, Any]) -> dict[str, Any]:
        row["route_points"] = loads(row.get("route_points"), [])
        row["completed_nodes"] = loads(row.get("completed_nodes"), [])
        row["trajectory"] = loads(row.get("trajectory"), [])
        return row

    def row_to_event(self, row: dict[str, Any]) -> dict[str, Any]:
        row["location"] = loads(row.get("location"), None)
        row["orientation"] = loads(row.get("orientation"), None)
        row["payload"] = loads(row.get("payload"), {})
        row["local_alert"] = bool(row.get("local_alert"))
        row["voice_broadcast"] = bool(row.get("voice_broadcast"))
        row["sample_retained"] = bool(row.get("sample_retained"))
        return row

    def row_to_device_status(self, row: dict[str, Any]) -> dict[str, Any]:
        row["sensor_status"] = loads(row.get("sensor_status"), {})
        row["abnormal_flags"] = loads(row.get("abnormal_flags"), [])
        row["online"] = bool(row.get("online"))
        return row

    def ensure_role(self, role: str, allowed: set[str]) -> None:
        if role not in allowed and role != "admin":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="权限不足")

    def normalize_robot_id(self, robot_id: Optional[str] = None) -> str:
        robot_id = robot_id or settings.default_robot_id
        if robot_id != settings.default_robot_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="仅支持默认机器人")
        return robot_id

    def disconnected_device_status(self) -> dict[str, Any]:
        return {
            "id": "status-disconnected",
            "robot_id": settings.default_robot_id,
            "battery": 0,
            "localization": "lost",
            "sensor_status": {},
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "signal_strength": 0,
            "online": False,
            "mode": "disconnected",
            "abnormal_flags": ["disconnected"],
            "created_at": utc_now(),
        }

    def latest_device_status(self, robot_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        robot_id = self.normalize_robot_id(robot_id)
        row = query_one(
            "SELECT * FROM device_status WHERE robot_id = ? ORDER BY created_at DESC LIMIT 1",
            (robot_id,),
        )
        return self.row_to_device_status(row) if row else None

    def robot(self, robot_id: str) -> dict[str, Any]:
        robot_id = self.normalize_robot_id(robot_id)
        device_status = self.latest_device_status(robot_id)
        if not device_status:
            return {
                "id": robot_id,
                "name": "巡检机器人",
                "online": False,
                "mode": "disconnected",
                "status": "disconnected",
                "battery": 0,
                "location": None,
                "updated_at": utc_now(),
            }

        online = bool(device_status["online"])
        abnormal = (
            not online
            or bool(device_status["abnormal_flags"])
            or device_status["localization"] != "normal"
        )
        return {
            "id": robot_id,
            "name": "巡检机器人",
            "online": online,
            "mode": device_status["mode"],
            "status": "disconnected" if not online else ("abnormal" if abnormal else "normal"),
            "battery": device_status["battery"],
            "location": None,
            "updated_at": device_status["created_at"],
        }

    def list_routes(self) -> list[dict[str, Any]]:
        return [
            {"method": "GET", "path": "/api/health", "module": "health"},
            {"method": "POST", "path": "/api/auth/login", "module": "auth"},
            {"method": "GET", "path": "/api/routes", "module": "registry"},
            {"method": "POST", "path": "/api/tasks", "module": "tasks"},
            {"method": "GET", "path": "/api/tasks", "module": "tasks"},
            {"method": "PATCH", "path": "/api/tasks/{task_id}", "module": "tasks"},
            {"method": "POST", "path": "/api/tasks/{task_id}/action", "module": "tasks"},
            {"method": "POST", "path": "/api/tasks/{task_id}/dispatch", "module": "tasks"},
            {"method": "DELETE", "path": "/api/tasks/{task_id}", "module": "tasks"},
            {"method": "POST", "path": "/api/inspection/start", "module": "inspection"},
            {"method": "POST", "path": "/api/inspection/{task_id}/confirm", "module": "inspection"},
            {"method": "POST", "path": "/api/inspection/{task_id}/obstacle", "module": "inspection"},
            {"method": "POST", "path": "/api/inspection/{task_id}/battery", "module": "inspection"},
            {"method": "POST", "path": "/api/inspection/{task_id}/emergency-pause", "module": "inspection"},
            {"method": "POST", "path": "/api/events/detect", "module": "events"},
            {"method": "POST", "path": "/api/events/detect/batch", "module": "events"},
            {"method": "POST", "path": "/api/events/flush-cache", "module": "events"},
            {"method": "POST", "path": "/api/events/{event_id}/dispose", "module": "events"},
            {"method": "GET", "path": "/api/events", "module": "events"},
            {"method": "GET", "path": "/api/faces", "module": "faces"},
            {"method": "POST", "path": "/api/faces", "module": "faces"},
            {"method": "POST", "path": "/api/faces/upload", "module": "faces"},
            {"method": "DELETE", "path": "/api/faces/{face_id}", "module": "faces"},
            {"method": "POST", "path": "/api/devices/status", "module": "devices"},
            {"method": "GET", "path": "/api/devices/status/current", "module": "devices"},
            {"method": "GET", "path": "/api/devices/status/history", "module": "devices"},
            {"method": "POST", "path": "/api/devices/{robot_id}/online", "module": "devices"},
            {"method": "POST", "path": "/api/maintenance/operate", "module": "maintenance"},
            {"method": "GET", "path": "/api/maintenance/logs", "module": "maintenance"},
            {"method": "GET", "path": "/api/query", "module": "query"},
            {"method": "GET", "path": "/api/query/export", "module": "query"},
        ]

    def create_task(self, data: dict[str, Any]) -> dict[str, Any]:
        mode = self.normalize_mode(data["mode"])
        speed = float(data["speed"])
        if speed > settings.max_task_speed:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"巡检速度超出最大限制 {settings.max_task_speed}m/s",
            )
        self.validate_time_range(data.get("start_time"), data.get("end_time"))

        robot_id = data.get("robot_id") or settings.default_robot_id
        robot = self.robot(robot_id)
        conflict_policy = "queue"

        dispatch_status = "dispatched" if robot["online"] else "queued"
        task_id = self.new_id("task")
        now = utc_now()
        execute(
            """
            INSERT INTO tasks (
                id, robot_id, mode, route_name, route_points, speed, frequency,
                start_time, end_time, status, dispatch_status, conflict_policy,
                completed_nodes, trajectory, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                robot_id,
                mode,
                data["route_name"],
                dumps(data.get("route_points") or []),
                speed,
                data.get("frequency"),
                data.get("start_time"),
                data.get("end_time"),
                "pending",
                dispatch_status,
                conflict_policy,
                dumps([]),
                dumps([]),
                now,
                now,
            ),
        )
        self.log(
            "task",
            f"任务 {task_id} 已创建，状态 pending，dispatch={dispatch_status}",
        )
        return self.get_task(task_id)

    def validate_time_range(self, start_time: Optional[str], end_time: Optional[str]) -> None:
        if not start_time or not end_time:
            return
        try:
            start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="时间格式非法") from exc
        if end <= start:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="结束时间必须晚于开始时间")

    def get_task(self, task_id: str) -> dict[str, Any]:
        row = query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="任务不存在")
        return self.row_to_task(row)

    def list_tasks(self, status_filter: Optional[str] = None) -> list[dict[str, Any]]:
        if status_filter:
            rows = query("SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC", (status_filter,))
        else:
            rows = query("SELECT * FROM tasks ORDER BY created_at DESC")
        return [self.row_to_task(row) for row in rows]

    def update_task(self, task_id: str, data: dict[str, Any]) -> dict[str, Any]:
        task = self.get_task(task_id)
        merged = {**task, **{k: v for k, v in data.items() if v is not None}}
        merged["mode"] = self.normalize_mode(merged["mode"])
        if float(merged["speed"]) > settings.max_task_speed:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="巡检速度超出最大限制")
        self.validate_time_range(merged.get("start_time"), merged.get("end_time"))
        execute(
            """
            UPDATE tasks
            SET mode = ?, route_name = ?, route_points = ?, speed = ?, frequency = ?,
                start_time = ?, end_time = ?, conflict_policy = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                merged["mode"],
                merged["route_name"],
                dumps(merged.get("route_points") or []),
                float(merged["speed"]),
                merged.get("frequency"),
                merged.get("start_time"),
                merged.get("end_time"),
                "queue",
                utc_now(),
                task_id,
            ),
        )
        self.log("task", f"任务 {task_id} 已修改")
        return self.get_task(task_id)

    def task_action(self, task_id: str, action: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        status_map = {
            "start": "running",
            "pause": "paused",
            "stop": "stopped",
            "complete": "completed",
        }
        status_value = status_map[action]
        execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status_value, utc_now(), task_id))
        self.log("task", f"任务 {task_id} 执行动作 {action}，状态变为 {status_value}")
        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> dict[str, str]:
        self.get_task(task_id)
        execute("UPDATE tasks SET status = 'deleted', updated_at = ? WHERE id = ?", (utc_now(), task_id))
        self.log("task", f"任务 {task_id} 已删除")
        return {"message": "任务已删除", "task_id": task_id}

    def dispatch_task(self, task_id: str, force: bool = False) -> dict[str, Any]:
        task = self.get_task(task_id)
        robot = self.robot(task["robot_id"])
        if task["status"] in {"deleted", "cancelled", "completed"} and not force:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="当前任务状态不可下发")

        if not task["route_points"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="巡检路线不能为空，无法下发")

        if robot["online"]:
            dispatch_status = "dispatched"
            message = "任务已下发至机器人，机器人已确认接收"
        else:
            dispatch_status = "queued"
            message = "机器人离线，任务已暂存至待下发队列"

        execute(
            """
            UPDATE tasks
            SET status = 'pending', dispatch_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (dispatch_status, utc_now(), task_id),
        )
        self.log("task", f"{message}：{task_id}")
        return {"message": message, "task": self.get_task(task_id), "robot_online": robot["online"]}

    def start_inspection(self, task_id: str) -> dict[str, Any]:
        task = self.task_action(task_id, "start")
        trajectory = [{"time": utc_now(), "action": "start", "location": {"area": "standby"}}]
        execute("UPDATE tasks SET trajectory = ?, updated_at = ? WHERE id = ?", (dumps(trajectory), utc_now(), task_id))
        return {"task": self.get_task(task_id), "slam": "localized", "path_plan": "generated"}

    def confirm_inspection_node(self, task_id: str, data: dict[str, Any]) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task["status"] not in {"pending", "running", "paused"}:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Only pending, running, or paused tasks can confirm inspection nodes",
            )

        route_points = task["route_points"]
        node_id = data["node_id"]
        valid_node_ids = {
            str(point.get("id") or point.get("node_id") or index + 1)
            for index, point in enumerate(route_points)
        }
        route_point = next(
            (
                point
                for index, point in enumerate(route_points)
                if str(point.get("id") or point.get("node_id") or index + 1)
                == node_id
            ),
            None,
        )
        if route_points and node_id not in valid_node_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Inspection node does not belong to the current route",
            )

        completed_nodes = task["completed_nodes"]
        if node_id not in completed_nodes:
            completed_nodes.append(node_id)

        sensor_summary = data.get("sensor_summary") or {}
        trajectory = task["trajectory"]
        trajectory.append(
            {
                "time": utc_now(),
                "action": "node_confirmed",
                "node_id": node_id,
                "location": data.get("location"),
                "snapshot_url": data.get("snapshot_url"),
                "sensor_summary": sensor_summary,
            }
        )

        all_confirmed = bool(route_points) and len(completed_nodes) >= len(route_points)
        next_status = "completed" if all_confirmed else "running"
        execute(
            """
            UPDATE tasks
            SET completed_nodes = ?, trajectory = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (dumps(completed_nodes), dumps(trajectory), next_status, utc_now(), task_id),
        )

        fire_event_result = None
        detection_results: list[dict[str, Any]] = []
        snapshot_url = str(data.get("snapshot_url") or "").strip()
        seen_image_paths: set[str] = set()

        def run_node_detection(
            kind: str,
            image_path: Any,
            event_type: str | None,
            tags: list[str],
            features: dict[str, Any] | None = None,
        ) -> Optional[dict[str, Any]]:
            nonlocal fire_event_result
            image_value = str(image_path or "").strip()
            if not image_value or image_value in seen_image_paths:
                return None
            seen_image_paths.add(image_value)
            result = self.detect_event(
                {
                    "robot_id": task.get("robot_id") or settings.default_robot_id,
                    "event_type": event_type,
                    "confidence": 0.0,
                    "image_url": image_value,
                    "snapshot_url": image_value,
                    "image_tags": ["inspection", *tags],
                    "image_features": features or {},
                    "location": data.get("location"),
                    "network_online": True,
                    "payload": {
                        "source": "inspection_confirm",
                        "detection_kind": kind,
                        "task_id": task_id,
                        "node_id": node_id,
                        "sensor_summary": sensor_summary,
                    },
                }
            )
            detection_results.append(
                {"kind": kind, "image_path": image_value, "result": result}
            )
            if kind == "fire":
                fire_event_result = result
            return result

        if route_point:
            fire_mode = route_point.get("fire_detection_mode")
            if fire_mode == "image":
                run_node_detection(
                    "fire",
                    route_point.get("fire_image_path"),
                    "fire",
                    ["fire"],
                )
            elif fire_mode == "camera":
                run_node_detection("fire", snapshot_url, "fire", ["fire"])

            run_node_detection(
                "face",
                route_point.get("face_image_path"),
                "unauthorized_person",
                ["face", "person"],
                {"face_check_requested": True},
            )
            run_node_detection(
                "inspection",
                route_point.get("inspection_image_path"),
                None,
                ["inspection"],
            )
        elif snapshot_url:
            run_node_detection("inspection", snapshot_url, None, ["inspection"])

        self.log("inspection", f"task {task_id} confirmed node {node_id}, status {next_status}")
        response = {
            "task": self.get_task(task_id),
            "confirmed_node": node_id,
            "confirmed_count": len(completed_nodes),
            "total_nodes": len(route_points),
            "all_confirmed": all_confirmed,
            "detection_results": detection_results,
        }
        if fire_event_result is not None:
            response["fire_event_result"] = fire_event_result
        return response

    def handle_obstacle(self, task_id: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        trajectory = task["trajectory"]
        trajectory.extend(
            [
                {"time": utc_now(), "action": "decelerate"},
                {"time": utc_now(), "action": "stop"},
                {"time": utc_now(), "action": "detour"},
                {"time": utc_now(), "action": "resume_route"},
            ]
        )
        execute("UPDATE tasks SET trajectory = ?, updated_at = ? WHERE id = ?", (dumps(trajectory), utc_now(), task_id))
        self.log("inspection", f"任务 {task_id} 已完成避障并恢复路线")
        return {"task_id": task_id, "actions": ["decelerate", "stop", "detour", "resume_route"], "status": "running"}

    def handle_battery(self, task_id: str, battery: int) -> dict[str, Any]:
        task = self.get_task(task_id)
        if battery > settings.low_battery_threshold:
            return {"task_id": task_id, "battery": battery, "status": task["status"], "low_battery": False}
        trajectory = task["trajectory"]
        trajectory.append({"time": utc_now(), "action": "return_to_charge", "battery": battery})
        execute(
            """
            UPDATE tasks SET status = 'interrupted', trajectory = ?, updated_at = ?
            WHERE id = ?
            """,
            (dumps(trajectory), utc_now(), task_id),
        )
        self.log("device", f"任务 {task_id} 因低电量中断并自动返航", level="WARN")
        return {
            "task_id": task_id,
            "battery": battery,
            "status": "interrupted",
            "return_to": "charging_station",
            "interrupt_point_recorded": True,
        }

    def emergency_pause(self, task_id: str) -> dict[str, Any]:
        self.get_task(task_id)
        execute("UPDATE tasks SET status = 'paused', updated_at = ? WHERE id = ?", (utc_now(), task_id))
        self.log("inspection", f"任务 {task_id} 人工紧急暂停", level="WARN")
        return {"task_id": task_id, "status": "paused", "robot_action": "immediate_stop"}

    def known_face_ids(self) -> set[str]:
        try:
            rows = query("SELECT id FROM known_faces")
        except sqlite3.OperationalError as exc:
            if "known_faces" not in str(exc).lower():
                raise
            from app.db import init_db

            init_db()
            rows = query("SELECT id FROM known_faces")
        return {str(row["id"]).lower() for row in rows}

    def row_to_known_face(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "role": row.get("role"),
            "image_path": row.get("image_path"),
            "created_at": row["created_at"],
            "updated_at": row.get("updated_at") or row["created_at"],
        }

    def list_known_faces(self) -> list[dict[str, Any]]:
        try:
            rows = query(
                """
                SELECT id, name, role, image_path, created_at,
                       COALESCE(updated_at, created_at) AS updated_at
                FROM known_faces
                ORDER BY updated_at DESC, created_at DESC
                """
            )
        except sqlite3.OperationalError as exc:
            if "known_faces" not in str(exc).lower() and "image_path" not in str(exc).lower():
                raise
            from app.db import init_db

            init_db()
            rows = query(
                """
                SELECT id, name, role, image_path, created_at,
                       COALESCE(updated_at, created_at) AS updated_at
                FROM known_faces
                ORDER BY updated_at DESC, created_at DESC
                """
            )
        return [self.row_to_known_face(row) for row in rows]

    def get_known_face(self, face_id: str) -> dict[str, Any]:
        row = query_one(
            """
            SELECT id, name, role, image_path, created_at,
                   COALESCE(updated_at, created_at) AS updated_at
            FROM known_faces
            WHERE id = ?
            """,
            (face_id,),
        )
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="known face not found")
        return self.row_to_known_face(row)

    def known_face_references(self) -> list[dict[str, Any]]:
        references: list[dict[str, Any]] = []
        for face in self.list_known_faces():
            raw_path = str(face.get("image_path") or "").strip()
            if not raw_path:
                continue
            resolved_path = self.resolve_local_image_path(raw_path)
            references.append(
                {
                    "id": face["id"],
                    "name": face["name"],
                    "role": face.get("role"),
                    "image_path": str(resolved_path or raw_path),
                    "source_image_path": raw_path,
                }
            )
        return references

    def upsert_known_face(self, data: dict[str, Any]) -> dict[str, Any]:
        face_id = str(data.get("face_id") or data.get("id") or "").strip()
        if not face_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="face_id is required")

        existing = query_one("SELECT * FROM known_faces WHERE id = ?", (face_id,))
        now = utc_now()
        name_value = data.get("name") or data.get("label") or (
            existing.get("name") if existing else face_id
        )
        name = str(name_value).strip()
        role = data.get("role") if "role" in data else (existing.get("role") if existing else None)
        if "image_path" in data:
            image_path = str(data.get("image_path") or "").strip() or None
        else:
            image_path = existing.get("image_path") if existing else None

        execute(
            """
            INSERT INTO known_faces (id, name, role, image_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                role = excluded.role,
                image_path = excluded.image_path,
                updated_at = excluded.updated_at
            """,
            (
                face_id,
                name or face_id,
                role,
                image_path,
                existing.get("created_at") if existing else now,
                now,
            ),
        )
        self.log("face", f"known face {face_id} saved")
        return self.get_known_face(face_id)

    def delete_known_face(self, face_id: str) -> dict[str, str]:
        self.get_known_face(face_id)
        execute("DELETE FROM known_faces WHERE id = ?", (face_id,))
        self.log("face", f"known face {face_id} deleted", level="WARN")
        return {"id": face_id, "message": "deleted"}

    def extract_face_ids(self, features: dict[str, Any]) -> list[str]:
        raw_face_ids = (
            features.get("face_ids")
            or features.get("recognized_face_ids")
            or features.get("recognized_faces")
            or features.get("face_id")
            or features.get("recognized_face_id")
        )
        if raw_face_ids is None:
            return []
        if isinstance(raw_face_ids, str):
            return [raw_face_ids]
        if isinstance(raw_face_ids, (int, float)):
            return [str(raw_face_ids)]
        if isinstance(raw_face_ids, list):
            return [str(face_id) for face_id in raw_face_ids if face_id not in (None, "")]
        return []

    def resolve_local_image_path(self, raw_path: Any) -> Optional[Path]:
        if raw_path in (None, ""):
            return None
        value = str(raw_path).strip()
        if not value:
            return None
        if value.startswith(("http://", "https://", "data:")):
            return None
        if value.startswith("/snapshots/"):
            relative_name = Path(value.split("?", 1)[0].split("#", 1)[0]).name
            candidate = settings.snapshot_path / relative_name
            return candidate.resolve() if candidate.exists() and candidate.is_file() else None
        if value.startswith("file://"):
            parsed = urlparse(value)
            value = unquote(parsed.path or "")
            if len(value) >= 3 and value[0] == '/' and value[2] == ':':
                value = value[1:]

        candidate = Path(value).expanduser()
        candidates = [candidate]
        if not candidate.is_absolute():
            database_parent = settings.database_path.parent
            candidates.append((database_parent / candidate).resolve())
            candidates.append((Path.cwd() / candidate).resolve())

        for item in candidates:
            try:
                if item.exists() and item.is_file():
                    return item.resolve()
            except OSError:
                continue
        return None

    def enrich_detection_with_backend_image_analysis(
        self, data: dict[str, Any]
    ) -> dict[str, Any]:
        prepared = dict(data)
        features = dict(prepared.get("image_features") or {})
        payload = dict(prepared.get("payload") or {})
        analysis_meta = payload.get("backend_image_analysis")
        if isinstance(analysis_meta, dict) and analysis_meta.get("status") in {
            "completed",
            "skipped",
            "error",
        }:
            prepared["image_features"] = features
            prepared["payload"] = payload
            return prepared

        image_path = None
        for raw_path in (
            prepared.get("image_url"),
            prepared.get("snapshot_url"),
            payload.get("snapshot_path"),
            payload.get("image_path"),
        ):
            image_path = self.resolve_local_image_path(raw_path)
            if image_path is not None:
                break

        if image_path is None:
            payload["backend_image_analysis"] = {
                "status": "skipped",
                "reason": "local_image_unavailable",
            }
            prepared["image_features"] = features
            prepared["payload"] = payload
            return prepared

        reference_face_path = self.resolve_local_image_path(
            features.get("face_reference_path")
            or payload.get("face_reference_path")
            or payload.get("reference_face_path")
        )
        reference_faces = self.known_face_references()

        try:
            from app.services.image_detection import analyze_image_confidence

            analysis = analyze_image_confidence(
                image_path,
                reference_face_path=reference_face_path,
                reference_faces=reference_faces,
                face_match_threshold=settings.face_match_threshold,
            )
        except Exception as exc:
            payload["backend_image_analysis"] = {
                "status": "error",
                "image_path": str(image_path),
                "reason": str(exc),
            }
            self.log(
                "event",
                f"backend image analysis failed: {image_path} -> {exc}",
                level="WARN",
            )
            prepared["image_features"] = features
            prepared["payload"] = payload
            return prepared

        analysis_features = dict(analysis.get("image_features") or {})
        analysis_features["face_boxes"] = analysis.get("face_boxes") or []
        features.update(analysis_features)

        payload["backend_image_analysis"] = {
            "status": "completed",
            "image_path": analysis.get("image_path", str(image_path)),
            "fire_confidence": analysis.get("fire_confidence", 0.0),
            "face_confidence": analysis.get("face_confidence", 0.0),
            "face_count": analysis.get("face_count", 0),
            "face_whitelist_checked": bool(
                analysis_features.get("face_whitelist_checked")
            ),
            "face_whitelist_matched": bool(
                analysis_features.get("face_whitelist_matched")
            ),
            "face_whitelist_reference_count": len(reference_faces),
        }
        if analysis.get("face_boxes"):
            payload["backend_face_boxes"] = analysis["face_boxes"]

        prepared["image_features"] = features
        prepared["payload"] = payload
        if not prepared.get("image_url"):
            prepared["image_url"] = str(image_path)
        if not prepared.get("snapshot_url"):
            prepared["snapshot_url"] = str(image_path)
        return prepared

    def evaluate_person_face(self, tags: list[str], image_url: str, features: dict[str, Any]) -> dict[str, Any]:
        score = 0.0
        reasons: list[str] = []
        face_check_requested = bool(features.get("face_check_requested")) or (
            "face" in image_url
            or any("face" in tag or "person" in tag or "human" in tag for tag in tags)
        )
        face_count = int(features.get("face_count") or 0)
        for keyword in PERSON_KEYWORDS:
            keyword_value = str(keyword).lower()
            if keyword_value in image_url or any(keyword_value in tag for tag in tags):
                score += 0.30
                reasons.append(f"图像标签/路径命中 {keyword}")

        for key in PERSON_FEATURE_KEYS:
            value = features.get(key)
            if (
                key in {
                    "face_score",
                    "face_detected",
                    "unknown_face_score",
                    "unauthorized_face_score",
                }
                and bool(features.get("face_whitelist_checked"))
                and not face_check_requested
                and face_count <= 0
            ):
                continue
            if isinstance(value, bool) and value:
                score += 0.40
                reasons.append(f"特征 {key}=true")
            elif isinstance(value, (int, float)):
                normalized = max(0.0, min(float(value), 1.0))
                score += normalized * 0.55
                if normalized > 0:
                    reasons.append(f"特征 {key}={value}")

        face_ids = self.extract_face_ids(features)
        face_context_available = (
            face_check_requested
            or face_count > 0
            or bool(face_ids)
            or (bool(features.get("face_detected")) and not whitelist_checked)
        )
        whitelist_checked = bool(features.get("face_whitelist_checked"))
        whitelist_matched = bool(features.get("face_whitelist_matched"))
        whitelist_best_match = features.get("face_whitelist_best_match")
        if whitelist_checked and whitelist_matched and face_context_available:
            matched_ids = face_ids or (
                [str(whitelist_best_match.get("face_id"))]
                if isinstance(whitelist_best_match, dict)
                and whitelist_best_match.get("face_id")
                else []
            )
            return {
                "detected": True,
                "authorized": True,
                "score": min(max(score, 0.95), 0.99),
                "reasons": [*reasons, "face whitelist matched"],
                "face_ids": matched_ids,
            }
        if whitelist_checked and not whitelist_matched and face_context_available:
            best_score = 0.0
            if isinstance(whitelist_best_match, dict):
                best_score = float(whitelist_best_match.get("confidence") or 0.0)
            return {
                "detected": True,
                "authorized": False,
                "score": min(max(score, 0.95, best_score), 0.99),
                "reasons": [*reasons, "face whitelist not matched"],
                "face_ids": face_ids,
            }

        known_faces = self.known_face_ids()
        unknown_face_ids = [
            face_id for face_id in face_ids if face_id.lower() not in known_faces
        ]
        if unknown_face_ids:
            return {
                "detected": True,
                "authorized": False,
                "score": min(max(score, 0.95), 0.99),
                "reasons": [*reasons, f"未授权人脸 {', '.join(unknown_face_ids)}"],
                "face_ids": face_ids,
            }
        if face_ids:
            return {
                "detected": True,
                "authorized": True,
                "score": min(score, 0.99),
                "reasons": [*reasons, "人脸已在白名单数据库中"],
                "face_ids": face_ids,
            }
        if score > 0:
            return {
                "detected": True,
                "authorized": None,
                "score": min(score, 0.89),
                "reasons": [*reasons, "检测到人员但缺少可比对的人脸 ID"],
                "face_ids": [],
            }
        return {
            "detected": False,
            "authorized": None,
            "score": 0.0,
            "reasons": [],
            "face_ids": [],
        }

    def infer_event_from_image(self, data: dict[str, Any]) -> dict[str, Any]:
        tags = [str(tag).lower() for tag in data.get("image_tags") or []]
        image_url = str(data.get("image_url") or data.get("snapshot_url") or "").lower()
        features = data.get("image_features") or {}
        candidates: list[tuple[str, float, list[str]]] = []

        for event_type, rule in IMAGE_EVENT_RULES.items():
            score = 0.0
            reasons: list[str] = []
            for keyword in rule["keywords"]:
                keyword_value = str(keyword).lower()
                if keyword_value in image_url or any(keyword_value in tag for tag in tags):
                    score += 0.50 if event_type == "fire" else 0.35
                    reasons.append(f"图像标签/路径命中 {keyword}")

            for key in rule["feature_keys"]:
                value = features.get(key)
                if isinstance(value, bool) and value:
                    score += 0.60 if event_type == "fire" else 0.45
                    reasons.append(f"特征 {key}=true")
                elif isinstance(value, (int, float)):
                    normalized = max(0.0, min(float(value), 1.0))
                    score += normalized * (0.85 if event_type == "fire" else 0.65)
                    if normalized > 0:
                        reasons.append(f"特征 {key}={value}")

            if score > 0:
                candidates.append((event_type, min(score, 0.99), reasons))

        person_result = self.evaluate_person_face(tags, image_url, features)
        if person_result["detected"]:
            if person_result["authorized"] is False:
                candidates.append(
                    (
                        "unauthorized_person",
                        float(person_result["score"]),
                        list(person_result["reasons"]),
                    )
                )
            elif person_result["authorized"] is True:
                candidates.append(
                    (
                        "authorized_person",
                        float(person_result["score"]),
                        list(person_result["reasons"]),
                    )
                )
            else:
                candidates.append(
                    (
                        "person_face_required",
                        float(person_result["score"]),
                        list(person_result["reasons"]),
                    )
                )

        if data.get("event_type"):
            # 兼容硬件端已有粗分类输入，但最终类型仍由后端统一标准化和确认。
            event_type = self.normalize_event_type(data["event_type"])
            input_confidence = float(data.get("confidence") or 0.0)
            if event_type == "unauthorized_person" and not person_result["detected"]:
                candidates.append(
                    (
                        "person_face_required",
                        max(input_confidence, 0.5),
                        ["硬件端识别到人员，需要人脸数据库复核"],
                    )
                )
            elif event_type in SUPPORTED_EVENT_TYPES and event_type != "unauthorized_person":
                candidates.append((event_type, max(input_confidence, 0.5), ["硬件端粗分类输入"]))

        if not candidates:
            return {
                "event_type": "unknown",
                "confidence": 0.0,
                "reasons": ["未从图像标签、路径或特征中识别到火焰、烟雾、障碍、边界或未授权人员"],
            }

        event_type, confidence, reasons = sorted(
            candidates,
            key=lambda item: (EVENT_PRIORITY.get(item[0], 99), -item[1]),
        )[0]
        return {"event_type": event_type, "confidence": confidence, "reasons": reasons}

    def detect_event(self, data: dict[str, Any]) -> dict[str, Any]:
        data = self.enrich_detection_with_backend_image_analysis(data)
        inference = self.infer_event_from_image(data)
        event_type = inference["event_type"]
        confidence_candidates = [float(inference["confidence"])]
        if data.get("confidence") is not None:
            confidence_candidates.append(float(data["confidence"]))
        confidence = max(confidence_candidates)
        if event_type == "unknown":
            return {
                "confirmed": False,
                "status": "unrecognized",
                "message": "后端未识别到火焰、烟雾、障碍、边界或未授权人员",
                "inference": inference,
            }
        if event_type == "authorized_person":
            return {
                "confirmed": False,
                "status": "authorized_person",
                "message": "检测到人员，但人脸已在数据库中，不触发不可通行告警",
                "inference": inference,
            }
        if event_type == "person_face_required":
            return {
                "confirmed": False,
                "status": "face_required",
                "message": "检测到人员，但缺少可比对的人脸信息，需继续采样",
                "required_frames": settings.confirmation_frames,
                "inference": inference,
            }
        if confidence < settings.detection_confidence_threshold:
            return {
                "confirmed": False,
                "status": "sampling",
                "message": "识别置信度不足，进入连续采样确认，不触发告警",
                "required_frames": settings.confirmation_frames,
                "inference": inference,
            }

        report_status = "reported" if data.get("network_online", True) else "cached"
        event_id = self.new_id("event")
        now = utc_now()
        execute(
            """
            INSERT INTO events (
                id, robot_id, event_type, confidence, priority, status, report_status,
                location, orientation, snapshot_url, local_alert, voice_broadcast,
                sample_retained, payload, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                data.get("robot_id") or settings.default_robot_id,
                event_type,
                confidence,
                EVENT_PRIORITY[event_type],
                "unhandled",
                report_status,
                dumps(data.get("location")),
                dumps(data.get("orientation")),
                data.get("snapshot_url") or f"/snapshots/{event_id}.jpg",
                1,
                1,
                0,
                dumps({**(data.get("payload") or {}), "backend_inference": inference}),
                now,
                now,
            ),
        )
        self.log(
            "event",
            f"危险事件 {event_id} 已识别，类型 {event_type}，report={report_status}",
            level="WARN",
        )
        return {"confirmed": True, "event": self.get_event(event_id), "report_latency_seconds": 0, "inference": inference}

    def detect_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prepared_items = [
            self.enrich_detection_with_backend_image_analysis(item) for item in items
        ]
        ordered = sorted(
            prepared_items,
            key=lambda item: EVENT_PRIORITY.get(self.infer_event_from_image(item)["event_type"], 99),
        )
        return [self.detect_event(item) for item in ordered]

    def get_event(self, event_id: str) -> dict[str, Any]:
        row = query_one("SELECT * FROM events WHERE id = ?", (event_id,))
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="危险事件不存在")
        return self.row_to_event(row)

    def list_events(
        self,
        event_type: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if event_type:
            clauses.append("event_type = ?")
            params.append(self.normalize_event_type(event_type))
        if status_filter:
            clauses.append("status = ?")
            params.append(status_filter)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = query(f"SELECT * FROM events {where} ORDER BY priority ASC, created_at DESC", tuple(params))
        return [self.row_to_event(row) for row in rows]

    def flush_cached_events(self) -> dict[str, Any]:
        rows = query("SELECT id FROM events WHERE report_status = 'cached'")
        now = utc_now()
        for row in rows:
            execute("UPDATE events SET report_status = 'reported', updated_at = ? WHERE id = ?", (now, row["id"]))
        self.log("event", f"网络恢复，补发缓存危险事件 {len(rows)} 条")
        return {"flushed": len(rows), "report_status": "reported"}

    def dispose_event(self, event_id: str, data: dict[str, Any]) -> dict[str, Any]:
        event = self.get_event(event_id)
        action = data["action"]
        if action == "false_alarm":
            new_status = "false_alarm"
            sample_retained = 1
            result = data.get("result") or "误报已标记，纳入模型优化样本"
        elif action == "danger_retreat":
            new_status = "monitoring"
            sample_retained = int(event["sample_retained"])
            result = data.get("result") or "机器人后退至安全区域并持续监控"
        else:
            new_status = "handled" if action == "handled" else "processing"
            sample_retained = int(event["sample_retained"])
            result = data.get("result") or "指令执行成功"
        record_id = self.new_id("dispose")
        execute(
            """
            INSERT INTO disposal_records
                (id, event_id, action, executor, result, reason, robot_feedback, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                event_id,
                action,
                data.get("executor") or "operator",
                result,
                data.get("reason"),
                dumps({"accepted": True, "feedback": result}),
                utc_now(),
            ),
        )
        execute(
            """
            UPDATE events SET status = ?, sample_retained = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_status, sample_retained, utc_now(), event_id),
        )
        self.log("disposal", f"危险事件 {event_id} 已处置：{action}")
        return {"event": self.get_event(event_id), "record": self.get_disposal_record(record_id)}

    def get_disposal_record(self, record_id: str) -> dict[str, Any]:
        row = query_one("SELECT * FROM disposal_records WHERE id = ?", (record_id,))
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="处置记录不存在")
        row["robot_feedback"] = loads(row.get("robot_feedback"), {})
        return row

    def record_device_status(self, data: dict[str, Any]) -> dict[str, Any]:
        robot_id = self.normalize_robot_id(data.get("robot_id"))
        sensor_status = data.get("sensor_status") or {}
        abnormal_flags: list[str] = []
        mode = "main"
        if data["battery"] <= settings.low_battery_threshold:
            abnormal_flags.append("low_battery")
        if data["localization"] == "lost":
            abnormal_flags.append("localization_lost")
        broken_sensors = [name for name, value in sensor_status.items() if value in {"fault", "offline", "disconnected"}]
        if broken_sensors:
            abnormal_flags.append("sensor_fault")
            mode = "degraded"
        if not data.get("online", False):
            abnormal_flags.append("offline")
            mode = "disconnected"
        status_id = self.new_id("status")
        now = utc_now()
        execute(
            """
            INSERT INTO device_status (
                id, robot_id, battery, localization, sensor_status, cpu_usage,
                memory_usage, signal_strength, online, mode, abnormal_flags, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                status_id,
                robot_id,
                data["battery"],
                data["localization"],
                dumps(sensor_status),
                data["cpu_usage"],
                data["memory_usage"],
                data["signal_strength"],
                int(data.get("online", False)),
                mode,
                dumps(abnormal_flags),
                now,
            ),
        )
        if broken_sensors:
            self.log("device", f"传感器故障 {broken_sensors}，系统切换至降级模式", level="WARN")
        if data.get("online", False):
            self.redeliver_queued_tasks(robot_id)
        return self.row_to_device_status(query_one("SELECT * FROM device_status WHERE id = ?", (status_id,)))

    def redeliver_queued_tasks(self, robot_id: str) -> int:
        rows = query(
            "SELECT id FROM tasks WHERE robot_id = ? AND dispatch_status = 'queued'",
            (robot_id,),
        )
        for row in rows:
            execute(
                "UPDATE tasks SET dispatch_status = 'dispatched', updated_at = ? WHERE id = ?",
                (utc_now(), row["id"]),
            )
        if rows:
            self.log("task", f"机器人 {robot_id} 上线，补发待下发任务 {len(rows)} 个")
        return len(rows)

    def set_robot_online(self, robot_id: str, online: bool) -> dict[str, Any]:
        robot_id = self.normalize_robot_id(robot_id)
        latest = self.latest_device_status(robot_id)
        redelivered = len(
            query(
                "SELECT id FROM tasks WHERE robot_id = ? AND dispatch_status = 'queued'",
                (robot_id,),
            )
        ) if online else 0
        self.record_device_status(
            {
                "robot_id": robot_id,
                "battery": latest["battery"] if latest else 0,
                "localization": latest["localization"] if latest else "lost",
                "sensor_status": latest["sensor_status"] if latest else {},
                "cpu_usage": latest["cpu_usage"] if latest else 0.0,
                "memory_usage": latest["memory_usage"] if latest else 0.0,
                "signal_strength": latest["signal_strength"] if latest else 0,
                "online": online,
            }
        )
        robot = self.robot(robot_id)
        robot["redelivered_tasks"] = redelivered
        return robot

    def current_device_status(self) -> dict[str, Any]:
        return self.latest_device_status() or self.disconnected_device_status()

    def device_history(self, robot_id: Optional[str] = None) -> list[dict[str, Any]]:
        if robot_id:
            rows = query("SELECT * FROM device_status WHERE robot_id = ? ORDER BY created_at DESC", (robot_id,))
        else:
            rows = query("SELECT * FROM device_status ORDER BY created_at DESC")
        return [self.row_to_device_status(row) for row in rows]

    def maintenance_operation(self, data: dict[str, Any]) -> dict[str, Any]:
        version_before = settings.current_version
        if data.get("dangerous"):
            status_value = "blocked"
            detail = {"message": "维护保护机制已触发，禁止危险操作", **data.get("detail", {})}
            version_after = version_before
        elif data["operation"] in {"software_update", "algorithm_update"} and not data.get("package_checksum_valid", True):
            status_value = "rolled_back"
            detail = {"message": "更新包校验失败，已回滚至上一版本", **data.get("detail", {})}
            version_after = version_before
        else:
            status_value = "success"
            detail = {"message": "操作完成，自检通过", **data.get("detail", {})}
            version_after = data.get("target_version") or version_before
        record_id = self.new_id("maint")
        execute(
            """
            INSERT INTO maintenance_records (
                id, operation, operator, status, version_before, version_after, detail, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                data["operation"],
                data.get("operator") or "maintainer",
                status_value,
                version_before,
                version_after,
                dumps(detail),
                utc_now(),
            ),
        )
        self.log("maintenance", detail["message"], level="WARN" if status_value != "success" else "INFO", sensitive=True)
        return self.maintenance_record(record_id)

    def maintenance_record(self, record_id: str) -> dict[str, Any]:
        row = query_one("SELECT * FROM maintenance_records WHERE id = ?", (record_id,))
        if not row:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="维护记录不存在")
        row["detail"] = loads(row.get("detail"), {})
        return row

    def logs(self, include_sensitive: bool = True) -> list[dict[str, Any]]:
        if include_sensitive:
            rows = query("SELECT * FROM logs ORDER BY created_at DESC")
        else:
            rows = query("SELECT id, level, category, '***' AS message, sensitive, created_at FROM logs ORDER BY created_at DESC")
        return rows

    def query_data(self, data_type: str, role: str, filters: dict[str, Any]) -> dict[str, Any]:
        sensitive = data_type in SENSITIVE_DATA_TYPES
        if sensitive and role not in {"admin", "maintainer"}:
            return {
                "data_type": data_type,
                "permission": "limited",
                "message": "权限不足，敏感字段已隐藏，拒绝导出",
                "items": self.logs(include_sensitive=False) if data_type == "logs" else [],
            }
        if data_type in {"events", "danger_events", "危险事件"}:
            return {"data_type": "events", "permission": "full", "items": self.list_events(filters.get("type"), filters.get("status"))}
        if data_type in {"tasks", "inspection_records", "巡检记录"}:
            return {"data_type": "tasks", "permission": "full", "items": self.list_tasks(filters.get("status"))}
        if data_type in {"device_status", "设备状态"}:
            return {"data_type": "device_status", "permission": "full", "items": self.device_history(filters.get("robot_id"))}
        if data_type in {"disposal_records", "处置记录"}:
            rows = query("SELECT * FROM disposal_records ORDER BY created_at DESC")
            for row in rows:
                row["robot_feedback"] = loads(row.get("robot_feedback"), {})
            return {"data_type": "disposal_records", "permission": "full", "items": rows}
        if data_type in {"logs", "maintenance"}:
            return {"data_type": data_type, "permission": "full", "items": self.logs(include_sensitive=True)}
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的数据类型")

    def export_data(self, data_type: str, export_format: str, role: str, filters: dict[str, Any]) -> dict[str, Any]:
        result = self.query_data(data_type, role, filters)
        if result["permission"] != "full":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="权限不足，拒绝导出")
        return {
            "file_name": f"{result['data_type']}.{export_format}",
            "format": export_format,
            "rows": len(result["items"]),
            "download_url": f"/exports/{result['data_type']}.{export_format}",
            "items": result["items"],
        }


service = RobotSystemService()
