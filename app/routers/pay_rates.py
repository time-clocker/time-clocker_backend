# app/routers/pay_rates.py
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.security import admin_required   # usa tu dependencia de admin
from app.services.pay_rates_admin import set_rate_from, rollback_last_change

router = APIRouter(prefix="/pay-rates", tags=["pay-rates"])

class ChangeRateIn(BaseModel):
    start_date: date = Field(..., description="YYYY-MM-DD (vigencia inclusiva)")
    hourly_rate: float = Field(..., gt=0)
    employee_id: str | None = Field(None, description="NULL = global")

@router.post("/change", summary="Cambiar tarifa (global o por empleado) desde una fecha")
async def change_rate(body: ChangeRateIn, _admin=Depends(admin_required), session: AsyncSession = Depends(get_session)):
    try:
        rate = await set_rate_from(
            session,
            start_date=body.start_date,
            hourly_rate=body.hourly_rate,
            employee_id=body.employee_id,
        )
        await session.commit()
        return {
            "ok": True,
            "id": str(rate.id),
            "employee_id": body.employee_id,
            "start_date": rate.start_date,
            "end_date": rate.end_date,
            "hourly_rate": float(rate.hourly_rate),
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

class RollbackIn(BaseModel):
    effective_date: date
    employee_id: str | None = None

@router.post("/rollback", summary="Revertir el cambio que inicia en la fecha indicada")
async def rollback_rate(body: RollbackIn, _admin=Depends(admin_required), session: AsyncSession = Depends(get_session)):
    ok = await rollback_last_change(session, effective_date=body.effective_date, employee_id=body.employee_id)
    if ok:
        await session.commit()
        return {"ok": True}
    await session.rollback()
    raise HTTPException(status_code=404, detail="No se encontró cambio para esa fecha/empleado")
