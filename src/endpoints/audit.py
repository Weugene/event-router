from fastapi import APIRouter

from src.dependencies import logger_dependency, message_service_dependency
from src.schemas import UserAuditResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{user_id}", response_model=UserAuditResponse)
async def get_user_audit(
    user_id: str,
    service: message_service_dependency,
    logger: logger_dependency,
) -> UserAuditResponse:
    """Return recent events and message decisions for a user."""
    audit_data = await service.get_user_audit(user_id, logger)
    return UserAuditResponse(**audit_data)
