from fastapi import APIRouter, Depends

from src.dependencies import get_message_router_service
from src.schemas import EventIngestResponse, EventPayload
from src.services.message_router_service import MessageRouterService

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResponse)
async def ingest_event(
    payload: EventPayload,
    service: MessageRouterService = Depends(get_message_router_service),
) -> EventIngestResponse:
    """Validate, process, and acknowledge an incoming lifecycle event."""
    result = await service.process_event(payload)
    return EventIngestResponse(
        status="accepted",
        message=f"Event accepted. decisions={result['decision_count']}",
    )
