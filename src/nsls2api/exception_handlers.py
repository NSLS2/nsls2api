from asgi_correlation_id import correlation_id
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Add the correlation ID to responses for unhandled server errors."""
    return await http_exception_handler(
        request,
        HTTPException(
            500,
            "Internal server error",
            headers={"X-Request-ID": correlation_id.get() or ""},
        ),
    )


def register_exception_handlers(app: FastAPI):
    """Register all exception handlers for the app."""
    # Generic Exception must be listed last.
    app.add_exception_handler(Exception, unhandled_exception_handler)
