"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, campaigns, twilio, webhooks
from app.config import get_settings
from app.websocket import dashboard_ws, operator_ws


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    print(f"Starting {settings.app_name}...")
    yield
    # Shutdown
    print("Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Predictive dialer system for telemarketing operations",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(campaigns.router, prefix="/api/v1")
    app.include_router(twilio.router, prefix="/api/v1")
    app.include_router(webhooks.router)  # No prefix - Twilio needs exact paths

    # WebSocket routers
    app.include_router(operator_ws.router)
    app.include_router(dashboard_ws.router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app


app = create_app()
