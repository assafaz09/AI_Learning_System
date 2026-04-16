from typing import Optional

from pydantic import BaseModel, EmailStr


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str


RegisterRequest = AuthCredentials
LoginRequest = AuthCredentials


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True
