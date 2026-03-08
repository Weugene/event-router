from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.clients.asyncpg_client import AsyncPGClient
from src.clients.email_notifier import EmailNotifier
from src.clients.pg_store import PGStore
from src.clients.sms_notifier import SmsNotifier
from src.endpoints.audit import router as audit_router
from src.endpoints.events import router as events_router
from src.middleware.context_logger_middleware import ContextLoggerMiddleware
from src.middleware.timeout import TimeoutMiddleware
from src.schemas import HealthResponse
from src.services.message_router_service import MessageRouterService
from src.services.rule_engine import RuleEngine
from src.settings.build_logger import logger
from src.settings.configuration_singleton import get_config

config = get_config()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and tear down application dependencies."""
    pg_client = AsyncPGClient()
    await pg_client.connect()
    logger.info("Connected to PostgreSQL")

    store = PGStore(pg_client)
    await store.init_schema()
    logger.info("Initialized PostgreSQL schema")

    rules_path = str(Path(__file__).resolve().parent / "configs" / "rules.yaml")
    rule_engine = RuleEngine(rules_file_path=rules_path, store=store, logger=logger)
    logger.info("Initialized rule engine")

    app.state.message_router_service = MessageRouterService(
        store=store,
        rule_engine=rule_engine,
        email_notifier=EmailNotifier(),
        sms_notifier=SmsNotifier(),
    )
    logger.info("Initialized message router service")
    yield
    await pg_client.close()
    logger.info("Closed PostgreSQL connection")


app = FastAPI(title=config.app_name, lifespan=lifespan)

app.add_middleware(TimeoutMiddleware, timeout_seconds=config.app_timeout_seconds)
app.add_middleware(ContextLoggerMiddleware, logger=logger)

app.include_router(events_router)
app.include_router(audit_router)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report service health status."""
    return HealthResponse(status="ok")
