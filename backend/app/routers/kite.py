"""Kite Connect API routes: OAuth, session management, portfolio."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import get_settings
from app.dependencies import CurrentUser, get_current_user
from app.rate_limit import limiter
from app.services import kite_svc
from app.services.audit_svc import log_audit
from app.services.supabase_client import get_service_client

router = APIRouter(tags=["kite"])


@router.get("/kite/login-url")
@limiter.limit("5/minute")
async def get_login_url(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    url = kite_svc.generate_login_url(user.id)
    return {"data": {"url": url}}


@router.get("/kite/callback")
@limiter.limit("3/minute")
async def kite_callback(
    request: Request,
    request_token: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """OAuth callback from Zerodha. No Supabase auth — validates state JWT."""
    settings = get_settings()
    try:
        user_id = kite_svc.exchange_token(request_token, state)
    except Exception:
        return JSONResponse(status_code=400, content={"detail": "Invalid or expired authorization"})
    # Audit via service-role (no Supabase JWT available on callback)
    try:
        get_service_client().table("audit_log").insert(
            {"user_id": user_id, "action": "kite_connect", "details": {"method": "oauth"}}
        ).execute()
    except Exception:
        pass  # Non-blocking
    return RedirectResponse(
        url=f"{settings.frontend_url}/mf-portfolio?connected=true",
        status_code=302,
    )


@router.get("/kite/status")
@limiter.limit("60/minute")
async def kite_status(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    session = kite_svc.get_session(user.id, user.access_token)
    if not session:
        return {"data": {"connected": False, "is_expired": False}}

    expires_at = datetime.fromisoformat(session["expires_at"])
    is_expired = datetime.now(timezone.utc) > expires_at.astimezone(timezone.utc)

    # Get last sync time from snapshot
    cached = kite_svc.get_cached_portfolio(user.id, user.access_token)
    last_sync = cached.get("synced_at") if cached else None

    return {
        "data": {
            "connected": True,
            "connected_at": session.get("connected_at"),
            "expires_at": session.get("expires_at"),
            "is_expired": is_expired,
            "last_sync": last_sync,
        }
    }


@router.delete("/kite/session")
@limiter.limit("10/minute")
async def disconnect_kite(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    kite_svc.delete_session(user.id, user.access_token)
    log_audit(user.id, "kite_disconnect", {}, user.access_token)
    return {"message": "Kite disconnected"}


@router.get("/kite/portfolio")
@limiter.limit("30/minute")
async def get_portfolio(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    portfolio = kite_svc.fetch_portfolio(user.id, user.access_token)
    if not portfolio.get("is_stale"):
        log_audit(user.id, "kite_portfolio_sync", {}, user.access_token)
    return {"data": portfolio}
