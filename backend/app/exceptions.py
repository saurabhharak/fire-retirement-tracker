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
