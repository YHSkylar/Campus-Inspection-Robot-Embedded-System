from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.models import BatchDetectionRequest, DetectionRequest, DisposeRequest
from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


@router.post("/upload-snapshot")
async def upload_snapshot(
    request: Request,
    filename: Optional[str] = None,
    robot_id: Optional[str] = None,
    task_id: Optional[str] = None,
    node_id: Optional[str] = None,
    kind: str = "snapshot",
) -> dict[str, object]:
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="empty snapshot body")
    prefix = "_".join(
        part.strip()
        for part in [kind, robot_id or "robot", task_id or "", node_id or ""]
        if part and part.strip()
    )
    return service.save_uploaded_snapshot(content, filename or "snapshot.jpg", prefix=prefix)


@router.post("/detect")
def detect_event(payload: DetectionRequest) -> dict[str, object]:
    return service.detect_event(payload.dict())


@router.post("/detect/batch")
def detect_batch(payload: BatchDetectionRequest) -> list[dict[str, object]]:
    return service.detect_batch([item.dict() for item in payload.events])


@router.get("")
def list_events(
    event_type: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict[str, object]]:
    return service.list_events(event_type, status)


@router.get("/{event_id}")
def get_event(event_id: str) -> dict[str, object]:
    return service.get_event(event_id)


@router.post("/flush-cache")
def flush_cache() -> dict[str, object]:
    return service.flush_cached_events()


@router.post("/{event_id}/dispose")
def dispose_event(
    event_id: str,
    payload: DisposeRequest,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "security"})
    return service.dispose_event(event_id, payload.dict())
