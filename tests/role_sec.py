import pytest
import httpx
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_admin_only_access():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 🔹 Login admin
        admin_login = await client.post("/auth/login", json={
            "email": "pandoraadmin@example.com",
            "password": "pandora"
        })
        admin_login.raise_for_status()
        admin_token = admin_login.json()["idToken"]

        # 🔹 Login empleado
        emp_login = await client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "Thomas123!"
        })
        emp_login.raise_for_status()
        emp_token = emp_login.json()["idToken"]

        # Fechas para el reporte
        start = (datetime.now() - timedelta(days=7)).isoformat()
        end = datetime.now().isoformat()

        # 🔹 Empleado intenta acceder -> debe fallar
        emp_access = await client.get(
            "/reports/global",
            headers={"Authorization": f"Bearer {emp_token}"},
            params={
                "start": start,
                "end": end,
                "timezone": "America/Bogota"
            }
        )
        assert emp_access.status_code == 403  # Forbidden

        # 🔹 Admin accede -> debe pasar
        admin_access = await client.get(
            "/reports/global",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={
                "start": start,
                "end": end,
                "timezone": "America/Bogota"
            }
        )
        assert admin_access.status_code == 200
        data = admin_access.json()

        # ✅ Validación correcta según la estructura real
        assert isinstance(data, dict)
        assert "range" in data
        assert "rows" in data
        assert "totals" in data
