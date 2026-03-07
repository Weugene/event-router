import asyncpg
from asyncpg.pool import Pool

from src.settings.configuration_singleton import get_config


class AsyncPGClient:
    def __init__(self) -> None:
        """Initialize client state and load database configuration."""
        self._pool: Pool | None = None
        self._config = get_config()

    async def connect(self) -> None:
        """Create the asyncpg pool if it is not initialized."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._config.postgres_dsn,
                min_size=self._config.postgres_min_pool_size,
                max_size=self._config.postgres_max_pool_size,
            )

    async def close(self) -> None:
        """Close the asyncpg pool if it is open."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> Pool:
        """Return the initialized connection pool."""
        if self._pool is None:
            raise RuntimeError("AsyncPG pool is not initialized. Call connect() first.")
        return self._pool
