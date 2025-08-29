from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from firebase_admin import auth as fb_auth
import httpx, re
from app.db.session import get_session
from app.core.config import settings
from app.models.employee import Employee
from app.schemas.employee import EmployeeOut
from app.schemas.auth import RegisterRequest, RegisterResponse, LoginRequest, LoginResponse
from app.core.security import get_current_user  

router = APIRouter(prefix="/auth", tags=["auth"])

def validate_password(password: str):
    """
    Valida que la contraseña cumpla con:
    - Mínimo 6 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un símbolo especial
    Lanza HTTPException 422 si no cumple.
    """
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="Password muy corta (<6)")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=422, detail="Password sin mayúscula")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=422, detail="Password sin minúscula")
    if not re.search(r"[0-9]", password):
        raise HTTPException(status_code=422, detail="Password sin número")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=422, detail="Password sin símbolo")

async def _firebase_sign_in(email: str, password: str) -> dict:
    """
    Inicia sesión en Firebase y retorna los tokens.
    Lanza HTTPException 400 si falla.
    """
    url = (
        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        f"?key={settings.FIREBASE_WEB_API_KEY}"
    )
    payload = {"email": email, "password": password, "returnSecureToken": True}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=r.json())
    return r.json()

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest) -> LoginResponse:
    """
    Endpoint de login. Retorna tokens de Firebase y datos del usuario.
    """
    data = await _firebase_sign_in(body.email, body.password)
    return LoginResponse(
        idToken=data.get("idToken"),
        refreshToken=data.get("refreshToken"),
        expiresIn=data.get("expiresIn"),
        email=data.get("email"),
        localId=data.get("localId"),
    )

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)) -> RegisterResponse:
    """
    Registra un nuevo empleado.
    Valida contraseña, email y documento.
    Crea usuario en Firebase y registro en DB.
    Retorna tokens y datos del empleado.
    Lanza HTTPException 422 si la contraseña no cumple reglas.
    Lanza HTTPException 409 si email o documento ya existen.
    """
    validate_password(body.password)

    q = await session.execute(select(Employee).where(Employee.email == body.email))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    q = await session.execute(select(Employee).where(Employee.doc_number == body.doc_number))
    if q.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Document already registered")

    try:
        fb_user = fb_auth.create_user(
            email=body.email,
            password=body.password,
            display_name=body.full_name,
            email_verified=False,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Firebase: {e}")

    try:
        emp = Employee(
            firebase_uid=fb_user.uid,
            full_name=body.full_name,
            email=body.email,
            doc_type=body.doc_type,
            doc_number=body.doc_number,
            hourly_rate=float(settings.DEFAULT_HOURLY_RATE),
            active=True,
        )
        session.add(emp)
        await session.commit()
        await session.refresh(emp)
    except Exception as e:
        try:
            fb_auth.delete_user(fb_user.uid)
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=f"DB error: {e}")

    tokens = await _firebase_sign_in(body.email, body.password)

    return RegisterResponse(
        employee=EmployeeOut.model_validate(emp),
        idToken=tokens.get("idToken"),
        refreshToken=tokens.get("refreshToken"),
        expiresIn=tokens.get("expiresIn"),
        email=tokens.get("email"),
        localId=tokens.get("localId"),
    )

@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    """
    Retorna información del usuario actualmente autenticado.
    """
    return user
