from fastapi import Request

from src.services.message_router_service import MessageRouterService


def get_message_router_service(request: Request) -> MessageRouterService:
    return request.app.state.message_router_service
