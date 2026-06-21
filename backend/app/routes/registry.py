from __future__ import annotations

from fastapi import APIRouter

from app.services import service

router = APIRouter()


@router.get("")
def route_registry() -> dict[str, object]:
    routes = service.list_routes()
    return {"count": len(routes), "routes": routes}
