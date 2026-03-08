import logging
import pytest

from datetime import datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path
from typing import Any

from src.clients.email_notifier import EmailNotifier
from src.dependencies import get_message_router_service, get_request_logger
from src.endpoints.audit import router as audit_router
from src.endpoints.events import router as events_router
from src.clients.sms_notifier import SmsNotifier
from src.services.message_router_service import MessageRouterService
from src.services.rule_engine import RuleEngine


class InMemoryStore:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.decisions: list[dict[str, Any]] = []

    async def insert_event(
        self,
        *,
        user_id: str,
        event_type: str,
        event_timestamp: datetime,
        properties: dict[str, Any],
        user_traits: dict[str, Any],
    ) -> None:
        self.events.append(
            {
                "user_id": user_id,
                "event_type": event_type,
                "event_timestamp": event_timestamp,
                "properties": properties,
                "user_traits": user_traits,
                "created_at": datetime.now(tz=event_timestamp.tzinfo),
            }
        )

    async def get_latest_event(self, *, user_id: str, event_type: str) -> dict[str, Any] | None:
        matches = [
            event
            for event in self.events
            if event["user_id"] == user_id and event["event_type"] == event_type
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: item["event_timestamp"])

    async def insert_decision(
        self,
        *,
        user_id: str,
        template_name: str,
        channel: str,
        decision_status: str,
        reason: str,
        suppression_reason: str | None,
        decided_at: datetime,
    ) -> None:
        self.decisions.append(
            {
                "user_id": user_id,
                "template_name": template_name,
                "channel": channel,
                "decision_status": decision_status,
                "reason": reason,
                "suppression_reason": suppression_reason,
                "decided_at": decided_at,
                "created_at": datetime.now(tz=decided_at.tzinfo),
            }
        )

    async def get_latest_sent_decision(
        self, *, user_id: str, template_name: str
    ) -> dict[str, Any] | None:
        matches = [
            decision
            for decision in self.decisions
            if decision["user_id"] == user_id
            and decision["template_name"] == template_name
            and decision["decision_status"] == "sent"
        ]
        if not matches:
            return None
        return max(matches, key=lambda item: item["decided_at"])

    async def get_recent_events(self, *, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        matches = [event for event in self.events if event["user_id"] == user_id]
        return sorted(matches, key=lambda item: item["event_timestamp"], reverse=True)[:limit]

    async def get_recent_decisions(self, *, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        matches = [decision for decision in self.decisions if decision["user_id"] == user_id]
        return sorted(matches, key=lambda item: item["decided_at"], reverse=True)[:limit]


@pytest.fixture
def app_logger() -> logging.Logger:
    return logging.getLogger("event-router-tests")


@pytest.fixture
def rules_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "src" / "configs" / "rules.yaml")


@pytest.fixture
def in_memory_store() -> InMemoryStore:
    return InMemoryStore()


@pytest.fixture
def message_router_service(
    in_memory_store: InMemoryStore, rules_path: str, app_logger: logging.Logger
) -> MessageRouterService:
    rule_engine = RuleEngine(rules_file_path=rules_path, store=in_memory_store, logger=app_logger)
    return MessageRouterService(
        store=in_memory_store,
        rule_engine=rule_engine,
        email_notifier=EmailNotifier(),
        sms_notifier=SmsNotifier(),
    )


@pytest.fixture
def test_app(message_router_service) -> FastAPI:
    app = FastAPI()
    app.include_router(events_router)
    app.include_router(audit_router)
    app.dependency_overrides[get_message_router_service] = lambda: message_router_service
    app.dependency_overrides[get_request_logger] = lambda: logging.getLogger("event-router-tests")
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)
