from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.models import BatchDetectionRequest, DetectionRequest, DisposeRequest
from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


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
