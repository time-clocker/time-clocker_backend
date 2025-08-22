from pydantic import BaseModel
from datetime import datetime
from typing import List

class EmployeeSummary(BaseModel):
    employee_id: str
    total_hours: float
    base_hours: float
    overtime_hours: float
    base_amount: float
    overtime_amount: float
    total_amount: float
    start: datetime
    end: datetime

class GlobalSummary(BaseModel):
    start: datetime
    end: datetime
    total_paid: float
    employees: int
    items: List[EmployeeSummary]
