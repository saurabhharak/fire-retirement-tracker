"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logging.info(f"Starting FIRE Tracker API ({settings.environment})")
    yield
    logging.info("Shutting down FIRE Tracker API")


app = FastAPI(
    title="FIRE Retirement Tracker API",
    version="2.0.0",
    description="Financial Independence, Retire Early — REST API",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
