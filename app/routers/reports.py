from __future__ import annotations

from datetime import datetime
from typing import Dict, List

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

    # empleados activos
    employees: List[Employee] = (
        await session.execute(select(Employee).where(Employee.active.is_(True)))
    ).scalars().all()
    if not employees:
        return {
            "range": {"from": start.date().isoformat(), "to": end.date().isoformat(), "timezone": timezone},
            "rows": [],
            "totals": {"hours_total": 0.0, "pay_total": 0.0},
        }

    # time entries por empleado en el rango
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
