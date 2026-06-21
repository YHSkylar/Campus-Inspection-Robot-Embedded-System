from fastapi import APIRouter

from app.models import LoginRequest
from app.routes.dependencies import authenticate, create_token

router = APIRouter()


@router.post("/login")
def login(payload: LoginRequest) -> dict[str, str]:
    user = authenticate(payload.username, payload.password)
    token = create_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }
