from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models import MaintenanceRequest
from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


@router.post("/operate")
def operate(
    payload: MaintenanceRequest,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"maintainer"})
    return service.maintenance_operation(payload.dict())


@router.get("/logs")
def logs(role: str = Depends(current_role)) -> list[dict[str, object]]:
    return service.logs(include_sensitive=role in {"admin", "maintainer"})
