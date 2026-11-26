"""Security headers, X-Request-ID, and canonical error-envelope middleware."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from services.api.schemas import ErrorDetail, ErrorResponse

SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


class ApiError(Exception):
    """Application error rendered using the canonical error envelope."""

    def __init__(self, code: str, status_code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    return rid if isinstance(rid, str) else str(uuid.uuid4())


def _error_response(status_code: int, code: str, message: str, request_id: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, request_id=request_id))
    resp = JSONResponse(status_code=status_code, content=body.model_dump())
    resp.headers["X-Request-ID"] = request_id
    for k, v in SECURITY_HEADERS.items():
        resp.headers[k] = v
    return resp


def install_middleware_and_handlers(app: FastAPI) -> None:
    """Attach request-ID/security-header middleware and canonical error handlers."""

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        raw_rid = request.headers.get("X-Request-ID", "").strip()
        rid = raw_rid if raw_rid and len(raw_rid) <= 64 else str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        for k, v in SECURITY_HEADERS.items():
            response.headers[k] = v
        return response

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, _request_id(request))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, _exc: RequestValidationError) -> JSONResponse:
        return _error_response(422, "VALIDATION", "Invalid request input", _request_id(request))

    @app.exception_handler(HTTPException)
    async def handle_http(request: Request, exc: HTTPException) -> JSONResponse:
        code = "FORBIDDEN" if exc.status_code == 403 else "UNAUTHENTICATED" if exc.status_code == 401 else "NOT_FOUND"
        return _error_response(exc.status_code, code, str(exc.detail), _request_id(request))

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, _exc: Exception) -> JSONResponse:
        return _error_response(500, "INTERNAL", "Internal server error", _request_id(request))
