# app/services/pay_rates_admin.py
from __future__ import annotations
from datetime import date, timedelta
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pay_rate import PayRate

SENTINEL = None  # global

async def _fetch_active_on(session: AsyncSession, employee_id: Optional[str], at: date):
    q = (
        select(PayRate)
        .where(
            and_(
                (PayRate.employee_id == employee_id) if employee_id else PayRate.employee_id.is_(SENTINEL),
                PayRate.start_date <= at,
                PayRate.end_date >= at,
            )
        )
        .order_by(PayRate.start_date.desc())
        .limit(1)
    )
    return (await session.execute(q)).scalar_one_or_none()

async def _fetch_prev_before(session: AsyncSession, employee_id: Optional[str], at: date):
    q = (
        select(PayRate)
        .where(
            and_(
                (PayRate.employee_id == employee_id) if employee_id else PayRate.employee_id.is_(SENTINEL),
                PayRate.end_date < at,
            )
        )
        .order_by(PayRate.end_date.desc())
        .limit(1)
    )
    return (await session.execute(q)).scalar_one_or_none()

async def _fetch_next_after(session: AsyncSession, employee_id: Optional[str], at: date):
    q = (
        select(PayRate)
        .where(
            and_(
                (PayRate.employee_id == employee_id) if employee_id else PayRate.employee_id.is_(SENTINEL),
                PayRate.start_date > at,
            )
        )
        .order_by(PayRate.start_date.asc())
        .limit(1)
    )
    return (await session.execute(q)).scalar_one_or_none()

async def set_rate_from(session: AsyncSession, *, start_date: date, hourly_rate: float, employee_id: Optional[str] = None):
    """Cierra vigencia anterior, crea nueva (sin solapes) y fusiona si la siguiente tiene el mismo valor."""
    if start_date is None:
        raise ValueError("start_date es obligatorio")

    active = await _fetch_active_on(session, employee_id, start_date)
    if active and float(active.hourly_rate) == float(hourly_rate) and active.start_date == start_date:
        return active  # idempotente

    if active:
        if float(active.hourly_rate) != float(hourly_rate) and active.start_date < start_date:
            active.end_date = start_date - timedelta(days=1)
            session.add(active)
    else:
        prev = await _fetch_prev_before(session, employee_id, start_date)
        if prev and prev.end_date >= start_date:
            prev.end_date = start_date - timedelta(days=1)
            session.add(prev)

    new_rate = PayRate(
        employee_id=employee_id,
        start_date=start_date,
        end_date=date(2099, 12, 31),
        hourly_rate=hourly_rate,
    )
    session.add(new_rate)

    next_row = await _fetch_next_after(session, employee_id, start_date)
    if next_row and float(next_row.hourly_rate) == float(hourly_rate):
        new_rate.end_date = next_row.end_date
        await session.flush()
        await session.delete(next_row)

    await session.flush()
    return new_rate

async def rollback_last_change(session: AsyncSession, *, effective_date: date, employee_id: Optional[str] = None):
    """Deshacer el cambio que inició en effective_date (borra fila y re-extiende la anterior)."""
    q_exact = select(PayRate).where(
        and_(
            (PayRate.employee_id == employee_id) if employee_id else PayRate.employee_id.is_(SENTINEL),
            PayRate.start_date == effective_date,
        )
    ).limit(1)
    current = (await session.execute(q_exact)).scalar_one_or_none()
    if not current:
        return False

    prev = await _fetch_prev_before(session, employee_id, effective_date)
    next_row = await _fetch_next_after(session, employee_id, effective_date)

    await session.delete(current)
    if prev:
        prev.end_date = next_row.end_date if next_row else date(2099, 12, 31)
        session.add(prev)

    await session.flush()
    return True
