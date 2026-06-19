from __future__ import annotations

from typing import Union

from fastapi import APIRouter

from app.config import settings
from app.services import service

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, Union[str, int]]:
    robot = service.robot(settings.default_robot_id)
    return {
        "status": "ok" if robot["status"] == "normal" else "abnormal",
        "app": settings.app_name,
        "status_refresh_seconds": settings.status_refresh_seconds,
        "alarm_report_deadline_seconds": settings.alarm_report_deadline_seconds,
    }
