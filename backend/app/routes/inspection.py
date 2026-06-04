from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models import BatterySignalRequest, InspectionConfirmRequest, InspectionStartRequest
from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


@router.post("/start")
def start_inspection(
    payload: InspectionStartRequest,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "duty_manager", "security"})
    return service.start_inspection(payload.task_id)


@router.post("/{task_id}/obstacle")
def obstacle_branch(task_id: str) -> dict[str, object]:
    return service.handle_obstacle(task_id)


@router.post("/{task_id}/confirm")
def confirm_inspection_node(
    task_id: str,
    payload: InspectionConfirmRequest,
) -> dict[str, object]:
    return service.confirm_inspection_node(task_id, payload.dict())


@router.post("/{task_id}/battery")
def low_battery_branch(task_id: str, payload: BatterySignalRequest) -> dict[str, object]:
    return service.handle_battery(task_id, payload.battery)


@router.post("/{task_id}/emergency-pause")
def emergency_pause(
    task_id: str,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "duty_manager", "security"})
    return service.emergency_pause(task_id)
