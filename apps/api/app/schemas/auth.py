from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    status: str
    role: str | None = None
