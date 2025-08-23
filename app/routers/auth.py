from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from app.core.config import settings
from app.db.session import get_session
from app.models.employee import Employee
from app.core.security import get_current_user
from app.schemas.auth import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
)
from app.schemas.employee import EmployeeOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse, summary="Login")
async def login(body: LoginRequest) -> LoginResponse:
    if not settings.FIREBASE_WEB_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Missing FIREBASE_WEB_API_KEY in settings"
        )

    url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={settings.FIREBASE_WEB_API_KEY}"
    )
    payload = {
        "email": body.email,
        "password": body.password,
        "returnSecureToken": body.returnSecureToken,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=r.json())
        data = r.json()

    return LoginResponse(**data)

@router.post("/register", response_model=RegisterResponse, summary="Register")
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    if not settings.FIREBASE_WEB_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Missing FIREBASE_WEB_API_KEY in settings"
        )
    fb_signup_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signUp"
        f"?key={settings.FIREBASE_WEB_API_KEY}"
    )
    payload = {
        "email": body.email,
        "password": body.password,
        "returnSecureToken": True,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(fb_signup_url, json=payload)
        if r.status_code != 200:
            raise HTTPException(status_code=400, detail=r.json())
        fb = r.json()
    exists = await session.execute(select(Employee).where(Employee.email == body.email))
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already exists")

    emp = Employee(
        firebase_uid=fb["localId"],
        full_name=body.full_name,
        email=body.email,
        hourly_rate=body.hourly_rate if body.hourly_rate is not None else settings.DEFAULT_HOURLY_RATE,
        active=True,
    )
    session.add(emp)
    await session.commit()
    await session.refresh(emp)

    return RegisterResponse(
        employee=EmployeeOut.model_validate(emp),
        idToken=fb.get("idToken"),
        refreshToken=fb.get("refreshToken"),
        expiresIn=fb.get("expiresIn"),
        email=fb.get("email"),
        localId=fb.get("localId"),
    )

@router.get("/me", summary="Me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "role": user.get("role") or user.get("claims", {}).get("role"),
    }
