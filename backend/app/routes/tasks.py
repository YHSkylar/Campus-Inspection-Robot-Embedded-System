from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.models import TaskActionRequest, TaskCreate, TaskDispatchRequest, TaskUpdate
from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


@router.post("")
def create_task(payload: TaskCreate, role: str = Depends(current_role)) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "duty_manager"})
    return service.create_task(payload.dict())


@router.get("")
def list_tasks(status: Optional[str] = None) -> list[dict[str, object]]:
    return service.list_tasks(status)


@router.get("/{task_id}")
def get_task(task_id: str) -> dict[str, object]:
    return service.get_task(task_id)


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    payload: TaskUpdate,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "duty_manager"})
    return service.update_task(task_id, payload.dict(exclude_unset=True))


@router.post("/{task_id}/action")
def task_action(
    task_id: str,
    payload: TaskActionRequest,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "duty_manager", "security"})
    return service.task_action(task_id, payload.action)


@router.post("/{task_id}/dispatch")
def dispatch_task(
    task_id: str,
    payload: TaskDispatchRequest,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "duty_manager"})
    return service.dispatch_task(task_id, payload.force)


@router.delete("/{task_id}")
def delete_task(task_id: str, role: str = Depends(current_role)) -> dict[str, str]:
    service.ensure_role(role, {"control_center", "duty_manager"})
    return service.delete_task(task_id)
