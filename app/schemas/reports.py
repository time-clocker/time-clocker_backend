from __future__ import annotations
from datetime import datetime  
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict

class RangeOut(BaseModel):
    from_: str = Field(alias="from")
    to: str
    timezone: str
    model_config = ConfigDict(populate_by_name=True)


class BarDay(BaseModel):
    date: str            
    hours_total: float   
    pay_total: float    


class PieHours(BaseModel):
    diurnal: float
    nocturnal: float
    extra: float
    total: float


class EmployeeMini(BaseModel):
    id: str
    full_name: str
    email: str
    hourly_rate: float


class EmployeeReportOut(BaseModel):
    employee: EmployeeMini
    range: RangeOut
    bar_by_day: List[BarDay]
    pie_hours: PieHours
    totals: Dict[str, float] 


class GlobalRow(BaseModel):
    employee_id: str
    full_name: str
    hours: PieHours
    pay_total: float


class GlobalReportOut(BaseModel):
    range: RangeOut
    rows: List[GlobalRow]
    totals: Dict[str, float]  

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
