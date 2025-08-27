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
async def clock_in(
    payload: ClockInRequest,
    session: AsyncSession = Depends(get_session),
    employee=Depends(get_current_employee),
):

    q = await session.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.employee_id == employee.id,
                TimeEntry.clock_out.is_(None),
            )
        )
    )
    open_entry = q.scalar_one_or_none()
    if open_entry:
        raise HTTPException(
            status_code=409, detail="Ya existe un clock-in abierto para este usuario."
        )

    tz_name = getattr(payload, "tz", None) or "America/Bogota"
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        raise HTTPException(status_code=400, detail=f"Zona horaria inválida: {tz_name}")

    now_utc = datetime.now(tz).astimezone(timezone.utc)

    entry = TimeEntry(
        employee_id=employee.id,
        clock_in=now_utc,
        clock_out=None,
        tz=tz_name,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry

@router.post("/clock-out", response_model=TimeEntryOut)
async def clock_out(
    payload: ClockOutRequest,
    session: AsyncSession = Depends(get_session),
    employee=Depends(get_current_employee),
):
    # Buscar la entrada abierta
    q = await session.execute(
        select(TimeEntry).where(
            and_(
                TimeEntry.employee_id == employee.id,
                TimeEntry.clock_out.is_(None),
            )
        )
    )
    entry = q.scalar_one_or_none()
    if not entry:
        raise HTTPException(
            status_code=409, detail="No hay un clock-in abierto para cerrar."
        )

    # Cerrar con la misma zona horaria registrada en la fila
    try:
        tz = pytz.timezone(entry.tz)
    except Exception:
        tz = pytz.timezone("UTC")

    now_utc = datetime.now(tz).astimezone(timezone.utc)
    entry.clock_out = now_utc

    await session.commit()
    await session.refresh(entry)
    return entry

@router.get("/status")
async def clock_status(
    session: AsyncSession = Depends(get_session),
    employee=Depends(get_current_employee),
):
    q = await session.execute(
        select(TimeEntry)
        .where(
            and_(
                TimeEntry.employee_id == employee.id,
                TimeEntry.clock_out.is_(None),
            )
        )
        .order_by(TimeEntry.clock_in.desc())
    )
    entry = q.scalar_one_or_none()

    if not entry:
        return {"clocked_in": False, "entry": None}

    return {
        "clocked_in": True,
        "entry": TimeEntryOut.model_validate(entry, from_attributes=True),
    }

@router.get("", response_model=list[TimeEntryOut])
async def list_entries(
    employee_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_employee),  
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
    return list(res.scalars().all())
