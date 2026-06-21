from fastapi import APIRouter

from . import auth, devices, events, health, inspection, maintenance, query, registry, tasks

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(registry.router, prefix="/routes", tags=["routes"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(inspection.router, prefix="/inspection", tags=["inspection"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
