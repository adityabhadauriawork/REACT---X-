"""
SIH26162 — Request Correlation ID Middleware & Logging Filter
Provides lightweight asynchronous request correlation tracking across FastAPI routes.
"""
import uuid
import logging
import contextvars
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Asynchronous Context Variable for correlation tracking
correlation_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Returns the current request correlation ID, or empty string if outside request scope."""
    return correlation_id_ctx.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    FastAPI / Starlette Middleware that extracts or generates a unique correlation ID
    per HTTP request, injects it into the request context, and attaches it as X-Request-ID
    on the HTTP response.
    """

    HEADER_NAME = "X-Request-ID"

    async def dispatch(self, request: Request, call_next):
        # Extract supplied header or generate a new UUID4
        supplied_id = request.headers.get(self.HEADER_NAME) or request.headers.get(self.HEADER_NAME.lower())
        correlation_id = supplied_id.strip() if supplied_id and supplied_id.strip() else uuid.uuid4().hex

        token = correlation_id_ctx.set(correlation_id)
        try:
            response: Response = await call_next(request)
            response.headers[self.HEADER_NAME] = correlation_id
            return response
        finally:
            correlation_id_ctx.reset(token)


class CorrelationIdFilter(logging.Filter):
    """
    Standard Python logging filter that injects `correlation_id` into all log records
    for structured / contextual logging output.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        cid = get_correlation_id()
        record.correlation_id = cid if cid else "-"
        return True
