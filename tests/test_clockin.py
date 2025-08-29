import pytest
import httpx

BASE_URL = "http://localhost:8000"  # cambia si es otro puerto

@pytest.mark.asyncio
async def test_login_and_clock_in():
    # Aumentamos el timeout a 30s
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Login
        try:
            login_response = await client.post(
                "/auth/login",
                json={"email": "test@test.com", "password": "Thomas123!"}
            )
            login_response.raise_for_status()  # lanza excepción si no es 2xx
        except httpx.RequestError as e:
            pytest.fail(f"No se pudo conectar al backend: {e}")
        except httpx.HTTPStatusError as e:
            pytest.fail(f"Error en login: {e.response.text}")

        login_data = login_response.json()
        assert "idToken" in login_data
        token = login_data["idToken"]

        # 2. Clock In
        try:
            clockin_response = await client.post(
                "/time-entries/clock-in",
                headers={"Authorization": f"Bearer {token}"},
                json={"tz": "America/Bogota"}
            )
            clockin_response.raise_for_status()
        except httpx.ReadTimeout:
            pytest.fail("Timeout: el endpoint /time-entries/clock-in tardó demasiado")
        except httpx.RequestError as e:
            pytest.fail(f"No se pudo conectar al backend: {e}")
        except httpx.HTTPStatusError as e:
            pytest.fail(f"Error en clock-in: {e.response.text}")

        # 3. Validaciones
        data = clockin_response.json()
        assert "id" in data
        assert "employee_id" in data
        assert "clock_in" in data
        assert "clock_out" in data
        assert "tz" in data
        assert data["tz"] == "America/Bogota"
        assert data["employee_id"]
