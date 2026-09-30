from asgi_correlation_id import correlation_id
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler


# This is to make sure we add the request ID to the response headers for the case
# of unhandled server errors.
async def unhandled_exception_handler(request: Request, exc: Exception):
    return await http_exception_handler(
        request,
        HTTPException(
            500,
            "Internal server error",
            headers={"X-Request-ID": correlation_id.get() or ""},
        ),
    )


def register_exception_handlers(app: FastAPI):
    app.add_exception_handler(Exception, unhandled_exception_handler)
