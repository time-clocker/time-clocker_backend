from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field
class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    firebase_uid: str
    full_name: str
    email: EmailStr
    hourly_rate: float
    active: bool

class EmployeeCreate(BaseModel):
    firebase_uid: str = Field(..., min_length=1)
    full_name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    hourly_rate: Optional[float] = None
    active: Optional[bool] = True

class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    hourly_rate: Optional[float] = None
    active: Optional[bool] = None
