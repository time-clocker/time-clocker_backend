import pytest
import httpx
import asyncio
import random
import string

BASE_URL = "http://localhost:8000"
NUM_USERS = 50


def random_email(i):
    return f"user{i}_{''.join(random.choices(string.ascii_lowercase, k=4))}@example.com"


def random_doc_number():
    return ''.join(random.choices(string.digits, k=8))


async def register_user(email: str, password: str, doc_number: str):
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        resp = await client.post("/auth/register", json={
            "full_name": "Test User",
            "doc_type": "CC",
            "doc_number": doc_number,
            "email": email,
            "password": password
        })
        return resp.status_code


async def login_user(email: str, password: str, delay: float = 0):
    await asyncio.sleep(delay)  # delay antes de loguear (sin delay falla por a propia config de pytest)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        resp = await client.post("/auth/login", json={"email": email, "password": password})
        return resp.status_code


@pytest.mark.asyncio
async def test_register_and_login_users():
    password = "Abc123!@"
    emails = [random_email(i) for i in range(NUM_USERS)]
    doc_numbers = [random_doc_number() for _ in range(NUM_USERS)]

    
    for i in range(0, NUM_USERS, 10):
        batch = [
            register_user(email, password, doc)
            for email, doc in zip(emails[i:i+10], doc_numbers[i:i+10])
        ]
        batch_results = await asyncio.gather(*batch)
        for j, status in enumerate(batch_results, start=i):
            print(f"Registro {emails[j]} -> Status {status}")
            assert status in (201, 409)  # 201 = creado, 409 = ya existe

    
    login_tasks = [
        login_user(email, password, delay=i * 0.001)
        #sin el delay falla la primera prueba más bien el test no determina si se pasa o no y lo cancela por
        #timeout
        for i, email in enumerate(emails)
    ]
    login_results = await asyncio.gather(*login_tasks)

    for i, status in enumerate(login_results):
        print(f"Login {emails[i]} -> Status {status}")


    assert all(status == 200 for status in login_results)
