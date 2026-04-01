"""FastAPI dependencies for authentication and authorization.

Uses Supabase JWKS endpoint for asymmetric JWT verification (ECC P-256).
More secure than shared secret (HS256) — no secret to leak.
"""

import logging
from functools import lru_cache

import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

security = HTTPBearer()


class CurrentUser(BaseModel):
    """Represents the authenticated user from the JWT."""
    id: str
    email: str = ""
    access_token: str = ""


@lru_cache
def _get_jwks_client(supabase_url: str) -> PyJWKClient:
    """Cached JWKS client for Supabase JWT verification.

    Fetches the public keys from Supabase's JWKS endpoint.
    The JWKS URL is: {supabase_url}/auth/v1/.well-known/jwks.json
    """
    jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """Validate Supabase JWT using JWKS (asymmetric key verification).

    1. Fetches the signing key from Supabase's JWKS endpoint
    2. Verifies the JWT signature using the public key
    3. Extracts user ID and email from the token claims
    """
    token = credentials.credentials

    try:
        # Get the signing key from JWKS
        jwks_client = _get_jwks_client(settings.supabase_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and verify the JWT
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256"],  # Support both ECC (new) and HS256 (legacy)
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning("JWT validation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("JWT verification error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
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
