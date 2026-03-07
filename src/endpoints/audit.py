from fastapi import APIRouter, Depends

from src.dependencies import get_message_router_service
from src.schemas import UserAuditResponse
from src.services.message_router_service import MessageRouterService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{user_id}", response_model=UserAuditResponse)
async def get_user_audit(
    user_id: str,
    service: MessageRouterService = Depends(get_message_router_service),
) -> UserAuditResponse:
    audit_data = await service.get_user_audit(user_id)
    return UserAuditResponse(**audit_data)
