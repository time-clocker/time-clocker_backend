from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timezone
from app.db.session import get_session
from app.schemas.time_entry import ClockInRequest, ClockOutRequest, TimeEntryOut
from app.models.time_entry import TimeEntry
from app.core.security import get_current_employee
import pytz

router = APIRouter(prefix="/time-entries", tags=["time-entries"])

@router.post("/clock-in", response_model=TimeEntryOut)
async def clock_in(payload: ClockInRequest, session: AsyncSession = Depends(get_session), employee=Depends(get_current_employee)):
    # Evitar dos entradas abiertas
    q = await session.execute(select(TimeEntry).where(and_(TimeEntry.employee_id == employee.id, TimeEntry.clock_out.is_(None))))
    open_entry = q.scalar_one_or_none()
    if open_entry:
        raise HTTPException(status_code=409, detail="You already have an open time entry")

    tz = pytz.timezone(payload.tz)
    now = datetime.now(tz).astimezone(timezone.utc)

    entry = TimeEntry(employee_id=employee.id, clock_in=now, tz=payload.tz)
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry

@router.post("/clock-out", response_model=TimeEntryOut)
async def clock_out(payload: ClockOutRequest, session: AsyncSession = Depends(get_session), employee=Depends(get_current_employee)):
    q = await session.execute(select(TimeEntry).where(and_(TimeEntry.employee_id == employee.id, TimeEntry.clock_out.is_(None))).order_by(TimeEntry.clock_in.desc()))
    entry = q.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=409, detail="No open time entry to close")

    tz = pytz.timezone(entry.tz)
    now = datetime.now(tz).astimezone(timezone.utc)

    entry.clock_out = now
    await session.commit()
    await session.refresh(entry)
    return entry

@router.get("", response_model=list[TimeEntryOut])
async def list_entries(
    employee_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_employee)  # empleado autenticado (empleado o admin con claims)
):
    stmt = select(TimeEntry)
    if employee_id:
        stmt = stmt.where(TimeEntry.employee_id == employee_id)
    if start:
        stmt = stmt.where(TimeEntry.clock_in >= start)
    if end:
        stmt = stmt.where(TimeEntry.clock_in <= end)
    stmt = stmt.order_by(TimeEntry.clock_in.desc())
    res = await session.execute(stmt)
    return res.scalars().all()
