"""
Authentication module for FIRE Retirement Tracker.

Session stored in st.session_state (persists while tab is open).
On page reload, user needs to log in again (Streamlit limitation).
"""

import logging
from datetime import datetime, timezone

import streamlit as st
from gotrue.errors import AuthApiError
from supabase import Client


def _get_supabase() -> Client:
    from db import get_supabase_client
    return get_supabase_client()


def _update_last_activity() -> None:
    st.session_state["last_activity"] = datetime.now(timezone.utc)


def _clear_session() -> None:
    for key in ["access_token", "refresh_token", "user_id", "user_email",
                "last_activity", "fire_inputs", "income_cache", "expenses_cache"]:
        st.session_state.pop(key, None)


def _store_session(session, user) -> dict:
    st.session_state["access_token"] = session.access_token
    st.session_state["refresh_token"] = session.refresh_token
    st.session_state["user_id"] = user.id
    st.session_state["user_email"] = user.email
    _update_last_activity()
    return {"user_id": user.id, "email": user.email}


def login(email: str, password: str) -> dict:
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
        raise Exception("Login failed: no session returned.")
    return _store_session(response.session, response.user)


def send_otp(email: str) -> bool:
    supabase = _get_supabase()
    try:
        supabase.auth.sign_in_with_otp({"email": email})
        return True
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"Could not send OTP: {exc}") from exc


def verify_otp(email: str, token: str) -> dict:
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
    supabase = _get_supabase()
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
    except AuthApiError:
        raise
    except Exception as exc:
        raise Exception(f"Signup failed: {exc}") from exc
    if response.user is None:
        raise Exception("Signup failed: no user returned.")
    if response.session is not None:
        return _store_session(response.session, response.user)
    return {"user_id": response.user.id, "email": response.user.email}


def logout() -> None:
    try:
        supabase = _get_supabase()
        supabase.auth.sign_out()
    except Exception:
        pass
    _clear_session()


def check_session() -> bool:
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
    user_id = st.session_state.get("user_id")
    if user_id is None:
        raise RuntimeError("No authenticated user. Please log in.")
    return str(user_id)


def is_authenticated() -> bool:
    return "user_id" in st.session_state and st.session_state["user_id"] is not None
