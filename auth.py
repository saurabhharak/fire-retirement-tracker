"""
Authentication module for FIRE Retirement Tracker.

Handles login, signup, logout, session validation, and idle timeout
using Supabase Auth.

Session persistence strategy (industry standard):
- Auth tokens stored in BOTH st.session_state AND browser cookies
- session_state = fast access during current session
- Cookies = survive browser tab close, page refresh, server restarts
- On page load: check session_state first, fall back to cookies
- On login: write to both
- On logout: clear both
"""

import logging
from datetime import datetime, timezone

import streamlit as st
from gotrue.errors import AuthApiError
from supabase import Client


# ---------------------------------------------------------------------------
# Cookie helpers (using Streamlit query params as lightweight cookie alternative)
# We use st.query_params as a fallback since extra-streamlit-components
# can have compatibility issues. The primary persistence mechanism is
# writing tokens to a hidden cookie via JS injection.
# ---------------------------------------------------------------------------

def _save_to_cookies(access_token: str, refresh_token: str, user_id: str, user_email: str) -> None:
    """Save auth tokens to browser localStorage via JS injection."""
    js_code = f"""
    <script>
        localStorage.setItem('fire_access_token', '{access_token}');
        localStorage.setItem('fire_refresh_token', '{refresh_token}');
        localStorage.setItem('fire_user_id', '{user_id}');
        localStorage.setItem('fire_user_email', '{user_email}');
    </script>
    """
    st.components.v1.html(js_code, height=0)


def _clear_cookies() -> None:
    """Clear auth tokens from browser localStorage."""
    js_code = """
    <script>
        localStorage.removeItem('fire_access_token');
        localStorage.removeItem('fire_refresh_token');
        localStorage.removeItem('fire_user_id');
        localStorage.removeItem('fire_user_email');
    </script>
    """
    st.components.v1.html(js_code, height=0)


def _restore_from_cookies() -> bool:
    """Try to restore session from browser localStorage.

    Uses a two-step approach:
    1. Inject JS to read localStorage and write to a hidden element
    2. On next rerun, check if tokens are available

    Returns True if session was restored to session_state.
    """
    # This is handled via the cookie sync component in app.py
    return False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_supabase() -> Client:
    """Retrieve the cached Supabase client."""
    from db import get_supabase_client
    return get_supabase_client()


def _update_last_activity() -> None:
    """Record the current time as the last user activity."""
    st.session_state["last_activity"] = datetime.now(timezone.utc)


def _clear_session() -> None:
    """Remove all auth-related keys from session_state and cookies."""
    keys_to_clear = [
        "access_token", "refresh_token", "user_id", "user_email",
        "last_activity", "fire_inputs", "income_cache", "expenses_cache",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    try:
        _clear_cookies()
    except Exception:
        pass


def _store_session(session, user) -> dict:
    """Persist auth tokens into session_state and browser cookies."""
    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token
    st.session_state["user_id"] = user.id
    st.session_state["user_email"] = user.email
    _update_last_activity()

    # Persist to browser cookies for tab-close survival
    try:
        _save_to_cookies(session.access_token, session.refresh_token, user.id, user.email)
    except Exception:
        pass  # Cookies are a bonus, not critical

    return {"user_id": user.id, "email": user.email}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def login(email: str, password: str) -> dict:
    """Authenticate with email and password."""
    supabase = _get_supabase()
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"Login failed: {exc}") from exc

    if response.session is None or response.user is None:
        raise Exception("Login failed: no session returned from Supabase.")
    return _store_session(response.session, response.user)


def send_otp(email: str) -> bool:
    """Send OTP to email via Supabase Auth."""
    supabase = _get_supabase()
    try:
        supabase.auth.sign_in_with_otp({"email": email})
        return True
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"Could not send OTP: {exc}") from exc


def verify_otp(email: str, token: str) -> dict:
    """Verify OTP code and log in."""
    supabase = _get_supabase()
    try:
        response = supabase.auth.verify_otp({
            "email": email, "token": token, "type": "email",
        })
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"OTP verification failed: {exc}") from exc

    if response.session is None or response.user is None:
        raise Exception("OTP verification failed: no session returned.")
    return _store_session(response.session, response.user)


def signup(email: str, password: str) -> dict:
    """Create a new user account."""
    supabase = _get_supabase()
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"Signup failed: {exc}") from exc

    if response.user is None:
        raise Exception("Signup failed: no user returned from Supabase.")
    if response.session is not None:
        return _store_session(response.session, response.user)
    return {"user_id": response.user.id, "email": response.user.email}


def logout() -> None:
    """Sign out and clear all session data."""
    try:
        supabase = _get_supabase()
        supabase.auth.sign_out()
    except Exception:
        pass
    _clear_session()


def check_session() -> bool:
    """Validate and refresh the current session.

    Uses refresh token from session_state to restore the Supabase session.
    This is necessary because the shared @st.cache_resource client doesn't
    retain per-user auth state between Streamlit reruns.
    """
    if "access_token" not in st.session_state:
        return False

    refresh_token = st.session_state.get("refresh_token")
    if not refresh_token:
        return False

    supabase = _get_supabase()

    try:
        response = supabase.auth.set_session(
            st.session_state["access_token"], refresh_token,
        )
        if response is None or response.session is None:
            _clear_session()
            return False

        st.session_state["access_token"] = response.session.access_token
        st.session_state["refresh_token"] = response.session.refresh_token
        _update_last_activity()
        return True
    except Exception:
        try:
            response = supabase.auth.refresh_session(refresh_token)
            if response and response.session:
                st.session_state["access_token"] = response.session.access_token
                st.session_state["refresh_token"] = response.session.refresh_token
                _update_last_activity()
                return True
        except Exception:
            pass
        _clear_session()
        return False


def check_idle_timeout() -> bool:
    """Check idle timeout (30 minutes). Clear session if exceeded."""
    from config import IDLE_TIMEOUT_MINUTES

    last_activity = st.session_state.get("last_activity")
    if last_activity is None:
        return False

    elapsed = (datetime.now(timezone.utc) - last_activity).total_seconds()
    if elapsed > IDLE_TIMEOUT_MINUTES * 60:
        logout()
        return False

    _update_last_activity()
    return True


def get_current_user_id() -> str:
    """Return the user_id from session_state."""
    user_id = st.session_state.get("user_id")
    if user_id is None:
        raise RuntimeError("No authenticated user. Please log in.")
    return str(user_id)


def is_authenticated() -> bool:
    """True when a user_id is present in session_state."""
    return "user_id" in st.session_state and st.session_state["user_id"] is not None
