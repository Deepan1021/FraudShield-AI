"""FastAPI application factory."""
from __future__ import annotations

import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import analytics, audit, knowledge, reports, system, transactions
from app.core.errors import FraudShieldError, RequestTooLargeError, StartupError
from app.core.logging import get_logger
from app.core.version import APP_FULL_NAME, APP_VERSION
from app.services.container import Container, build_container


def _error(status: int, code: str, message: str, field: Optional[str] = None, details=None) -> JSONResponse:
    err = {"code": code, "message": message}
    if field:
        err["field"] = field
    if details is not None:
        err["details"] = details
    return JSONResponse(status_code=status, content={"success": False, "error": err})


def create_app(container: Optional[Container] = None) -> FastAPI:
    log = get_logger()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            app.state.container = container or build_container()
        except StartupError as exc:
            log.critical("Startup failed: %s", exc.message)
            raise
        yield
        app.state.container.db.close_all()

    from app.core.config import load_settings
    settings = container.settings if container else load_settings()
    app = FastAPI(title=APP_FULL_NAME, version=APP_VERSION, lifespan=lifespan,
                  description="Rule-based, explainable digital-payment fraud risk assessment (forward chaining over a versioned rule base).",
                  docs_url=None if settings.is_production else "/docs", redoc_url=None if settings.is_production else "/redoc",
                  openapi_url=None if settings.is_production else "/openapi.json")
    if container is not None:
        app.state.container = container

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"],
                       allow_headers=["Content-Type"], allow_credentials=False)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        started = time.perf_counter()
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > settings.max_request_bytes:
            return _error(413, RequestTooLargeError.code, f"Request body exceeds {settings.max_request_bytes} bytes.")
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Process-Time-ms"] = f"{(time.perf_counter() - started) * 1000:.2f}"
        return response

    @app.exception_handler(FraudShieldError)
    async def handle_domain_error(request: Request, exc: FraudShieldError):
        if exc.status_code >= 500:
            log.error("%s on %s: %s", exc.code, request.url.path, exc.message)
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        loc = [str(p) for p in first.get("loc", []) if p not in ("body", "query", "path")]
        field = loc[-1] if loc else None
        kind = first.get("type", "")
        if kind == "extra_forbidden":
            return _error(422, "UNKNOWN_FIELD", f"Unknown field '{field}'. Payment credentials are never accepted.", field)
        msg = first.get("msg", "Invalid request")
        details = [{"field": ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query", "path")), "message": e.get("msg", "")} for e in errors]
        return _error(422, "VALIDATION_ERROR", f"{field}: {msg}" if field else msg, field, details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException):
        path = request.url.path
        if exc.status_code == 404 and request.method == "GET" and not path.startswith("/api") and settings.serve_frontend:
            dist = settings.frontend_dist.resolve()
            index = dist / "index.html"
            if index.is_file():
                candidate = (dist / path.lstrip("/")).resolve()
                if candidate.is_file() and dist in candidate.parents:
                    return FileResponse(candidate)
                return FileResponse(index)
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return _error(exc.status_code, code, "Resource not found." if exc.status_code == 404 else str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        log.exception("Unhandled error on %s", request.url.path)
        return _error(500, "INTERNAL_ERROR", "An unexpected error occurred. The incident has been logged.")

    for module in (system, transactions, analytics, knowledge, audit, reports):
        app.include_router(module.router, prefix="/api")
    return app


app = create_app()
