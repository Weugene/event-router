import asyncio

import pytest
from src.clients.asyncpg_client import AsyncPGClient


def test_connect_raises_clear_runtime_error_on_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _failing_create_pool(**_: object) -> None:
        raise OSError("Connection refused")

    monkeypatch.setattr("src.clients.asyncpg_client.asyncpg.create_pool", _failing_create_pool)

    client = AsyncPGClient()

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(client.connect())

    error_message = str(exc_info.value)
    assert "Could not connect to PostgreSQL" in error_message
    assert client._config.postgres_host in error_message
    assert str(client._config.postgres_port) in error_message
    assert client._config.postgres_db in error_message
    assert client._config.postgres_user in error_message

