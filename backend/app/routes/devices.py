from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from app.models import DeviceStatusRequest
from app.services import service

router = APIRouter()


@router.post("/status")
def report_status(payload: DeviceStatusRequest) -> dict[str, object]:
    return service.record_device_status(payload.dict())


@router.get("/status/current")
def current_status() -> dict[str, object]:
    return service.current_device_status()


@router.get("/status/history")
def status_history(robot_id: Optional[str] = None) -> list[dict[str, object]]:
    return service.device_history(robot_id)
