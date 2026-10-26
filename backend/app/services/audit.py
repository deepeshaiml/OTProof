from typing import Any

from sqlalchemy.orm import Session

from app.core.auth import Principal
from app.models.entities import AuditEvent


def record(
    db: Session,
    principal: Principal,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor=principal.actor,
            actor_role=principal.role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
    )
