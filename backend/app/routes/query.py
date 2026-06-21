from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


@router.get("")
def query_data(
    data_type: str,
    type: Optional[str] = None,
    status: Optional[str] = None,
    robot_id: Optional[str] = None,
    role: str = Depends(current_role),
) -> dict[str, object]:
    return service.query_data(
        data_type,
        role,
        {"type": type, "status": status, "robot_id": robot_id},
    )


@router.get("/export")
def export_data(
    data_type: str,
    export_format: str = "xlsx",
    type: Optional[str] = None,
    status: Optional[str] = None,
    robot_id: Optional[str] = None,
    role: str = Depends(current_role),
) -> dict[str, object]:
    return service.export_data(
        data_type,
        export_format,
        role,
        {"type": type, "status": status, "robot_id": robot_id},
    )
