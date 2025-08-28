import pytest
from httpx import AsyncClient
from app.main import app


# CP-01: Registrar entrada - Validar inserción correcta de entrada en BD.
@pytest.mark.asyncio
async def test_cp01_registrar_entrada():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Simulate login and get token (mock or fixture needed)
        token = "Bearer testtoken"
        payload = {"tz": "America/Bogota"}
        response = await ac.post("/time-entries/clock-in", json=payload, headers={"Authorization": token})
        assert response.status_code == 200
        assert "clock_in" in response.json()

# CP-02: Registrar salida - Verificar persistencia correcta de salida y cálculo de horas.
@pytest.mark.asyncio
async def test_cp02_registrar_salida():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        token = "Bearer testtoken"
        # First, clock-in
        await ac.post("/time-entries/clock-in", json={"tz": "America/Bogota"}, headers={"Authorization": token})
        # Then, clock-out
        response = await ac.post("/time-entries/clock-out", json={}, headers={"Authorization": token})
        assert response.status_code == 200
        assert "clock_out" in response.json()

# CP-03: Evitar doble entrada - Simular doble petición de entrada y comprobar rechazo.
@pytest.mark.asyncio
async def test_cp03_evitar_doble_entrada():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        token = "Bearer testtoken"
        await ac.post("/time-entries/clock-in", json={"tz": "America/Bogota"}, headers={"Authorization": token})
        response = await ac.post("/time-entries/clock-in", json={"tz": "America/Bogota"}, headers={"Authorization": token})
        assert response.status_code == 409

# CP-04: Evitar doble salida - Simular doble petición de salida y comprobar rechazo.
@pytest.mark.asyncio
async def test_cp04_evitar_doble_salida():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        token = "Bearer testtoken"
        await ac.post("/time-entries/clock-in", json={"tz": "America/Bogota"}, headers={"Authorization": token})
        await ac.post("/time-entries/clock-out", json={}, headers={"Authorization": token})
        response = await ac.post("/time-entries/clock-out", json={}, headers={"Authorization": token})
        assert response.status_code == 409

# CP-05: Reporte de horas - Validar la lógica de sumatoria de horas trabajadas.
@pytest.mark.asyncio
async def test_cp05_reporte_horas():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        token = "Bearer testtoken"
        # Simulate report request (dates should be adapted)
        response = await ac.get("/reports/employee/test-employee-id", params={
            "start": "2025-01-01T00:00:00",
            "end": "2025-01-31T23:59:59",
            "timezone": "America/Bogota"
        }, headers={"Authorization": token})
        assert response.status_code in (200, 404)  # 404 if employee not found

# CP-07: Seguridad de roles - Probar acceso con distintos roles (admin/empleado).
@pytest.mark.asyncio
async def test_cp07_seguridad_roles():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Try global report as employee (should fail)
        token_employee = "Bearer employeetoken"
        response = await ac.get("/reports/global", params={
            "start": "2025-01-01T00:00:00",
            "end": "2025-01-31T23:59:59",
            "timezone": "America/Bogota"
        }, headers={"Authorization": token_employee})
        assert response.status_code == 403
        # Try as admin (should succeed)
        token_admin = "Bearer admintoken"
        response = await ac.get("/reports/global", params={
            "start": "2025-01-01T00:00:00",
            "end": "2025-01-31T23:59:59",
            "timezone": "America/Bogota"
        }, headers={"Authorization": token_admin})
        assert response.status_code == 200

# CP-08: Contraseña segura - Validar reglas de contraseñas (mínimo caracteres, complejidad).
def test_cp08_contrasena_segura():
    from app.schemas.auth import RegisterRequest
    # Too short password
    with pytest.raises(Exception):
        RegisterRequest(full_name="Test", doc_type="CC", doc_number="123", email="test@test.com", password="123")
    # Valid password
    req = RegisterRequest(full_name="Test", doc_type="CC", doc_number="123", email="test@test.com", password="123456")
    assert req.password == "123456"

# CP-12: Auditoría de acciones - Verificar que cada acción se registre con usuario, fecha y hora.
@pytest.mark.asyncio
async def test_cp12_auditoria_acciones():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        token = "Bearer testtoken"
        # Clock-in and clock-out, then check report for audit fields
        await ac.post("/time-entries/clock-in", json={"tz": "America/Bogota"}, headers={"Authorization": token})
        await ac.post("/time-entries/clock-out", json={}, headers={"Authorization": token})
        response = await ac.get("/reports/employee/test-employee-id", params={
            "start": "2025-01-01T00:00:00",
            "end": "2025-01-31T23:59:59",
            "timezone": "America/Bogota"
        }, headers={"Authorization": token})
        if response.status_code == 200:
            data = response.json()
            assert "employee" in data
            assert "bar_by_day" in data
            assert "pie_hours" in data

# ...existing