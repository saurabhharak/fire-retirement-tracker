# Phase 1: FastAPI Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready FastAPI backend that reuses the verified financial engine and replaces the Streamlit prototype's server layer.

**Architecture:** FastAPI REST API with Supabase Python client for DB access. JWT validation via Supabase secret. Repository-pattern services. The core engine.py (720 verified tests) is copied unchanged. Pydantic v2 for all request/response schemas.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, pydantic-settings, supabase-py, python-jose (JWT), uvicorn, pytest

---

## File Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, CORS, lifespan, exception handlers
│   ├── config.py                  # pydantic-settings: SUPABASE_URL, KEY, JWT_SECRET
│   ├── dependencies.py            # get_current_user (JWT dependency)
│   ├── exceptions.py              # Custom exceptions + handlers
│   │
│   ├── core/                      # ZERO framework dependencies
│   │   ├── __init__.py
│   │   ├── engine.py              # COPIED from root engine.py (unchanged)
│   │   ├── constants.py           # COPIED from root config.py (renamed)
│   │   ├── formatting.py          # format_indian() extracted from engine.py
│   │   └── models.py              # COPIED from root models.py (unchanged)
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── fire_inputs.py         # GET/PUT /api/fire-inputs
│   │   ├── income.py              # GET/POST/DELETE /api/income
│   │   ├── expenses.py            # GET/POST/PATCH/DELETE /api/expenses
│   │   ├── sip_log.py             # GET/POST /api/sip-log
│   │   ├── projections.py         # GET /api/projections/*
│   │   └── export.py              # GET /api/export, DELETE /api/account
│   │
│   └── services/
│       ├── __init__.py
│       ├── supabase_client.py     # get_user_client(access_token)
│       ├── fire_inputs_svc.py
│       ├── income_svc.py
│       ├── expenses_svc.py
│       ├── sip_log_svc.py
│       └── audit_svc.py
│
├── tests/
│   ├── conftest.py                # Fixtures: test client, mock JWT
│   ├── unit/
│   │   ├── test_engine.py
│   │   ├── test_formatting.py
│   │   └── test_constants.py
│   └── excel_verification/        # Existing 720 tests (copied)
│
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── .env.example
```

---

### Task 1: Project Scaffold + pyproject.toml

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/.env.example`

- [ ] **Step 1: Create directory structure**

```bash
cd C:/Projects/fire-retirement-tracker
mkdir -p backend/app/core backend/app/routers backend/app/services backend/tests/unit backend/tests/excel_verification
touch backend/app/__init__.py backend/app/core/__init__.py backend/app/routers/__init__.py backend/app/services/__init__.py backend/tests/__init__.py backend/tests/unit/__init__.py
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "fire-retirement-tracker-api"
version = "2.0.0"
description = "FastAPI backend for FIRE Retirement Tracker"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.30.0",
    "supabase>=2.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-jose[cryptography]>=3.3.0",
    "python-dotenv>=1.0.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
    "mypy>=1.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["app"]

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 3: Create requirements.txt**

```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
supabase>=2.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-jose[cryptography]>=3.3.0
python-dotenv>=1.0.0
python-multipart>=0.0.9
```

- [ ] **Step 4: Create .env.example**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_JWT_SECRET=your-jwt-secret-here
ENVIRONMENT=development
LOG_LEVEL=INFO

# WARNING: Never use the service_role key. Only the anon (public) key.
# Get JWT secret from: Supabase Dashboard > Settings > API > JWT Secret
```

- [ ] **Step 5: Install dependencies**

```bash
cd backend && pip install -e ".[dev]"
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI project structure"
```

---

### Task 2: Copy Core Engine (unchanged)

**Files:**
- Create: `backend/app/core/engine.py` (copy from root)
- Create: `backend/app/core/constants.py` (copy + rename from root config.py)
- Create: `backend/app/core/formatting.py` (extract from engine.py)
- Create: `backend/app/core/models.py` (copy from root)
- Copy: `backend/tests/excel_verification/` (all existing test files)

- [ ] **Step 1: Copy core files**

```bash
cd C:/Projects/fire-retirement-tracker
cp config.py backend/app/core/constants.py
cp models.py backend/app/core/models.py
cp engine.py backend/app/core/engine.py
```

- [ ] **Step 2: Fix engine.py import to use constants (not config)**

In `backend/app/core/engine.py`, change line 10:
```python
# OLD:
from config import BUCKET_PERCENTAGES, FUNDS, SWR_SCENARIOS, SWR_VERDICTS
# NEW:
from app.core.constants import BUCKET_PERCENTAGES, FUNDS, SWR_SCENARIOS, SWR_VERDICTS
```

- [ ] **Step 3: Create formatting.py (extract format_indian from engine.py)**

```python
"""Indian number formatting and display utilities."""


def format_indian(amount: float) -> str:
    """Format a number in Indian comma notation (e.g. 1,30,20,768)."""
    is_negative = amount < 0
    n = int(round(abs(amount)))
    s = str(n)

    if len(s) <= 3:
        result = s
    else:
        last3 = s[-3:]
        remaining = s[:-3]
        groups = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        result = ",".join(groups) + "," + last3

    return ("-" + result) if is_negative else result
```

- [ ] **Step 4: Copy existing tests**

```bash
cp tests/conftest.py backend/tests/excel_verification/
cp tests/test_01_inputs.py backend/tests/excel_verification/
cp tests/test_02_fund_allocation.py backend/tests/excel_verification/
cp tests/test_03_growth_projection.py backend/tests/excel_verification/
cp tests/test_04_retirement_income.py backend/tests/excel_verification/
cp tests/test_05_sip_tracker.py backend/tests/excel_verification/
```

- [ ] **Step 5: Write unit test for formatting**

File: `backend/tests/unit/test_formatting.py`
```python
from app.core.formatting import format_indian


def test_format_small_number():
    assert format_indian(500) == "500"

def test_format_thousands():
    assert format_indian(1250) == "1,250"

def test_format_lakhs():
    assert format_indian(125000) == "1,25,000"

def test_format_crores():
    assert format_indian(10844030) == "1,08,44,030"

def test_format_negative():
    assert format_indian(-50000) == "-50,000"

def test_format_zero():
    assert format_indian(0) == "0"

def test_format_float_rounds():
    assert format_indian(1234.56) == "1,235"
```

- [ ] **Step 6: Run unit tests**

```bash
cd backend && python -m pytest tests/unit/test_formatting.py -v
```
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/ backend/tests/
git commit -m "feat(backend): copy core engine, constants, models, formatting"
```

---

### Task 3: Config + Settings (pydantic-settings)

**Files:**
- Create: `backend/app/config.py`

- [ ] **Step 1: Create settings module**

```python
"""Application settings using pydantic-settings (12-factor compliant)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_jwt_secret: str

    # App
    environment: str = "production"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "feat(backend): add pydantic-settings configuration"
```

---

### Task 4: Custom Exceptions + Handlers

**Files:**
- Create: `backend/app/exceptions.py`

- [ ] **Step 1: Create exception hierarchy**

```python
"""Custom exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class FireTrackerError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str = "An error occurred"):
        self.message = message
        super().__init__(message)


class DatabaseError(FireTrackerError):
    """Raised when a database operation fails."""
    pass


class DataNotFoundError(FireTrackerError):
    """Raised when requested data does not exist."""
    pass


class AuthenticationError(FireTrackerError):
    """Raised when authentication fails."""
    pass


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""

    @app.exception_handler(DataNotFoundError)
    async def data_not_found_handler(request: Request, exc: DataNotFoundError):
        return JSONResponse(status_code=404, content={"detail": exc.message})

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError):
        return JSONResponse(status_code=500, content={"detail": "Database operation failed."})

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"detail": exc.message})
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/exceptions.py
git commit -m "feat(backend): add custom exception hierarchy and handlers"
```

---

### Task 5: JWT Authentication Dependency

**Files:**
- Create: `backend/app/dependencies.py`

- [ ] **Step 1: Create JWT validation dependency**

```python
"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import Settings, get_settings

security = HTTPBearer()


class CurrentUser:
    """Represents the authenticated user from the JWT."""

    def __init__(self, id: str, email: str = "", access_token: str = ""):
        self.id = id
        self.email = email
        self.access_token = access_token


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Validate Supabase JWT and return the current user.

    The JWT is verified locally using the Supabase JWT secret.
    No network call to Supabase is needed.
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID",
        )

    return CurrentUser(
        id=user_id,
        email=payload.get("email", ""),
        access_token=token,
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "feat(backend): add JWT authentication dependency"
```

---

### Task 6: Supabase Client Service

**Files:**
- Create: `backend/app/services/supabase_client.py`

- [ ] **Step 1: Create client service**

```python
"""Supabase client factory for per-request authenticated access."""

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_anon_client() -> Client:
    """Get a Supabase client with the anon key (for non-authenticated operations)."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


def get_user_client(access_token: str) -> Client:
    """Create a Supabase client scoped to a specific user's JWT for RLS.

    This client uses the anon key but sets the user's JWT as the auth session,
    so all queries respect Row Level Security policies.
    """
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_key)
    client.auth.set_session(access_token, "")
    return client
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/supabase_client.py
git commit -m "feat(backend): add Supabase client factory with per-request auth"
```

---

### Task 7: FastAPI Main App

**Files:**
- Create: `backend/app/main.py`

- [ ] **Step 1: Create main app**

```python
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


# Routers (added in subsequent tasks)
# from app.routers import fire_inputs, income, expenses, sip_log, projections, export
# app.include_router(fire_inputs.router, prefix="/api")
# app.include_router(income.router, prefix="/api")
# ...
```

- [ ] **Step 2: Test the server starts**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```
Expected: Server runs, `http://localhost:8000/api/health` returns `{"status": "ok", "version": "2.0.0"}`

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat(backend): add FastAPI main app with CORS, health check, lifespan"
```

---

### Task 8: Fire Inputs Service + Router

**Files:**
- Create: `backend/app/services/fire_inputs_svc.py`
- Create: `backend/app/routers/fire_inputs.py`

- [ ] **Step 1: Create service**

```python
"""FIRE inputs CRUD service."""

import logging
from typing import Optional

from app.exceptions import DatabaseError
from app.services.supabase_client import get_user_client

logger = logging.getLogger(__name__)


async def load_fire_inputs(user_id: str, access_token: str) -> Optional[dict]:
    """Load FIRE settings for a user. Returns None if not found."""
    try:
        client = get_user_client(access_token)
        response = client.table("fire_inputs").select("*").eq("user_id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Could not load fire inputs: {e}")
        raise DatabaseError("Could not load FIRE settings") from e


async def save_fire_inputs(user_id: str, data: dict, access_token: str) -> dict:
    """Upsert FIRE settings for a user."""
    try:
        client = get_user_client(access_token)
        payload = {**data, "user_id": user_id}
        response = client.table("fire_inputs").upsert(payload, on_conflict="user_id").execute()
        if response.data:
            return response.data[0]
        raise DatabaseError("No data returned after save")
    except DatabaseError:
        raise
    except Exception as e:
        logger.error(f"Could not save fire inputs: {e}")
        raise DatabaseError("Could not save FIRE settings") from e
```

- [ ] **Step 2: Create router**

```python
"""FIRE inputs API routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import CurrentUser, get_current_user
from app.services import fire_inputs_svc

router = APIRouter(tags=["fire-inputs"])


@router.get("/fire-inputs")
async def get_fire_inputs(user: CurrentUser = Depends(get_current_user)):
    """Get the current user's FIRE settings."""
    result = await fire_inputs_svc.load_fire_inputs(user.id, user.access_token)
    if result is None:
        return {"data": None, "message": "No FIRE settings configured yet"}
    return {"data": result}


@router.put("/fire-inputs")
async def update_fire_inputs(
    data: dict,
    user: CurrentUser = Depends(get_current_user),
):
    """Create or update the user's FIRE settings."""
    result = await fire_inputs_svc.save_fire_inputs(user.id, data, user.access_token)
    return {"data": result, "message": "FIRE settings saved"}
```

- [ ] **Step 3: Register router in main.py**

Add to `backend/app/main.py`:
```python
from app.routers import fire_inputs
app.include_router(fire_inputs.router, prefix="/api")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/fire_inputs_svc.py backend/app/routers/fire_inputs.py backend/app/main.py
git commit -m "feat(backend): add FIRE inputs GET/PUT endpoints"
```

---

### Task 9: Projections Router (engine integration)

**Files:**
- Create: `backend/app/routers/projections.py`

- [ ] **Step 1: Create projections router**

```python
"""Projection API routes — computed from engine.py, not stored."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.engine import (
    compute_derived_inputs,
    compute_fund_allocation,
    compute_growth_projection,
    compute_monthly_sips,
    compute_retirement_metrics,
)
from app.dependencies import CurrentUser, get_current_user
from app.services import fire_inputs_svc

router = APIRouter(tags=["projections"])


async def _get_inputs(user: CurrentUser) -> dict:
    """Helper: load fire inputs and compute derived values."""
    raw = await fire_inputs_svc.load_fire_inputs(user.id, user.access_token)
    if raw is None:
        raise HTTPException(status_code=404, detail="Configure FIRE Settings first")
    return compute_derived_inputs(raw)


@router.get("/projections/growth")
async def get_growth_projection(user: CurrentUser = Depends(get_current_user)):
    """Year-by-year portfolio growth projection."""
    inputs = await _get_inputs(user)
    projection = compute_growth_projection(inputs)
    return {"data": projection}


@router.get("/projections/retirement")
async def get_retirement_analysis(user: CurrentUser = Depends(get_current_user)):
    """Retirement metrics, 3-bucket strategy, SWR comparison."""
    inputs = await _get_inputs(user)
    projection = compute_growth_projection(inputs)
    years = inputs["years_to_retirement"]
    corpus = projection[years]["portfolio"] if years < len(projection) else projection[-1]["portfolio"]
    metrics = compute_retirement_metrics(inputs, corpus)
    return {"data": metrics}


@router.get("/projections/fund-allocation")
async def get_fund_allocation(user: CurrentUser = Depends(get_current_user)):
    """10-fund allocation breakdown."""
    inputs = await _get_inputs(user)
    allocation = compute_fund_allocation(inputs)
    return {"data": allocation}


@router.get("/projections/monthly-sips")
async def get_monthly_sips(user: CurrentUser = Depends(get_current_user)):
    """192-month SIP schedule."""
    inputs = await _get_inputs(user)
    sips = compute_monthly_sips(inputs)
    return {"data": sips}
```

- [ ] **Step 2: Register router**

Add to `backend/app/main.py`:
```python
from app.routers import projections
app.include_router(projections.router, prefix="/api")
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/routers/projections.py backend/app/main.py
git commit -m "feat(backend): add projection endpoints (growth, retirement, funds, SIPs)"
```

---

### Task 10: Income, Expenses, SIP Log Services + Routers

**Files:**
- Create: `backend/app/services/income_svc.py`
- Create: `backend/app/services/expenses_svc.py`
- Create: `backend/app/services/sip_log_svc.py`
- Create: `backend/app/services/audit_svc.py`
- Create: `backend/app/routers/income.py`
- Create: `backend/app/routers/expenses.py`
- Create: `backend/app/routers/sip_log.py`
- Create: `backend/app/routers/export.py`

These follow the exact same pattern as Task 8 (fire_inputs). Each service has load/save/delete functions that raise DatabaseError. Each router has GET/POST/PUT/DELETE endpoints with `Depends(get_current_user)`.

- [ ] **Step 1: Create all remaining services** (income_svc.py, expenses_svc.py, sip_log_svc.py, audit_svc.py)

Each follows this pattern:
```python
async def load_X(user_id: str, access_token: str, ...) -> list[dict]:
    try:
        client = get_user_client(access_token)
        response = client.table("X").select("*").eq("user_id", user_id)...execute()
        return response.data or []
    except Exception as e:
        raise DatabaseError(...) from e
```

- [ ] **Step 2: Create all remaining routers** (income.py, expenses.py, sip_log.py, export.py)

- [ ] **Step 3: Register all routers in main.py**

```python
from app.routers import fire_inputs, income, expenses, sip_log, projections, export

app.include_router(fire_inputs.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(sip_log.router, prefix="/api")
app.include_router(projections.router, prefix="/api")
app.include_router(export.router, prefix="/api")
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ backend/app/routers/ backend/app/main.py
git commit -m "feat(backend): add all CRUD routers (income, expenses, SIP, export)"
```

---

### Task 11: Dockerfile + Render Deploy Config

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/render.yaml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Test locally**

```bash
cd backend && uvicorn app.main:app --reload --port 8000
# Visit http://localhost:8000/docs for Swagger UI
# All endpoints should be visible
```

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat(backend): add Dockerfile for Render deployment"
```

---

### Task 12: Run All Tests

- [ ] **Step 1: Run unit tests**

```bash
cd backend && python -m pytest tests/unit/ -v
```
Expected: All formatting tests pass.

- [ ] **Step 2: Verify engine tests still work**

```bash
cd backend && python -m pytest tests/excel_verification/ -v --tb=short -q 2>&1 | tail -5
```
Expected: 720 passed.

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat(backend): Phase 1 complete — FastAPI backend with all endpoints"
git push origin revamp/ui-production-ready
```

---

## API Summary

After Phase 1, these endpoints are available:

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | No | Health check |
| GET | `/api/fire-inputs` | JWT | Get FIRE settings |
| PUT | `/api/fire-inputs` | JWT | Save FIRE settings |
| GET | `/api/income?limit=12` | JWT | List income entries |
| POST | `/api/income` | JWT | Create/update income |
| DELETE | `/api/income/{month}/{year}` | JWT | Delete income entry |
| GET | `/api/expenses?active=true` | JWT | List expenses |
| POST | `/api/expenses` | JWT | Create expense |
| PATCH | `/api/expenses/{id}` | JWT | Update expense |
| DELETE | `/api/expenses/{id}` | JWT | Deactivate expense |
| GET | `/api/sip-log?limit=60` | JWT | List SIP logs |
| POST | `/api/sip-log` | JWT | Create/update SIP log |
| GET | `/api/projections/growth` | JWT | Growth projection |
| GET | `/api/projections/retirement` | JWT | Retirement analysis |
| GET | `/api/projections/fund-allocation` | JWT | Fund allocation |
| GET | `/api/projections/monthly-sips` | JWT | Monthly SIP schedule |
| GET | `/api/export` | JWT | Export all data |
| DELETE | `/api/account` | JWT | Delete account data |

Swagger docs available at: `http://localhost:8000/docs`
