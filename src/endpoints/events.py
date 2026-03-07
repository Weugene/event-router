from fastapi import APIRouter

from src.dependencies import logger_dependency, message_service_dependency
from src.schemas import EventIngestResponse, EventPayload, NotificationOutcome

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResponse)
async def ingest_event(
    payload: EventPayload,
    service: message_service_dependency,
    logger: logger_dependency,
) -> EventIngestResponse:
    """Validate, process, and acknowledge an incoming lifecycle event."""
    result = await service.process_event(payload, logger)
    notifications = [
        NotificationOutcome(
            template_name=item["template_name"],
            channel=item["channel"],
            status="applied" if item["status"] == "sent" else "suppressed",
            reason=item["reason"],
            suppression_reason=item["suppression_reason"],
        )
        for item in result["decisions"]
    ]
    applied_count = sum(1 for item in notifications if item.status == "applied")
    suppressed_count = sum(1 for item in notifications if item.status == "suppressed")
    return EventIngestResponse(
        status="accepted",
        message=(
            f"Event accepted. notifications={len(notifications)} "
            f"applied={applied_count} suppressed={suppressed_count}"
        ),
        notifications=notifications,
    )
