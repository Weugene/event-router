import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_504_GATEWAY_TIMEOUT


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_seconds: int = 10):
        """Create middleware that enforces a request timeout."""
        super().__init__(app)
        self.timeout_seconds = timeout_seconds

    async def dispatch(self, request: Request, call_next):
        """Abort long-running requests with a 504 response."""
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout_seconds)
        except TimeoutError:
            return JSONResponse(
                status_code=HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": "Request timeout"},
            )
