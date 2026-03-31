"""
Authentication module for FIRE Retirement Tracker.

Handles login, signup, logout, session validation, and idle timeout
using Supabase Auth. Stores JWT tokens and user info in st.session_state.
"""

from datetime import datetime, timezone

import streamlit as st
from gotrue.errors import AuthApiError

from supabase import Client


def _get_supabase() -> Client:
    """Retrieve the cached Supabase client from session_state or cache."""
    # Imported here to avoid circular imports; db.py or app.py sets this up.
    from db import get_supabase_client

    return get_supabase_client()


def _update_last_activity() -> None:
    """Record the current time as the last user activity."""
    st.session_state["last_activity"] = datetime.now(timezone.utc)


def _clear_session() -> None:
    """Remove all auth-related keys from session_state."""
    keys_to_clear = [
        "access_token",
        "refresh_token",
        "user_id",
        "user_email",
        "last_activity",
        "fire_inputs",
        "income_cache",
        "expenses_cache",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)


def _store_session(session, user) -> dict:
    """Persist auth tokens and user info into session_state.

    Returns a dict with user_id and email for convenience.
    """
    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token
    st.session_state["user_id"] = user.id
    st.session_state["user_email"] = user.email
    _update_last_activity()
    return {"user_id": user.id, "email": user.email}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def login(email: str, password: str) -> dict:
    """Authenticate a user with email and password.

    Returns:
        dict with ``user_id`` and ``email`` on success.

    Raises:
        AuthApiError: on invalid credentials or Supabase error.
        Exception: on unexpected failures.
    """
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


def signup(email: str, password: str) -> dict:
    """Create a new user account (initial setup only).

    After the first account is created, disable email signups in the
    Supabase dashboard (Auth > Settings > Enable email signups = false).

    Returns:
        dict with ``user_id`` and ``email`` on success.

    Raises:
        AuthApiError: if signup is disabled or validation fails.
        Exception: on unexpected failures.
    """
    supabase = _get_supabase()

    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"Signup failed: {exc}") from exc

    if response.user is None:
        raise Exception("Signup failed: no user returned from Supabase.")

    # If email confirmation is enabled, session may be None until confirmed.
    if response.session is not None:
        return _store_session(response.session, response.user)

    return {"user_id": response.user.id, "email": response.user.email}


def logout() -> None:
    """Sign out the current user and clear all session data."""
    try:
        supabase = _get_supabase()
        supabase.auth.sign_out()
    except Exception:
        # Even if the server-side sign-out fails, clear local state.
        pass
    _clear_session()


def check_session() -> bool:
    """Check whether the current session is valid; refresh the JWT if needed.

    Returns:
        True if the session is valid (or was successfully refreshed).
        False if there is no session or the refresh failed.
    """
    if "access_token" not in st.session_state:
        return False

    supabase = _get_supabase()

    try:
        # get_session() returns the current session and auto-refreshes if the
        # access token is expired but the refresh token is still valid.
        response = supabase.auth.get_session()

        if response is None:
            _clear_session()
            return False

        # Update tokens in case they were refreshed.
        st.session_state["access_token"] = response.access_token
        st.session_state["refresh_token"] = response.refresh_token
        _update_last_activity()
        return True

    except Exception:
        _clear_session()
        return False


def check_idle_timeout() -> bool:
    """Check whether the user has been idle for longer than 30 minutes.

    If the timeout has been exceeded the session is cleared automatically.

    Returns:
        True if the session is still active (within timeout).
        False if the session was cleared due to inactivity.
    """
    from config import IDLE_TIMEOUT_MINUTES

    last_activity = st.session_state.get("last_activity")

    if last_activity is None:
        return False

    elapsed = (datetime.now(timezone.utc) - last_activity).total_seconds()
    timeout_seconds = IDLE_TIMEOUT_MINUTES * 60

    if elapsed > timeout_seconds:
        logout()
        return False

    # User is still active -- refresh the timestamp.
    _update_last_activity()
    return True


def get_current_user_id() -> str:
    """Return the ``user_id`` stored in session_state.

    Returns:
        The user's UUID string.

    Raises:
        RuntimeError: if no user is logged in.
    """
    user_id = st.session_state.get("user_id")
    if user_id is None:
        raise RuntimeError("No authenticated user. Please log in.")
    return str(user_id)


def is_authenticated() -> bool:
    """Convenience helper: True when a user_id is present in session_state."""
    return "user_id" in st.session_state and st.session_state["user_id"] is not None
