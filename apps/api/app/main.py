from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from apps.api.app.core.errors import ApiError
from apps.api.app.routes.analytics import router


def create_app() -> FastAPI:
    application = FastAPI(
        title="Urban Mobility Analytics API",
        summary="Read-only analytics over local DuckDB dbt marts.",
        version="0.1.0",
    )
    application.include_router(router)

    @application.exception_handler(ApiError)
    async def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail},
        )

    return application


app = create_app()
