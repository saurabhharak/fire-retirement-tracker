"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.rate_limit import limiter
from app.exceptions import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logging.info("Starting FIRE Tracker API (%s)", settings.environment)
    yield
    logging.info("Shutting down FIRE Tracker API")


settings = get_settings()

app = FastAPI(
    title="FIRE Retirement Tracker API",
    version="2.0.0",
    description="Financial Independence, Retire Early — REST API",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


# Security headers middleware
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "0"
    return response


# Exception handlers
register_exception_handlers(app)


# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


# Routers
from app.routers import fire_inputs, income, expenses, sip_log, projections, export, precious_metals

app.include_router(fire_inputs.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(precious_metals.router, prefix="/api")
app.include_router(sip_log.router, prefix="/api")
app.include_router(projections.router, prefix="/api")
app.include_router(export.router, prefix="/api")
