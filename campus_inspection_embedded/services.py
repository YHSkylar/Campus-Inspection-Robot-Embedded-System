from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib import error, request

from .interfaces import ControlCenterClient, MotionController
from .models import AbnormalEvent, ActionResult, DisposalRecord
from .repository import SQLiteRepository


class JsonlControlCenterClient(ControlCenterClient):
    def __init__(self, output_path: str | Path) -> None:
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.available = True

    def report_event(self, event: AbnormalEvent) -> ActionResult:
        if not self.available:
            return ActionResult(ok=False, message="control center unavailable")
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_payload(), ensure_ascii=False) + "\n")
        return ActionResult(ok=True, message="reported")


class HttpControlCenterClient(ControlCenterClient):
    def __init__(self, endpoint: str, token: str = "") -> None:
        self.endpoint = endpoint
        self.token = token

    def report_event(self, event: AbnormalEvent) -> ActionResult:
        payload = json.dumps(event.to_payload(), ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = request.Request(self.endpoint, data=payload, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=3) as response:
                return ActionResult(ok=200 <= response.status < 300, message=str(response.status))
        except error.URLError as exc:
            return ActionResult(ok=False, message=str(exc))


class SimpleMotionController(MotionController):
    def __init__(self) -> None:
        self.executed_actions: list[dict[str, str | float | int | None]] = []

    def leave_danger_area(self, event: AbnormalEvent, retreat_distance_m: float) -> ActionResult:
        self.executed_actions.append(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "retreat_distance_m": retreat_distance_m,
            }
        )
        return ActionResult(ok=True, message=f"retreated {retreat_distance_m:.1f}m")


class EventReporter:
    def __init__(self, repository: SQLiteRepository, client: ControlCenterClient) -> None:
        self.repository = repository
        self.client = client

    def report_or_cache(self, event: AbnormalEvent) -> ActionResult:
        result = self.client.report_event(event)
        if result.ok and event.event_id is not None:
            self.repository.update_event_reported(event.event_id, True)
        return result

    def flush_pending(self) -> list[ActionResult]:
        results: list[ActionResult] = []
        for event in self.repository.list_unreported_events():
            result = self.client.report_event(event)
            results.append(result)
            if result.ok and event.event_id is not None:
                self.repository.update_event_reported(event.event_id, True)
        return results


class ResponseService:
    def __init__(
        self,
        repository: SQLiteRepository,
        motion_controller: MotionController,
        retreat_distance_m: float,
        handler_id: int,
    ) -> None:
        self.repository = repository
        self.motion_controller = motion_controller
        self.retreat_distance_m = retreat_distance_m
        self.handler_id = handler_id

    def execute_report_and_leave(self, event: AbnormalEvent) -> ActionResult:
        result = self.motion_controller.leave_danger_area(event, self.retreat_distance_m)
        if event.event_id is not None:
            self.repository.update_event_status(event.event_id, "processing")
            self.repository.save_disposal_record(
                DisposalRecord(
                    event_id=event.event_id,
                    handler_id=self.handler_id,
                    action="leave",
                    action_time=datetime.now(),
                    remark=result.message,
                )
            )
        return result
