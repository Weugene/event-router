from typing import Annotated

from fastapi import Depends, Request

from src.services.message_router_service import MessageRouterService
from src.settings.build_logger import logger as base_logger
from src.app_types import AppLogger


def get_message_router_service(request: Request) -> MessageRouterService:
    """Return the request-scoped message router service instance."""
    return request.app.state.message_router_service


def get_request_logger(request: Request) -> AppLogger:
    """Return request-enriched logger set by middleware, or base logger as fallback."""
    request_logger = getattr(request.state, "logger", None)
    if request_logger is not None:
        return request_logger
    return base_logger


logger_dependency = Annotated[AppLogger, Depends(get_request_logger)]
message_service_dependency = Annotated[
    MessageRouterService, Depends(get_message_router_service)
]
