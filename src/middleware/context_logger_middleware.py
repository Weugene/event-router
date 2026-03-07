import logging
from logging import LoggerAdapter
from time import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.middleware.tracer import set_trace_id


class ContextLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger: logging.Logger | None = None) -> None:
        """Configure context logging middleware with a base logger."""
        super().__init__(app)
        self._logger = logger or logging.getLogger("event-router")

    async def dispatch(self, request: Request, call_next):
        """Attach request context to logs and emit start/end request entries."""
        start_time = time()
        request.scope["timeline"] = start_time
        request.scope.setdefault("logref", str(uuid4()))

        incoming_trace_id = request.headers.get("x-trace-id")
        trace_id = set_trace_id(incoming_trace_id)
        request.state.trace_id = trace_id

        context: dict[str, object] = {
            "trace_id": trace_id,
            "endpoint": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params),
            "request_info": {},
            "logref": request.scope["logref"],
            "timeline": start_time,
        }

        # Keep the most useful request metadata available in each log entry.
        request_info = context["request_info"]
        if isinstance(request_info, dict):
            for key in ["client", "server", "user-agent", "x-request-id", "x-trace-id", "x-user"]:
                if key in request.headers:
                    request_info[key] = request.headers[key]

            if request.client is not None:
                request_info["client_host"] = request.client.host
                request_info["client_port"] = request.client.port

        context_logger = LoggerAdapter(self._logger, context)
        request.state.logger = context_logger
        request.scope["logger"] = context_logger

        context_logger.info("Start request")
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        context_logger.info(
            "End request | status_code=%s total_duration_ms=%s",
            response.status_code,
            int((time() - start_time) * 1000),
        )
        return response
