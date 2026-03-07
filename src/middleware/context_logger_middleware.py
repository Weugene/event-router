from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.middleware.tracer import set_trace_id


class ContextLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_trace_id = request.headers.get("x-trace-id")
        trace_id = set_trace_id(incoming_trace_id)
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["x-trace-id"] = trace_id
        return response
