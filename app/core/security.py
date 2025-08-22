from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.employee import Employee
from sqlalchemy import select

bearer_scheme = HTTPBearer(auto_error=True)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    token = credentials.credentials
    try:
        decoded = auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return decoded 

async def get_current_employee(
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Employee:
    q = await session.execute(select(Employee).where(Employee.firebase_uid == user["uid"]))
    emp = q.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=403, detail="Employee not registered in system")
    return emp

def admin_required(user: dict = Depends(get_current_user)):
    role = user.get("role") or user.get("claims", {}).get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
