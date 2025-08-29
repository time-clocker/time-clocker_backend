import pytest, asyncio, random, string
from datetime import datetime, timedelta
import httpx

BASE_URL = "http://localhost:8000"

def random_email():
    return ''.join(random.choices(string.ascii_lowercase, k=6)) + "@example.com"

def random_doc_number():
    return ''.join(random.choices(string.digits, k=6))

@pytest.mark.asyncio
async def test_password_rules_dynamic():
    """
    Test dinámico de contraseñas para validar reglas:
    - mínimo 6 caracteres
    - al menos una mayúscula
    - al menos una minúscula
    - al menos un número
    - al menos un símbolo especial
    Imprime resultados de cada contraseña.
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
        print("Resumen de contraseñas:")
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
