from pydantic import BaseModel, EmailStr

from app.schemas.user import UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(LoginRequest):
    pass


class TokenPayload(BaseModel):
    sub: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
