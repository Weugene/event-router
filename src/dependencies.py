from fastapi import Request

from src.services.message_router_service import MessageRouterService


def get_message_router_service(request: Request) -> MessageRouterService:
    """Return the request-scoped message router service instance."""
    return request.app.state.message_router_service
