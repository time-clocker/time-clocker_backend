import pytest
import httpx

BASE_URL = "http://localhost:8000"  # cambia si es otro puerto

@pytest.mark.asyncio
async def test_login_success():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        response = await client.post(
            "/auth/login",
            json={
                "email": "test@test.com",
                "password": "Thomas123!"
            }
        )

    # ✅ debe loguear correctamente
    assert response.status_code == 200, response.text
    data = response.json()

    # tu API devuelve "idToken", no "access_token"
    assert "idToken" in data
    assert "expiresIn" in data
    assert data["email"] == "test@test.com"
