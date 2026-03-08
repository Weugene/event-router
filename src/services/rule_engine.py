from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import yaml

from src.app_types import AppLogger
from src.clients.pg_store import PGStore
from src.schemas import EventPayload

ALLOWED_AST_NODES: tuple[type[ast.AST], ...] = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Attribute,
    ast.Constant,
    ast.Call,
    ast.keyword,
    ast.Eq,
    ast.NotEq,
    ast.Gt,
    ast.GtE,
    ast.Lt,
    ast.LtE,
)


@dataclass(slots=True)
class RuleAction:
    template_name: str
    channel: str
    reason: str


@dataclass(slots=True)
class RuleSuppression:
    type: str


@dataclass(slots=True)
class Rule:
    name: str
    description: str
    trigger_event: str
    conditions: list[str]
    action: RuleAction
    suppression: RuleSuppression


def _to_namespace(value: Any) -> Any:
    """Recursively convert dictionaries into namespaces for dot-access."""
    if isinstance(value, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_to_namespace(v) for v in value]
    return value


class RuleEngine:
    def __init__(self, rules_file_path: str, store: PGStore, logger: AppLogger) -> None:
        """Load rule definitions and prepare rule lookup by trigger event."""
        self._rules_file_path = rules_file_path
        self._store = store
        self.logger = logger
        self._rules_by_event: dict[str, list[Rule]] = self._load_rules()

    def get_rules_for_event(self, event_type: str) -> list[Rule]:
        """Return all rules configured for the given event type."""
        return self._rules_by_event.get(event_type, [])

    def _load_rules(self) -> dict[str, list[Rule]]:
        """Read and parse YAML rules into internal dataclass structures."""
        with open(self._rules_file_path, encoding="utf-8") as file:
            raw = yaml.safe_load(file) or {}

        rules_by_event: dict[str, list[Rule]] = {}
        for event_type, items in raw.items():
            parsed_rules: list[Rule] = []
            for item in items:
                parsed_rules.append(
                    Rule(
                        name=item["name"],
                        description=item["description"],
                        trigger_event=item["trigger_event"],
                        conditions=item.get("conditions", []),
                        action=RuleAction(**item["action"]),
                        suppression=RuleSuppression(**item["suppression"]),
                    )
                )
            rules_by_event[event_type] = parsed_rules
        self.logger.info(
            "Loaded rules configuration | events=%s rules=%s",
            len(rules_by_event),
            sum(len(rules) for rules in rules_by_event.values()),
        )
        return rules_by_event

    async def evaluate_rule(self, rule: Rule, event: EventPayload) -> bool:
        """Evaluate all conditions in a rule against the event payload."""
        for condition in rule.conditions:
            ok = await self._evaluate_condition(condition=condition, event=event)
            if not ok:
                return False
        return True

    async def _evaluate_condition(self, condition: str, event: EventPayload) -> bool:
        """Safely evaluate a single rule condition expression."""
        expression = condition.replace("$json.", "json.")
        node = ast.parse(expression, mode="eval")
        for item in ast.walk(node):
            if not isinstance(item, ALLOWED_AST_NODES):
                raise ValueError(f"Unsupported expression AST node: {type(item).__name__}")
            if isinstance(item, ast.Call):
                if not isinstance(item.func, ast.Name) or item.func.id != "event_within":
                    raise ValueError("Only event_within() call is allowed in conditions.")

        async def event_within(event_type: str, *, hours: int) -> bool:
            """Check whether a previous event occurred within the time window."""
            previous_event = await self._store.get_latest_event(
                user_id=event.user_id, event_type=event_type
            )
            if previous_event is None:
                return False
            previous_ts = previous_event["event_timestamp"]
            current_ts = event.event_timestamp
            if previous_ts.tzinfo is None:
                previous_ts = previous_ts.replace(tzinfo=UTC)
            if current_ts.tzinfo is None:
                current_ts = current_ts.replace(tzinfo=UTC)
            delta = current_ts.astimezone(UTC) - previous_ts.astimezone(UTC)
            return timedelta(0) <= delta <= timedelta(hours=hours)

        context = {
            "json": _to_namespace(event.model_dump()),
            "event_within": event_within,
            # Support both Python-style and YAML/JSON-style literals in rules.
            "True": True,
            "False": False,
            "None": None,
            "true": True,
            "false": False,
            "null": None,
        }
        result = eval(compile(node, "<condition>", "eval"), {"__builtins__": {}}, context)
        if hasattr(result, "__await__"):
            result = await result
        return bool(result)

    async def evaluate_suppression(
        self,
        *,
        user_id: str,
        template_name: str,
        suppression_type: str,
        event_timestamp: datetime,
    ) -> tuple[bool, str | None]:
        """Determine if a message should be suppressed by configured strategy."""
        if suppression_type == "none":
            return False, None

        latest = await self._store.get_latest_sent_decision(
            user_id=user_id, template_name=template_name
        )
        if latest is None:
            return False, None

        latest_sent_at: datetime = latest["decided_at"]
        latest_utc = (
            latest_sent_at.replace(tzinfo=UTC)
            if latest_sent_at.tzinfo is None
            else latest_sent_at.astimezone(UTC)
        )
        current_utc = (
            event_timestamp.replace(tzinfo=UTC)
            if event_timestamp.tzinfo is None
            else event_timestamp.astimezone(UTC)
        )

        if suppression_type == "once_ever":
            return True, f"already sent before at {latest_utc.isoformat()}"

        if suppression_type == "once_per_day" and latest_utc.date() == current_utc.date():
            return True, f"already sent today at {latest_utc.isoformat()}"

        return False, None
