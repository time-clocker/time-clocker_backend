import pytest
import httpx

BASE_URL = "http://localhost:8000"  # Cambia si tu backend corre en otro puerto

@pytest.mark.asyncio
async def test_clock_out():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1️⃣ Login
        login_response = await client.post(
            "/auth/login",
            json={"email": "test@test.com", "password": "Thomas123!"}
        )
        login_response.raise_for_status()  # lanza excepción si no es 2xx
        login_data = login_response.json()
        token = login_data["idToken"]

        # 2️⃣ Clock Out
        clockout_response = await client.post(
            "/time-entries/clock-out",
            headers={"Authorization": f"Bearer {token}"},
            json={}  # body vacío
        )

        # 3️⃣ Validaciones
        assert clockout_response.status_code == 200, clockout_response.text
        data = clockout_response.json()

        # Campos que devuelve la API
        assert "id" in data
        assert "employee_id" in data
        assert "clock_in" in data
        assert "clock_out" in data
        assert "tz" in data

        # Chequeo básico
        assert data["employee_id"]  # UUID del empleado
        assert data["clock_out"]  # debe estar rellenado
