from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Dict, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_session
from app.models.employee import Employee
from app.models.time_entry import TimeEntry
from app.schemas.reports import (
    EmployeeReportOut,
    GlobalReportOut,
)
from app.services.reports import (
    build_employee_report,
    build_global_report,
)

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_employee(session: AsyncSession, employee_id: str) -> Employee:
    q = await session.execute(select(Employee).where(Employee.id == employee_id))
    emp = q.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


def _authorize_employee_report(user: dict, emp: Employee) -> None:
    role = user.get("role") or user.get("claims", {}).get("role")
    if role == "admin":
        return
    if user.get("uid") == emp.firebase_uid:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

def _month_bounds(year: int, month: int, tz: str) -> tuple[datetime, datetime]:
    tzinfo = ZoneInfo(tz)
    start = datetime(year, month, 1, 0, 0, 0, tzinfo=tzinfo)
    if month == 12:
        next_month = datetime(year + 1, 1, 1, tzinfo=tzinfo)
    else:
        next_month = datetime(year, month + 1, 1, tzinfo=tzinfo)
    end = next_month - timedelta(seconds=1)
    return start, end


def _week_bounds_sun_to_sat(ref: datetime, tz: str) -> tuple[datetime, datetime]:
    ref_local = ref.astimezone(ZoneInfo(tz))
    d = ref_local.date()
    days_since_sunday = (ref_local.weekday() + 1) % 7
    start_date = d - timedelta(days=days_since_sunday)  
    end_date = start_date + timedelta(days=6)           
    tzinfo = ZoneInfo(tz)
    start_dt = datetime.combine(start_date, time(0, 0, 0), tzinfo=tzinfo)
    end_dt = datetime.combine(end_date, time(23, 59, 59), tzinfo=tzinfo)
    return start_dt, end_dt

@router.get(
    "/employee/{employee_id}",
    response_model=EmployeeReportOut,
    summary="Employee report (bars by day + pie hours)",
)
async def employee_report(
    employee_id: str,
    start: datetime = Query(..., description="Start datetime (inclusive)"),
    end: datetime = Query(..., description="End datetime (inclusive)"),
    timezone: str = Query(settings.DEFAULT_TIMEZONE, description="IANA timezone, e.g. America/Bogota"),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(get_current_user),
):
    emp = await _get_employee(session, employee_id)
    _authorize_employee_report(user, emp)

    rows = (
        await session.execute(
            select(TimeEntry).where(
                and_(
                    TimeEntry.employee_id == emp.id,
                    TimeEntry.clock_in >= start,
                    TimeEntry.clock_in <= end,
                    TimeEntry.clock_out.is_not(None),
                )
            )
        )
    ).scalars().all()

    payload = build_employee_report(
        employee=emp,
        entries=rows,
        start=start,
        end=end,
        timezone=timezone,
    )
    return payload


@router.get(
    "/global",
    response_model=GlobalReportOut,
    summary="Global report for admin (table per employee)",
)
async def global_report(
    start: datetime = Query(..., description="Start datetime (inclusive)"),
    end: datetime = Query(..., description="End datetime (inclusive)"),
    timezone: str = Query(settings.DEFAULT_TIMEZONE, description="IANA timezone, e.g. America/Bogota"),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(get_current_user),
):
    role = user.get("role") or user.get("claims", {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    employees: List[Employee] = (
        await session.execute(
            select(Employee).where(
                and_(
                    Employee.active.is_(True),
                    Employee.hourly_rate > 0,
                    Employee.firebase_uid != user.get("uid"),
                )
            )
        )
    ).scalars().all()
    if not employees:
        return {
            "range": {"from": start.date().isoformat(), "to": end.date().isoformat(), "timezone": timezone},
            "rows": [],
            "totals": {"hours_total": 0.0, "pay_total": 0.0},
        }

    entries_by_emp: Dict[str, List[TimeEntry]] = {}
    emp_ids = [e.id for e in employees]
    all_rows = (
        await session.execute(
            select(TimeEntry).where(
                and_(
                    TimeEntry.employee_id.in_(emp_ids),
                    TimeEntry.clock_in >= start,
                    TimeEntry.clock_in <= end,
                    TimeEntry.clock_out.is_not(None),
                )
            )
        )
    ).scalars().all()

    for r in all_rows:
        key = str(r.employee_id)
        entries_by_emp.setdefault(key, []).append(r)

    payload = build_global_report(
        employees=employees,
        entries_by_employee=entries_by_emp,
        start=start,
        end=end,
        timezone=timezone,
    )
    return payload
@router.get(
    "/global/monthly",
    response_model=GlobalReportOut,
    summary="Global (admin): totales del mes por empleado",
)
async def global_report_monthly(
    year: int,
    month: int,
    timezone: str = Query(settings.DEFAULT_TIMEZONE),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(get_current_user),
):
    role = user.get("role") or user.get("claims", {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    start, end = _month_bounds(year, month, timezone)
    employees: List[Employee] = (
        await session.execute(
            select(Employee).where(
                and_(
                    Employee.active.is_(True),
                    Employee.hourly_rate > 0,
                    Employee.firebase_uid != user.get("uid"),
                )
            )
        )
    ).scalars().all()

    if not employees:
        return {
            "range": {"from": start.date().isoformat(), "to": end.date().isoformat(), "timezone": timezone},
            "rows": [],
            "totals": {"hours_total": 0.0, "pay_total": 0.0},
        }

    emp_ids = [e.id for e in employees]
    all_rows = (
        await session.execute(
            select(TimeEntry).where(
                and_(
                    TimeEntry.employee_id.in_(emp_ids),
                    TimeEntry.clock_in >= start,
                    TimeEntry.clock_in <= end,
                    TimeEntry.clock_out.is_not(None),
                )
            )
        )
    ).scalars().all()

    entries_by_emp: Dict[str, List[TimeEntry]] = {}
    for r in all_rows:
        entries_by_emp.setdefault(str(r.employee_id), []).append(r)

    return build_global_report(
        employees=employees,
        entries_by_employee=entries_by_emp,
        start=start,
        end=end,
        timezone=timezone,
    )


@router.get(
    "/employee/{employee_id}/weekly",
    response_model=EmployeeReportOut,
    summary="Empleado: reporte semanal (domingo a sábado)",
)
async def employee_report_weekly(
    employee_id: str,
    ref_date: datetime = Query(None, description="Referencia; por defecto 'ahora'"),
    timezone: str = Query(settings.DEFAULT_TIMEZONE),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(get_current_user),
):
    emp = await _get_employee(session, employee_id)
    _authorize_employee_report(user, emp)

    if ref_date is None:
        ref_date = datetime.now(tz=ZoneInfo(timezone))
    start, end = _week_bounds_sun_to_sat(ref_date, timezone)

    rows = (
        await session.execute(
            select(TimeEntry).where(
                and_(
                    TimeEntry.employee_id == emp.id,
                    TimeEntry.clock_in >= start,
                    TimeEntry.clock_in <= end,
                    TimeEntry.clock_out.is_not(None),
                )
            )
        )
    ).scalars().all()

    return build_employee_report(
        employee=emp,
        entries=rows,
        start=start,
        end=end,
        timezone=timezone,
    )


@router.get(
    "/employee/{employee_id}/monthly",
    response_model=EmployeeReportOut,
    summary="Empleado: reporte mensual",
)
async def employee_report_monthly(
    employee_id: str,
    year: int,
    month: int,
    timezone: str = Query(settings.DEFAULT_TIMEZONE),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(get_current_user),
):
    emp = await _get_employee(session, employee_id)
    _authorize_employee_report(user, emp)

    start, end = _month_bounds(year, month, timezone)

    rows = (
        await session.execute(
            select(TimeEntry).where(
                and_(
                    TimeEntry.employee_id == emp.id,
                    TimeEntry.clock_in >= start,
                    TimeEntry.clock_in <= end,
                    TimeEntry.clock_out.is_not(None),
                )
            )
        )
    ).scalars().all()

    return build_employee_report(
        employee=emp,
        entries=rows,
        start=start,
        end=end,
        timezone=timezone,
    )


@router.get(
    "/employee/{employee_id}/yearly",
    summary="Empleado: resumen por mes del año (horas y pago por mes)",
)
async def employee_report_yearly(
    employee_id: str,
    year: int,
    timezone: str = Query(settings.DEFAULT_TIMEZONE),
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(get_current_user),
):
    emp = await _get_employee(session, employee_id)
    _authorize_employee_report(user, emp)

    months: List[dict] = []
    for month in range(1, 12 + 1):
        start, end = _month_bounds(year, month, timezone)
        rows = (
            await session.execute(
                select(TimeEntry).where(
                    and_(
                        TimeEntry.employee_id == emp.id,
                        TimeEntry.clock_in >= start,
                        TimeEntry.clock_in <= end,
                        TimeEntry.clock_out.is_not(None),
                    )
                )
            )
        ).scalars().all()

        rep = build_employee_report(
            employee=emp, entries=rows, start=start, end=end, timezone=timezone
        )
        months.append({
            "year": year,
            "month": month,
            "hours_total": rep["totals"]["hours_total"],
            "pay_total": rep["totals"]["pay_total"],
        })

    return {
        "employee": {
            "id": str(emp.id),
            "full_name": emp.full_name,
            "email": emp.email,
            "hourly_rate": float(emp.hourly_rate),
        },
        "year": year,
        "timezone": timezone,
        "months": months,
    }
