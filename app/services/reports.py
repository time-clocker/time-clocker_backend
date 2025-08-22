from datetime import datetime, timedelta
from typing import List, Tuple
from app.models.time_entry import TimeEntry
from app.models.employee import Employee
from app.models.pay_rule import PayRule

def _hours(dt_start, dt_end) -> float:
    return max(0.0, (dt_end - dt_start).total_seconds() / 3600.0)

def apply_rule_per_entry(hours: float, threshold: float, multiplier: float, hourly_rate: float) -> Tuple[float, float, float, float]:
    base_hours = min(hours, threshold)
    overtime_hours = max(0.0, hours - threshold)
    base_amount = base_hours * hourly_rate
    overtime_amount = overtime_hours * hourly_rate * multiplier
    return base_hours, overtime_hours, base_amount, overtime_amount
