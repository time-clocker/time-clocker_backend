from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime
from app.db.session import get_session
from app.models.time_entry import TimeEntry
from app.models.employee import Employee
from app.models.pay_rule import PayRule
from app.schemas.reports import EmployeeSummary, GlobalSummary
from app.core.security import admin_required
from app.services.reports import _hours, apply_rule_per_entry

router = APIRouter(prefix="/reports", tags=["reports"])

async def _active_rule(session: AsyncSession, day: datetime) -> PayRule:
    # Regla cuyo rango incluye "day"
    q = await session.execute(select(PayRule).where(and_(PayRule.start_date <= day.date(), PayRule.end_date >= day.date())).limit(1))
    rule = q.scalar_one_or_none()
    if not rule:
        # fallback
        class R: daily_overtime_threshold_hours = 8.0; overtime_multiplier = 1.5
        return R()
    return rule

@router.get("/employee/{employee_id}", response_model=EmployeeSummary, dependencies=[Depends(admin_required)])
async def employee_summary(employee_id: str, start: datetime, end: datetime, session: AsyncSession = Depends(get_session)):
    emp = (await session.execute(select(Employee).where(Employee.id == employee_id))).scalar_one()
    rows = (await session.execute(
        select(TimeEntry).where(and_(TimeEntry.employee_id == emp.id, TimeEntry.clock_in >= start, TimeEntry.clock_in <= end, TimeEntry.clock_out.is_not(None)))
    )).scalars().all()

    total_hours = base_hours = overtime_hours = base_amount = overtime_amount = 0.0
    for r in rows:
        rule = await _active_rule(session, r.clock_in)
        h = _hours(r.clock_in, r.clock_out)
        b, o, ba, oa = apply_rule_per_entry(h, rule.daily_overtime_threshold_hours, rule.overtime_multiplier, emp.hourly_rate)
        total_hours += h; base_hours += b; overtime_hours += o; base_amount += ba; overtime_amount += oa

    return EmployeeSummary(
        employee_id=str(emp.id), start=start, end=end,
        total_hours=round(total_hours, 2),
        base_hours=round(base_hours, 2),
        overtime_hours=round(overtime_hours, 2),
        base_amount=round(base_amount, 2),
        overtime_amount=round(overtime_amount, 2),
        total_amount=round(base_amount + overtime_amount, 2),
    )

@router.get("/global", response_model=GlobalSummary, dependencies=[Depends(admin_required)])
async def global_summary(start: datetime, end: datetime, session: AsyncSession = Depends(get_session)):
    emps = (await session.execute(select(Employee).where(Employee.active.is_(True)))).scalars().all()
    items = []
    total_paid = 0.0
    for emp in emps:
        rows = (await session.execute(
            select(TimeEntry).where(and_(TimeEntry.employee_id == emp.id, TimeEntry.clock_in >= start, TimeEntry.clock_in <= end, TimeEntry.clock_out.is_not(None)))
        )).scalars().all()
        if not rows:
            continue
        total_hours = base_hours = overtime_hours = base_amount = overtime_amount = 0.0
        for r in rows:
            rule = await _active_rule(session, r.clock_in)
            h = _hours(r.clock_in, r.clock_out)
            b, o, ba, oa = apply_rule_per_entry(h, rule.daily_overtime_threshold_hours, rule.overtime_multiplier, emp.hourly_rate)
            total_hours += h; base_hours += b; overtime_hours += o; base_amount += ba; overtime_amount += oa
        total = base_amount + overtime_amount
        total_paid += total
        items.append({
            "employee_id": str(emp.id),
            "start": start, "end": end,
            "total_hours": round(total_hours, 2),
            "base_hours": round(base_hours, 2),
            "overtime_hours": round(overtime_hours, 2),
            "base_amount": round(base_amount, 2),
            "overtime_amount": round(overtime_amount, 2),
            "total_amount": round(total, 2),
        })
    return GlobalSummary(start=start, end=end, total_paid=round(total_paid, 2), employees=len(items), items=items)
