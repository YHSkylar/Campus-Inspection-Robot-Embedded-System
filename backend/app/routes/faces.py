from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.models import KnownFaceRequest
from app.routes.dependencies import current_role
from app.services import service

router = APIRouter()


@router.get("")
def list_faces() -> list[dict[str, object]]:
    return service.list_known_faces()


@router.post("")
def upsert_face(
    payload: KnownFaceRequest,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "security", "maintainer"})
    return service.upsert_known_face(payload.dict())


@router.post("/upload")
async def upload_face(
    request: Request,
    face_id: str,
    name: Optional[str] = None,
    role_name: Optional[str] = None,
    filename: Optional[str] = None,
    role: str = Depends(current_role),
) -> dict[str, object]:
    service.ensure_role(role, {"control_center", "security", "maintainer"})
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="empty face image body")

    saved = service.save_uploaded_snapshot(
        content,
        filename or f"{face_id}.jpg",
        prefix=f"face_{face_id}",
    )
    face = service.upsert_known_face(
        {
            "face_id": face_id,
            "name": name or face_id,
            "role": role_name,
            "image_path": saved["local_path"],
        }
    )
    return {"face": face, "upload": saved}


@router.delete("/{face_id}")
def delete_face(
    face_id: str,
    role: str = Depends(current_role),
) -> dict[str, str]:
    service.ensure_role(role, {"control_center", "security", "maintainer"})
    return service.delete_known_face(face_id)
