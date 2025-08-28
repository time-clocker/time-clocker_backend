from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time, date
from decimal import Decimal
from typing import Dict, List, Tuple, Iterable
from zoneinfo import ZoneInfo

from app.models.time_entry import TimeEntry
from app.models.employee import Employee
from app.models.pay_rule import PayRule  
DAY_START = time(6, 0, 0)   
DAY_END = time(21, 0, 0)    
DAILY_BASE_LIMIT_HOURS = 8.0

MULTIPLIER_DAY = 1.00
MULTIPLIER_NIGHT = 1.35
MULTIPLIER_EXTRA_DAY = 1.25
MULTIPLIER_EXTRA_NIGHT = 1.75

MULTIPLIER_SUNDAY_DAY = 1.75
MULTIPLIER_SUNDAY_NIGHT = 2.10
MULTIPLIER_SUNDAY_EXTRA_DAY = 2.00
MULTIPLIER_SUNDAY_EXTRA_NIGHT = 2.50


def _hours(dt_start: datetime, dt_end: datetime) -> float:
    return max(0.0, (dt_end - dt_start).total_seconds() / 3600.0)


def _round2(x: float) -> float:
    return float(Decimal(x).quantize(Decimal("0.01")))


def _daterange(d0: date, d1: date) -> Iterable[date]:
    cur = d0
    while cur <= d1:
        yield cur
        cur += timedelta(days=1)


def _localize(dt: datetime, tz: str) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo(tz))
    return dt.astimezone(ZoneInfo(tz))


def _clamp(a: datetime, b: datetime, lo: datetime, hi: datetime) -> Tuple[datetime, datetime] | None:
    start = max(a, lo)
    end = min(b, hi)
    if end <= start:
        return None
    return start, end


@dataclass
class Segment:
    day: date          
    kind: str          
    hours: float
    is_sunday: bool    


def _split_by_day_and_shift(start: datetime, end: datetime, tz: str) -> List[Segment]:

    start_local = _localize(start, tz)
    end_local = _localize(end, tz)

    segments: List[Segment] = []
    first_day = start_local.date()
    last_day = end_local.date()

    for day in _daterange(first_day, last_day):
        day_start = datetime.combine(day, time(0, 0), tzinfo=ZoneInfo(tz))
        day_end = day_start + timedelta(days=1)

        clipped = _clamp(start_local, end_local, day_start, day_end)
        if not clipped:
            continue
        lo, hi = clipped

        is_sunday = day_start.isoweekday() == 7 

        a1 = datetime.combine(day, DAY_START, tzinfo=ZoneInfo(tz))  
        a2 = datetime.combine(day, DAY_END, tzinfo=ZoneInfo(tz))   

        if inter := _clamp(lo, hi, day_start, a1):
            segments.append(Segment(day, "night", _hours(*inter), is_sunday))

        if inter := _clamp(lo, hi, a1, a2):
            segments.append(Segment(day, "day", _hours(*inter), is_sunday))

        if inter := _clamp(lo, hi, a2, day_end):
            segments.append(Segment(day, "night", _hours(*inter), is_sunday))

    return segments


def _allocate_daily_extra(segments: List[Segment]) -> Dict[date, Dict[str, float]]:
    by_day: Dict[date, List[Segment]] = {}
    for s in segments:
        by_day.setdefault(s.day, []).append(s)

    out: Dict[date, Dict[str, float | bool]] = {}

    for d, segs in by_day.items():
        segs = list(segs) 
        sum_day = sum(s.hours for s in segs if s.kind == "day")
        sum_night = sum(s.hours for s in segs if s.kind == "night")
        total = sum_day + sum_night

        extra = 0.0
        if total > DAILY_BASE_LIMIT_HOURS:
            excess = total - DAILY_BASE_LIMIT_HOURS
            rest = excess
            for s in reversed(segs):
                take = min(s.hours, rest)
                s.hours -= take
                rest -= take
                extra += take
                if rest <= 0:
                    break
            sum_day = sum(s.hours for s in segs if s.kind == "day")
            sum_night = sum(s.hours for s in segs if s.kind == "night")

        is_sunday = all(s.is_sunday for s in segs) if segs else False

        out[d] = {
            "day": _round2(sum_day),
            "night": _round2(sum_night),
            "extra": _round2(extra),
            "total": _round2(sum_day + sum_night + extra),
            "sunday": is_sunday,
        }

    return out


def _pay_bucket(bucket: Dict[str, float | bool], hourly_rate: float) -> float:

    h_day = float(bucket["day"])
    h_night = float(bucket["night"])
    h_extra = float(bucket["extra"])
    is_sunday = bool(bucket.get("sunday", False))

    if is_sunday:
        pay = (
            h_day * hourly_rate * MULTIPLIER_SUNDAY_DAY +
            h_night * hourly_rate * MULTIPLIER_SUNDAY_NIGHT
        )

        base_total = h_day + h_night
        if base_total > 0:
            share_day = h_day / base_total
            share_night = h_night / base_total
        else:
            share_day = 1.0
            share_night = 0.0
        pay += (
            h_extra * share_day * hourly_rate * MULTIPLIER_SUNDAY_EXTRA_DAY +
            h_extra * share_night * hourly_rate * MULTIPLIER_SUNDAY_EXTRA_NIGHT
        )
    else:
        pay = (
            h_day * hourly_rate * MULTIPLIER_DAY +
            h_night * hourly_rate * MULTIPLIER_NIGHT
        )
        base_total = h_day + h_night
        if base_total > 0:
            share_day = h_day / base_total
            share_night = h_night / base_total
        else:
            share_day = 1.0
            share_night = 0.0
        pay += (
            h_extra * share_day * hourly_rate * MULTIPLIER_EXTRA_DAY +
            h_extra * share_night * hourly_rate * MULTIPLIER_EXTRA_NIGHT
        )

    return _round2(pay)

def build_employee_report(
    employee: Employee,
    entries: List[TimeEntry],
    start: datetime,
    end: datetime,
    timezone: str,
) -> dict:

    all_segments: List[Segment] = []
    for te in entries:
        if not te.clock_out:
            continue
        all_segments.extend(_split_by_day_and_shift(te.clock_in, te.clock_out, timezone))

    per_day = _allocate_daily_extra(all_segments)

    bar: List[dict] = []
    pie_diurnal = pie_night = pie_extra = 0.0
    hours_total = 0.0
    pay_total = 0.0

    start_local = _localize(start, timezone).date()
    end_local = _localize(end, timezone).date()

    for d in _daterange(start_local, end_local):
        bucket = per_day.get(d, {"day": 0.0, "night": 0.0, "extra": 0.0, "sunday": False})
        h_day = float(bucket["day"])
        h_night = float(bucket["night"])
        h_extra = float(bucket["extra"])
        h_total = _round2(h_day + h_night + h_extra)
        day_pay = _pay_bucket(bucket, employee.hourly_rate)

        bar.append({
            "date": d.isoformat(),
            "hours_total": h_total,
            "pay_total": day_pay,
        })

        pie_diurnal += h_day
        pie_night += h_night
        pie_extra += h_extra
        hours_total += h_total
        pay_total += day_pay

    return {
        "employee": {
            "id": str(employee.id),
            "full_name": employee.full_name,
            "email": employee.email,
            "hourly_rate": float(employee.hourly_rate),
        },
        "range": {
            "from": _localize(start, timezone).date().isoformat(),
            "to": _localize(end, timezone).date().isoformat(),
            "timezone": timezone,
        },
        "bar_by_day": bar,
        "pie_hours": {
            "diurnal": _round2(pie_diurnal),
            "nocturnal": _round2(pie_night),
            "extra": _round2(pie_extra),
            "total": _round2(hours_total),
        },
        "totals": {
            "hours_total": _round2(hours_total),
            "pay_total": _round2(pay_total),
        },
    }


def build_global_report(
    employees: List[Employee],
    entries_by_employee: Dict[str, List[TimeEntry]],
    start: datetime,
    end: datetime,
    timezone: str,
) -> dict:
    rows: List[dict] = []
    total_hours = 0.0
    total_pay = 0.0

    for emp in employees:
        segs: List[Segment] = []
        for te in entries_by_employee.get(str(emp.id), []):
            if not te.clock_out:
                continue
            segs.extend(_split_by_day_and_shift(te.clock_in, te.clock_out, timezone))

        per_day = _allocate_daily_extra(segs)

        di, ni, ex = 0.0, 0.0, 0.0
        pay = 0.0
        for bucket in per_day.values():
            di += float(bucket["day"])
            ni += float(bucket["night"])
            ex += float(bucket["extra"])
            pay += _pay_bucket(bucket, emp.hourly_rate)

        row_total_h = _round2(di + ni + ex)

        rows.append({
            "employee_id": str(emp.id),
            "full_name": emp.full_name,
            "hours": {
                "diurnal": _round2(di),
                "nocturnal": _round2(ni),
                "extra": _round2(ex),
                "total": row_total_h,
            },
            "pay_total": _round2(pay),
        })

        total_hours += row_total_h
        total_pay += pay

    return {
        "range": {
            "from": _localize(start, timezone).date().isoformat(),
            "to": _localize(end, timezone).date().isoformat(),
            "timezone": timezone,
        },
        "rows": rows,
        "totals": {
            "hours_total": _round2(total_hours),
            "pay_total": _round2(total_pay),
        },
    }

def apply_rule_per_entry(
    hours: float, threshold: float, multiplier: float, hourly_rate: float
) -> Tuple[float, float, float, float]:
    base_hours = min(hours, threshold)
    overtime_hours = max(0.0, hours - threshold)
    base_amount = base_hours * hourly_rate
    overtime_amount = overtime_hours * hourly_rate * multiplier
    return (
        _round2(base_hours),
        _round2(overtime_hours),
        _round2(base_amount),
        _round2(overtime_amount),
    )
