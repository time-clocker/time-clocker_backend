from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from uuid import UUID
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.db.session import get_session
from app.models.employee import Employee
from app.models.pay_rate import PayRate 
from app.core.security import admin_required, get_current_employee
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeOut,
)

from firebase_admin import auth as fb_auth
try:
    from firebase_admin.auth import UserNotFoundError
except Exception:
    from firebase_admin._auth_utils import UserNotFoundError 

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("/", response_model=list[EmployeeOut], summary="List Employees (admin)")
async def list_employees(
    q: str | None = Query(None, description="Buscar por nombre o email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Employee).order_by(Employee.created_at.desc())
    if q:
        patt = f"%{q.lower()}%"
        stmt = stmt.where(
            and_(
                (Employee.full_name.ilike(patt)) | (Employee.email.ilike(patt))
            )
        )
    stmt = stmt.limit(limit).offset(offset)
    rows = await session.execute(stmt)
    return rows.scalars().all()


@router.get("/{employee_id}", response_model=EmployeeOut, summary="Get Employee (admin)")
async def get_employee(
    employee_id: UUID,
    _admin=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(Employee).where(Employee.id == employee_id))
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED, summary="Create Employee (admin)")
async def create_employee(
    body: EmployeeCreate,
    _admin=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    exists = await session.execute(select(Employee).where(Employee.email == body.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    emp = Employee(
        firebase_uid=body.firebase_uid,
        full_name=body.full_name,
        email=body.email,
        hourly_rate=body.hourly_rate if body.hourly_rate is not None else 15000.0,
        active=True if body.active is None else body.active,
    )
    session.add(emp)
    await session.commit()
    await session.refresh(emp)
    return emp


@router.patch("/{employee_id}", response_model=EmployeeOut, summary="Update Employee (admin)")
async def update_employee(
    employee_id: UUID,
    body: EmployeeUpdate,
    _admin=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(Employee).where(Employee.id == employee_id))
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    prev_hourly = float(emp.hourly_rate or 0.0)

    if body.full_name is not None:
        emp.full_name = body.full_name

    if body.email is not None:
        exists = await session.execute(
            select(Employee).where(and_(Employee.email == body.email, Employee.id != employee_id))
        )
        if exists.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")
        emp.email = body.email

    rate_changed = False
    if body.hourly_rate is not None:
        new_rate = float(body.hourly_rate)
        rate_changed = (new_rate != prev_hourly)
        emp.hourly_rate = new_rate  

    if body.active is not None:
        emp.active = body.active

    if rate_changed:
        today = datetime.now(ZoneInfo("America/Bogota")).date()
        yesterday = today - timedelta(days=1)
        current_rate_stmt = (
            select(PayRate)
            .where(
                and_(
                    PayRate.employee_id == emp.id,
                    PayRate.start_date <= today,
                    or_(PayRate.end_date.is_(None), PayRate.end_date >= today),
                )
            )
            .order_by(PayRate.start_date.desc())
            .limit(1)
        )
        cur = (await session.execute(current_rate_stmt)).scalars().first()
        if cur and cur.end_date is None:
            cur.end_date = yesterday

        new_pr = PayRate(
            employee_id=emp.id,        
            hourly_rate=emp.hourly_rate,
            start_date=today,
            end_date=None,              
        )
        session.add(new_pr)

    await session.commit()
    await session.refresh(emp)
    return emp


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Employee (admin)")
async def delete_employee(
    employee_id: UUID,
    soft: bool = Query(False, description="Si es true, solo desactiva en BD (soft delete)"),
    _admin=Depends(admin_required),
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(Employee).where(Employee.id == employee_id))
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    if soft:
        if emp.active:
            emp.active = False
            await session.commit()
        return None
    if emp.firebase_uid:
        try:
            fb_auth.delete_user(emp.firebase_uid)
        except UserNotFoundError:
            pass
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete user in Firebase Auth: {str(e)}",
            )
    await session.delete(emp)
    await session.commit()
    return None


@router.get("/me/profile", response_model=EmployeeOut, summary="My Profile (employee)")
async def my_profile(
    current_emp=Depends(get_current_employee),
):
    return current_emp
