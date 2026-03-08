from datetime import UTC, datetime
from typing import Any

from src.clients.email_notifier import EmailNotifier
from src.clients.pg_store import PGStore
from src.clients.sms_notifier import SmsNotifier
from src.schemas import EventPayload
from src.services.rule_engine import RuleEngine
from src.app_types import AppLogger


class MessageRouterService:
    def __init__(
        self,
        *,
        store: PGStore,
        rule_engine: RuleEngine,
        email_notifier: EmailNotifier,
        sms_notifier: SmsNotifier,
    ) -> None:
        """Initialize service dependencies for event processing and notifications."""
        self._store = store
        self._rule_engine = rule_engine
        self._email_notifier = email_notifier
        self._sms_notifier = sms_notifier

    async def process_event(
        self,
        payload: EventPayload,
        logger: AppLogger,
    ) -> dict[str, Any]:
        """Persist an event, evaluate rules, and record resulting decisions."""
        event_timestamp_utc = self._to_utc(payload.event_timestamp)
        await self._store.insert_event(
            user_id=payload.user_id,
            event_type=payload.event_type,
            event_timestamp=event_timestamp_utc,
            properties=payload.properties.model_dump(),
            user_traits=payload.user_traits.model_dump(),
        )

        decisions: list[dict[str, Any]] = []
        rules = self._rule_engine.get_rules_for_event(payload.event_type)
        for rule in rules:
            is_match = await self._rule_engine.evaluate_rule(rule, payload)
            if not is_match:
                logger.info(
                    "Rule not matched | user_id=%s event_type=%s rule_name=%s",
                    payload.user_id,
                    payload.event_type,
                    rule.name,
                )
                continue

            is_suppressed, suppression_reason = await self._rule_engine.evaluate_suppression(
                user_id=payload.user_id,
                template_name=rule.action.template_name,
                suppression_type=rule.suppression.type,
                event_timestamp=event_timestamp_utc,
            )

            decision_status = "suppressed" if is_suppressed else "sent"
            if not is_suppressed:
                logger.info(
                    "Sending notification | user_id=%s event_type=%s rule_name=%s",
                    payload.user_id,
                    payload.event_type,
                    rule.name,
                )
                await self._send_stub(
                    user_id=payload.user_id,
                    template_name=rule.action.template_name,
                    channel=rule.action.channel,
                    reason=rule.action.reason,
                    logger=logger,
                )

            await self._store.insert_decision(
                user_id=payload.user_id,
                template_name=rule.action.template_name,
                channel=rule.action.channel,
                decision_status=decision_status,
                reason=rule.action.reason,
                suppression_reason=suppression_reason,
                decided_at=event_timestamp_utc,
            )
            decisions.append(
                {
                    "template_name": rule.action.template_name,
                    "channel": rule.action.channel,
                    "status": decision_status,
                    "reason": rule.action.reason,
                    "suppression_reason": suppression_reason,
                }
            )

        logger.info(
            "Event processed | user_id=%s event_type=%s decisions=%s",
            payload.user_id,
            payload.event_type,
            len(decisions),
        )
        return {"decision_count": len(decisions), "decisions": decisions}

    async def get_user_audit(
        self,
        user_id: str,
        logger: AppLogger,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Fetch recent events and decisions for audit output."""
        events = await self._store.get_recent_events(user_id=user_id, limit=limit)
        decisions = await self._store.get_recent_decisions(user_id=user_id, limit=limit)
        logger.info(
            "User audit requested | user_id=%s limit=%s events=%s decisions=%s",
            user_id,
            limit,
            len(events),
            len(decisions),
        )
        return {
            "user_id": user_id,
            "recent_events": events,
            "decisions": decisions,
        }

    async def _send_stub(
        self,
        *,
        user_id: str,
        template_name: str,
        channel: str,
        reason: str,
        logger: AppLogger,
    ) -> None:
        """Dispatch a stub notification to the selected channel."""
        if channel == "email":
            await self._email_notifier.send(
                user_id=user_id, template_name=template_name, reason=reason
            )
            return
        if channel == "sms":
            await self._sms_notifier.send(
                user_id=user_id, template_name=template_name, reason=reason
            )
            return
        if channel == "internal_alert":
            logger.warning(
                "Stub internal alert | user_id=%s template=%s reason=%s",
                user_id,
                template_name,
                reason,
            )
            return
        raise ValueError(f"Unsupported channel: {channel}")

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        """Normalize datetimes to UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
