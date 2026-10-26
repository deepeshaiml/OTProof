from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    role: str
    actor: str


def current_principal(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    role = get_settings().configured_tokens.get(credentials.credentials)
    if role not in {"engineer", "reviewer", "approver", "admin"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token")
    return Principal(role=role, actor=f"{role}:demo-user")


def require_roles(*roles: str):
    def check(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles and principal.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Role not authorized for this action"
            )
        return principal

    return check
