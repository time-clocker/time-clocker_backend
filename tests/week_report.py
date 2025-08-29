import pytest
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8000"

@pytest.mark.asyncio
async def test_weekly_report():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1️⃣ Login empleado
        login_response = await client.post("/auth/login", json={
            "email": "test@test.com",
            "password": "Thomas123!"
        })
        login_response.raise_for_status()
        token = login_response.json()["idToken"]

        # 2️⃣ Obtener reporte semanal
        employee_id = "c73c929d-449e-4259-88ed-730428df520b"
        ref_date = datetime.now().isoformat()
        report_response = await client.get(
            f"/reports/employee/{employee_id}/weekly",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "ref_date": ref_date,
                "timezone": "America/Bogota"
            }
        )
        report_response.raise_for_status()
        report_data = report_response.json()

        # 3️⃣ Validaciones básicas del reporte
        assert "employee" in report_data
        assert report_data["employee"]["id"] == employee_id
        assert "bar_by_day" in report_data
        assert isinstance(report_data["bar_by_day"], list)
        assert "pie_hours" in report_data
        assert "totals" in report_data

        # Opcional: validar sumatoria de horas
        total_hours = sum(day["hours_total"] for day in report_data["bar_by_day"])
        assert total_hours >= 0
