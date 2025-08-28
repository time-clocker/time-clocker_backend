from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class TimeEntryOut(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    clock_in: datetime
    clock_out: Optional[datetime] = None
    tz: str
    class Config:
        from_attributes = True

class ClockInRequest(BaseModel):
    tz: str = "America/Bogota"

class ClockOutRequest(BaseModel):
    pass
