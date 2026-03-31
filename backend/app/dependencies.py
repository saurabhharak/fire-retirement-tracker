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
    """Validate Supabase JWT and return the current user."""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError:
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
