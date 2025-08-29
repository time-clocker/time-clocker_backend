import pytest
import httpx
import asyncio
import random
import string
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

def random_email():
    return ''.join(random.choices(string.ascii_lowercase, k=6)) + "@example.com"

def random_doc_number():
    return ''.join(random.choices(string.digits, k=6))


@pytest.mark.asyncio
async def test_password_rules_dynamic():
    """
    Valida reglas de contraseñas:
    - mínimo 6 caracteres
    - al menos una mayúscula
    - al menos una minúscula
    - al menos un número
    - al menos un símbolo especial
    Imprime resultados.
    """
    users = [
        {"password": "Ab1!", "fail": "muy corta (<6)"},
        {"password": "abcdef1!", "fail": "sin mayúscula"},
        {"password": "ABCDEFG1!", "fail": "sin minúscula"},
        {"password": "Abcdef!@", "fail": "sin número"},
        {"password": "Abcdef12", "fail": "sin símbolo"},
        {"password": "Abc123!@", "fail": None}  # válido
    ]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        print("\nResumen de contraseñas:")
        for user in users:
            email = random_email()
            doc_number = random_doc_number()
            resp = await client.post("/auth/register", json={
                "full_name": "Test User",
                "doc_type": "CC",
                "doc_number": doc_number,
                "email": email,
                "password": user["password"]
            })
            if user["fail"]:
                if resp.status_code == 422:
                    print(f"{user['password']} -> FALLA correcta: {user['fail']}")
                else:
                    print(f"{user['password']} -> OTRO ERROR: {resp.status_code}")
            else:
                if resp.status_code == 201:
                    print(f"{user['password']} -> OK")
                else:
                    print(f"{user['password']} -> ERROR: {resp.status_code}")


@pytest.mark.asyncio
async def test_admin_only_access():
    """
    Verifica que solo admins puedan acceder al reporte global.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        admin_login = await client.post("/auth/login", json={
            "email": "pandoraadmin@example.com",
            "password": "pandora"
        })
        admin_login.raise_for_status()
        admin_token = admin_login.json()["idToken"]

        emp_login = await client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "Thomas123!"
        })
        emp_login.raise_for_status()
        emp_token = emp_login.json()["idToken"]

        start = (datetime.now() - timedelta(days=7)).isoformat()
        end = datetime.now().isoformat()

        emp_access = await client.get(
            "/reports/global",
            headers={"Authorization": f"Bearer {emp_token}"},
            params={"start": start, "end": end, "timezone": "America/Bogota"}
        )
        assert emp_access.status_code == 403

        admin_access = await client.get(
            "/reports/global",
            headers={"Authorization": f"Bearer {admin_token}"},
            params={"start": start, "end": end, "timezone": "America/Bogota"}
        )
        assert admin_access.status_code == 200
        data = admin_access.json()
        assert isinstance(data, dict)
        assert "range" in data
        assert "rows" in data
        assert "totals" in data


@pytest.mark.asyncio
async def test_login_and_clock_in():
    """
    Login de usuario y registrar clock-in.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        login_response = await client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "Thomas123!"
        })
        login_response.raise_for_status()
        token = login_response.json()["idToken"]

        clockin_response = await client.post("/time-entries/clock-in",
            headers={"Authorization": f"Bearer {token}"},
            json={"tz": "America/Bogota"}
        )
        clockin_response.raise_for_status()
        data = clockin_response.json()
        assert "id" in data
        assert "employee_id" in data
        assert "clock_in" in data
        assert "clock_out" in data
        assert data["tz"] == "America/Bogota"


@pytest.mark.asyncio
async def test_clock_out():
    """
    Login y registrar clock-out.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        login_response = await client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "Thomas123!"
        })
        login_response.raise_for_status()
        token = login_response.json()["idToken"]

        clockout_response = await client.post("/time-entries/clock-out",
            headers={"Authorization": f"Bearer {token}"},
            json={}
        )
        assert clockout_response.status_code == 200
        data = clockout_response.json()
        assert "id" in data
        assert "employee_id" in data
        assert "clock_in" in data
        assert "clock_out" in data
        assert "tz" in data


@pytest.mark.asyncio
async def test_weekly_report():
    """
    Reporte semanal de un empleado.
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        login_response = await client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "Thomas123!"
        })
        login_response.raise_for_status()
        token = login_response.json()["idToken"]

        employee_id = "c73c929d-449e-4259-88ed-730428df520b"
        ref_date = datetime.now().isoformat()
        report_response = await client.get(
            f"/reports/employee/{employee_id}/weekly",
            headers={"Authorization": f"Bearer {token}"},
            params={"ref_date": ref_date, "timezone": "America/Bogota"}
        )
        report_response.raise_for_status()
        report_data = report_response.json()
        assert "employee" in report_data
        assert report_data["employee"]["id"] == employee_id
        assert "bar_by_day" in report_data
        assert isinstance(report_data["bar_by_day"], list)
        assert "pie_hours" in report_data
        assert "totals" in report_data
