import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from src.clients.asyncpg_client import AsyncPGClient
from src.utils.async_ttl_cache import async_ttl_cache


class PGStore:
    def __init__(self, client: AsyncPGClient) -> None:
        """Initialize the store with a shared PostgreSQL client."""
        self._client = client

    async def init_schema(self) -> None:
        """Create database tables and indexes if they do not exist."""
        query = """
        CREATE TABLE IF NOT EXISTS events (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TIMESTAMPTZ NOT NULL,
            properties JSONB NOT NULL,
            user_traits JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_events_user_id_created_at
            ON events (user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_user_event_type_created_at
            ON events (user_id, event_type, created_at DESC);

        CREATE TABLE IF NOT EXISTS message_decisions (
            id BIGSERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            template_name TEXT NOT NULL,
            channel TEXT NOT NULL,
            decision_status TEXT NOT NULL,
            reason TEXT NOT NULL,
            suppression_reason TEXT,
            decided_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_user_id_created_at
            ON message_decisions (user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_decisions_template_decided_at
            ON message_decisions (user_id, template_name, decided_at DESC);
        """
        async with self._client.pool.acquire() as conn:
            await conn.execute(query)

    async def insert_event(
        self,
        *,
        user_id: str,
        event_type: str,
        event_timestamp: datetime,
        properties: dict[str, Any],
        user_traits: dict[str, Any],
    ) -> None:
        """Persist a single inbound event record."""
        query = """
        INSERT INTO events (user_id, event_type, event_timestamp, properties, user_traits)
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb)
        """
        properties_json = json.dumps(properties)
        user_traits_json = json.dumps(user_traits)
        async with self._client.pool.acquire() as conn:
            await conn.execute(
                query,
                user_id,
                event_type,
                event_timestamp,
                properties_json,
                user_traits_json,
            )

    async def get_latest_event(self, *, user_id: str, event_type: str) -> dict[str, Any] | None:
        """Return the most recent event for a user and event type."""
        query = """
        SELECT user_id, event_type, event_timestamp, properties, user_traits, created_at
        FROM events
        WHERE user_id = $1 AND event_type = $2
        ORDER BY event_timestamp DESC
        LIMIT 1
        """
        async with self._client.pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id, event_type)
        return dict(row) if row is not None else None

    @async_ttl_cache(3)
    async def get_recent_events(self, *, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent events for a user ordered by event time."""
        query = """
        SELECT user_id, event_type, event_timestamp, properties, user_traits, created_at
        FROM events
        WHERE user_id = $1
        ORDER BY event_timestamp DESC
        LIMIT $2
        """
        async with self._client.pool.acquire() as conn:
            rows: Sequence[Any] = await conn.fetch(query, user_id, limit)
        return [dict(row) for row in rows]

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
        """Persist a single message decision record."""
        query = """
        INSERT INTO message_decisions (
            user_id, template_name, channel, decision_status, reason, suppression_reason, decided_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        async with self._client.pool.acquire() as conn:
            await conn.execute(
                query,
                user_id,
                template_name,
                channel,
                decision_status,
                reason,
                suppression_reason,
                decided_at,
            )

    async def get_latest_sent_decision(
        self, *, user_id: str, template_name: str
    ) -> dict[str, Any] | None:
        """Return the latest sent decision for a user/template pair."""
        query = """
        SELECT user_id, template_name, channel, decision_status, reason, suppression_reason, decided_at, created_at
        FROM message_decisions
        WHERE user_id = $1 AND template_name = $2 AND decision_status = 'sent'
        ORDER BY decided_at DESC
        LIMIT 1
        """
        async with self._client.pool.acquire() as conn:
            row = await conn.fetchrow(query, user_id, template_name)
        return dict(row) if row is not None else None

    @async_ttl_cache(3)
    async def get_recent_decisions(self, *, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent decisions for a user ordered by decision time."""
        query = """
        SELECT user_id, template_name, channel, decision_status, reason, suppression_reason, decided_at, created_at
        FROM message_decisions
        WHERE user_id = $1
        ORDER BY decided_at DESC
        LIMIT $2
        """
        async with self._client.pool.acquire() as conn:
            rows: Sequence[Any] = await conn.fetch(query, user_id, limit)
        return [dict(row) for row in rows]
