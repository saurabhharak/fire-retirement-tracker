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
    """Create a Supabase client scoped to a specific user's JWT for RLS."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_key)
    client.auth.set_session(access_token, "")
    return client
