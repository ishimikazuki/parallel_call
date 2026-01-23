"""Auth schemas."""

from pydantic import BaseModel


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""

    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """Token refresh response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User info response."""

    id: str
    username: str
    email: str | None = None
    role: str
    is_active: bool = True
