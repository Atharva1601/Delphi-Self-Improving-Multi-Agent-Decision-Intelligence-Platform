"""
app/main.py
───────────
Delphi FastAPI application factory.
Uses lifespan context manager (modern FastAPI pattern) for
startup / shutdown instead of deprecated @app.on_event decorators.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import DelphiException
from app.core.logging import setup_logging
from app.database.init_db import create_tables
from app.services.expert_seeder import seed_experts
from app.api.v1.router import api_router


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version} [{settings.app_env}]")
    await create_tables()
    await seed_experts()
    logger.info("Startup complete. Ready to serve requests.")

    yield  # Application runs here

    # Shutdown
    logger.info(f"Shutting down {settings.app_name}...")


# ── App Factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Delphi — Self-improving multi-agent decision intelligence platform. "
            "Expert agents analyze, debate, challenge assumptions, form consensus, "
            "maintain reputation, and improve through reflection."
        ),
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ────────────────────────────────────────────────────
    @app.exception_handler(DelphiException)
    async def delphi_exception_handler(
        request: Request, exc: DelphiException
    ) -> JSONResponse:
        logger.warning(
            f"DelphiException: {exc.error_code}",
            path=str(request.url),
            detail=exc.detail,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_app()
