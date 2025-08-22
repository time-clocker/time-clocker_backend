# app/schemas/auth.py
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from pydantic import ConfigDict
from app.schemas.employee import EmployeeOut


# ---------- LOGIN ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    returnSecureToken: bool = True


class LoginResponse(BaseModel):
    idToken: str
    refreshToken: Optional[str] = None
    expiresIn: Optional[str] = None
    email: Optional[EmailStr] = None
    localId: Optional[str] = None


# ---------- REGISTER ----------
class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=6)
    hourly_rate: Optional[float] = None


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee: EmployeeOut
    idToken: Optional[str] = None
    refreshToken: Optional[str] = None
    expiresIn: Optional[str] = None
    email: Optional[EmailStr] = None
    localId: Optional[str] = None
