from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Iterable, List, Tuple, Optional

from sqlalchemy import select, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pay_rate import PayRate
from app.models.employee import Employee

SENTINEL_EMP = None 

async def resolve_hourly_rate(session: AsyncSession, employee_id, at_ts: datetime | date) -> float:

    at_date = at_ts.date() if isinstance(at_ts, datetime) else at_ts

    is_global = case((PayRate.employee_id.is_(None), 1), else_=0)

    q = (
        select(PayRate.hourly_rate, PayRate.employee_id)
        .where(
            and_(
                or_(PayRate.employee_id == employee_id, PayRate.employee_id.is_(SENTINEL_EMP)),
                PayRate.start_date <= at_date,
                or_(PayRate.end_date.is_(None), PayRate.end_date >= at_date),
            )
        )
        .order_by(
            is_global.asc(),           
            PayRate.start_date.desc(), 
        )
        .limit(1)
    )

    row = (await session.execute(q)).first()
    if row:
        rate, _ = row
        return float(rate)

    emp_rate = (
        await session.execute(
            select(Employee.hourly_rate).where(Employee.id == employee_id).limit(1)
        )
    ).scalar_one_or_none()
    return float(emp_rate or 0.0)


async def find_rate_boundaries(
    session: AsyncSession,
    employee_id,
    start_ts: datetime,
    end_ts: datetime,
) -> List[datetime]:
    if end_ts <= start_ts:
        return []

    start_d, end_d = start_ts.date(), end_ts.date()

    rows = (
        await session.execute(
            select(PayRate.start_date, PayRate.end_date).where(
                and_(
                    or_(PayRate.employee_id == employee_id, PayRate.employee_id.is_(SENTINEL_EMP)),
                    PayRate.start_date <= end_d,
                    or_(PayRate.end_date.is_(None), PayRate.end_date >= start_d),
                )
            )
        )
    ).all()

    cuts: set[datetime] = set()
    for s_d, e_d in rows:
        cuts.add(datetime.combine(s_d, datetime.min.time(), tzinfo=start_ts.tzinfo))
        if e_d is not None:
            cuts.add(datetime.combine(e_d + timedelta(days=1), datetime.min.time(), tzinfo=start_ts.tzinfo))

    return sorted([c for c in cuts if start_ts < c < end_ts])


def split_by_boundaries(
    start_ts: datetime,
    end_ts: datetime,
    boundaries: Iterable[datetime],
) -> List[Tuple[datetime, datetime]]:
    if end_ts <= start_ts:
        return []
    points = [start_ts] + [b for b in boundaries if start_ts < b < end_ts] + [end_ts]
    points.sort()
    return [(points[i], points[i + 1]) for i in range(len(points) - 1) if points[i + 1] > points[i]]


async def compute_amount_for_entry(
    session: AsyncSession,
    employee_id,
    clock_in: datetime,
    clock_out: Optional[datetime],
) -> float:

    if not clock_out or clock_out <= clock_in:
        return 0.0

    boundaries = await find_rate_boundaries(session, employee_id, clock_in, clock_out)
    segments = split_by_boundaries(clock_in, clock_out, boundaries)

    total = 0.0
    for seg_start, seg_end in segments:
        rate = await resolve_hourly_rate(session, employee_id, seg_start)
        hours = (seg_end - seg_start).total_seconds() / 3600.0
        total += rate * hours

    return total
