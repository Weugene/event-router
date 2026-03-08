from fastapi import APIRouter, Query

from src.dependencies import logger_dependency, message_service_dependency
from src.schemas import UserAuditResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{user_id}", response_model=UserAuditResponse)
async def get_user_audit(
    user_id: str,
    service: message_service_dependency,
    logger: logger_dependency,
    limit: int = Query(default=50, ge=1, le=60),
) -> UserAuditResponse:
    """Return recent events and message decisions for a user."""
    audit_data = await service.get_user_audit(user_id=user_id, logger=logger, limit=limit)
    return UserAuditResponse(**audit_data)
