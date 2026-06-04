from __future__ import annotations

from secrets import token_urlsafe
from typing import Optional

from fastapi import Header, HTTPException, status

from app.db import query_one


TOKENS: dict[str, dict[str, str]] = {}


def create_token(user: dict[str, str]) -> str:
    token = token_urlsafe(24)
    TOKENS[token] = {"username": user["username"], "role": user["role"]}
    return token


def current_role(
    authorization: Optional[str] = Header(default=None),
    x_role: Optional[str] = Header(default=None),
) -> str:
    if x_role:
        return x_role
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token in TOKENS:
            return TOKENS[token]["role"]
    return "security"


def authenticate(username: str, password: str) -> dict[str, str]:
    user = query_one(
        "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
        (username, password),
    )
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    return user
