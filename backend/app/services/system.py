from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
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
    "fire": "fire",
    "烟雾": "smoke",
    "smoke": "smoke",
    "非法入侵": "intrusion",
    "入侵": "intrusion",
    "人员入侵": "intrusion",
    "intrusion": "intrusion",
    "越界停留": "overstay",
    "overstay": "overstay",
    "漏电": "electric_leakage",
    "漏电风险": "electric_leakage",
    "electric_leakage": "electric_leakage",
}

EVENT_PRIORITY = {
    "fire": 1,
    "smoke": 2,
    "intrusion": 3,
    "overstay": 4,
    "electric_leakage": 5,
}

IMAGE_EVENT_RULES = {
    "fire": {
        "keywords": {"fire", "flame", "火", "火焰", "火警"},
        "feature_keys": {"flame_score", "temperature_high", "red_area_ratio"},
    },
    "smoke": {
        "keywords": {"smoke", "烟", "烟雾", "灰雾"},
        "feature_keys": {"smoke_score", "gray_area_ratio", "haze_density"},
    },
    "intrusion": {
        "keywords": {"person", "human", "intrusion", "非法入侵", "人员", "闯入"},
        "feature_keys": {"person_score", "human_count", "restricted_area_overlap"},
    },
    "overstay": {
        "keywords": {"overstay", "loitering", "越界停留", "滞留"},
        "feature_keys": {"stay_seconds", "boundary_overlap"},
    },
    "electric_leakage": {
        "keywords": {"leakage", "electric", "spark", "漏电", "电火花"},
        "feature_keys": {"leakage_score", "current_anomaly", "spark_score"},
    },
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
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="危险事件类型仅支持火警、烟雾、非法入侵、越界停留、漏电",
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

    def robot(self, robot_id: str) -> dict[str, Any]:
        robot = query_one("SELECT * FROM robots WHERE id = ?", (robot_id,))
        if not robot:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="机器人不存在")
        robot["online"] = bool(robot["online"])
        robot["location"] = loads(robot.get("location"), None)
        return robot

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
        conflict_policy = data.get("conflict_policy", "reject")
        conflicts = query(
            """
            SELECT * FROM tasks
            WHERE robot_id = ? AND status IN ('pending', 'running', 'paused')
            """,
            (robot_id,),
        )
        if conflicts and conflict_policy == "reject":
            raise HTTPException(status.HTTP_409_CONFLICT, detail="存在任务冲突")
        if conflicts and conflict_policy == "cover":
            execute(
                """
                UPDATE tasks SET status = 'cancelled', updated_at = ?
                WHERE robot_id = ? AND status IN ('pending', 'running', 'paused')
                """,
                (utc_now(), robot_id),
            )

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
                merged.get("conflict_policy", "reject"),
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
        if action == "start":
            execute(
                "UPDATE robots SET status = 'inspecting', updated_at = ? WHERE id = ?",
                (utc_now(), task["robot_id"]),
            )
        if action in {"stop", "complete"}:
            execute(
                "UPDATE robots SET status = 'idle', updated_at = ? WHERE id = ?",
                (utc_now(), task["robot_id"]),
            )
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
        if task["status"] not in {"running", "paused"}:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="只有运行中或暂停中的任务可确认巡检点")

        route_points = task["route_points"]
        node_id = data["node_id"]
        valid_node_ids = {str(point.get("id") or point.get("node_id") or index + 1) for index, point in enumerate(route_points)}
        if route_points and node_id not in valid_node_ids:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="巡检点不属于当前任务路线")

        completed_nodes = task["completed_nodes"]
        if node_id not in completed_nodes:
            completed_nodes.append(node_id)

        trajectory = task["trajectory"]
        trajectory.append(
            {
                "time": utc_now(),
                "action": "node_confirmed",
                "node_id": node_id,
                "location": data.get("location"),
                "snapshot_url": data.get("snapshot_url"),
                "sensor_summary": data.get("sensor_summary") or {},
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
        if all_confirmed:
            execute(
                "UPDATE robots SET status = 'returning_to_standby', updated_at = ? WHERE id = ?",
                (utc_now(), task["robot_id"]),
            )
        self.log("inspection", f"任务 {task_id} 确认巡检点 {node_id}，状态 {next_status}")
        return {
            "task": self.get_task(task_id),
            "confirmed_node": node_id,
            "confirmed_count": len(completed_nodes),
            "total_nodes": len(route_points),
            "all_confirmed": all_confirmed,
        }

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
        execute(
            "UPDATE robots SET battery = ?, status = 'returning_to_charge', updated_at = ? WHERE id = ?",
            (battery, utc_now(), task["robot_id"]),
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
        task = self.get_task(task_id)
        execute("UPDATE tasks SET status = 'paused', updated_at = ? WHERE id = ?", (utc_now(), task_id))
        execute("UPDATE robots SET status = 'emergency_paused', updated_at = ? WHERE id = ?", (utc_now(), task["robot_id"]))
        self.log("inspection", f"任务 {task_id} 人工紧急暂停", level="WARN")
        return {"task_id": task_id, "status": "paused", "robot_action": "immediate_stop"}

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
                    score += 0.35
                    reasons.append(f"图像标签/路径命中 {keyword}")

            for key in rule["feature_keys"]:
                value = features.get(key)
                if isinstance(value, bool) and value:
                    score += 0.45
                    reasons.append(f"特征 {key}=true")
                elif isinstance(value, (int, float)):
                    normalized = max(0.0, min(float(value), 1.0))
                    score += normalized * 0.65
                    if normalized > 0:
                        reasons.append(f"特征 {key}={value}")

            if score > 0:
                candidates.append((event_type, min(score, 0.99), reasons))

        if data.get("event_type"):
            # 兼容硬件端已有粗分类输入，但最终类型仍由后端统一标准化和确认。
            event_type = self.normalize_event_type(data["event_type"])
            input_confidence = float(data.get("confidence") or 0.0)
            candidates.append((event_type, max(input_confidence, 0.5), ["硬件端粗分类输入"]))

        if not candidates:
            return {
                "event_type": "unknown",
                "confidence": 0.0,
                "reasons": ["未从图像标签、路径或特征中识别到危险类型"],
            }

        event_type, confidence, reasons = sorted(
            candidates,
            key=lambda item: (-item[1], EVENT_PRIORITY.get(item[0], 99)),
        )[0]
        return {"event_type": event_type, "confidence": confidence, "reasons": reasons}

    def detect_event(self, data: dict[str, Any]) -> dict[str, Any]:
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
                "message": "后端未识别到火警、烟雾、入侵、越界停留或漏电风险",
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
        ordered = sorted(
            items,
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
        robot_id = data.get("robot_id") or settings.default_robot_id
        self.robot(robot_id)
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
        if not data.get("online", True):
            abnormal_flags.append("offline")
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
                int(data.get("online", True)),
                mode,
                dumps(abnormal_flags),
                now,
            ),
        )
        execute(
            """
            UPDATE robots
            SET online = ?, mode = ?, battery = ?, location = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                int(data.get("online", True)),
                mode,
                data["battery"],
                dumps(data.get("location")),
                now,
                robot_id,
            ),
        )
        if broken_sensors:
            self.log("device", f"传感器故障 {broken_sensors}，系统切换至降级模式", level="WARN")
        if data.get("online", True):
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
        self.robot(robot_id)
        execute(
            "UPDATE robots SET online = ?, updated_at = ? WHERE id = ?",
            (int(online), utc_now(), robot_id),
        )
        redelivered = self.redeliver_queued_tasks(robot_id) if online else 0
        robot = self.robot(robot_id)
        robot["redelivered_tasks"] = redelivered
        return robot

    def current_device_status(self) -> Optional[dict[str, Any]]:
        row = query_one("SELECT * FROM device_status ORDER BY created_at DESC LIMIT 1")
        return self.row_to_device_status(row) if row else None

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
