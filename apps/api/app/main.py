from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.app.core.errors import ApiError
from apps.api.app.routes.analytics import router
from urban_mobility.observability import (
    REQUEST_ID_HEADER,
    emit_event,
    resolve_correlation_id,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Urban Mobility Analytics API",
        summary="Read-only analytics over local DuckDB dbt marts.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    application.include_router(router)

    @application.middleware("http")
    async def observe_request(request: Request, call_next):
        request_id = resolve_correlation_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started_at = time.perf_counter()
        emit_event(
            level="INFO",
            component="api",
            event="api.request.started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
        except Exception as error:
            emit_event(
                level="ERROR",
                component="api",
                event="api.request.unhandled_error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
                error_type=type(error).__name__,
            )
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )
        else:
            emit_event(
                level="INFO",
                component="api",
                event="api.request.completed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @application.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
        emit_event(
            level="ERROR",
            component="api",
            event="api.request.error",
            request_id=getattr(request.state, "request_id", None),
            method=request.method,
            path=request.url.path,
            status_code=error.status_code,
            error_type=type(error).__name__,
        )
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
        )

    return application


app = create_app()
