WorkTime – Backend (FastAPI + PostgreSQL + Firebase)

Backend del sistema de control de tiempos y reportes.
Stack: FastAPI · SQLAlchemy (async) · PostgreSQL · Alembic · Firebase Authentication.

Requisitos

Python 3.11+

PostgreSQL 14+ (pgAdmin opcional)

Cuenta de Firebase con:

Firebase Authentication habilitado (Email/Password)

Web API Key (para login/register desde REST)

Service Account JSON (para verificación de tokens en el backend)

Estructura actual
worktime-backend/
├─ app/
│  ├─ core/
│  │  ├─ config.py          # Settings (.env) + helpers
│  │  ├─ security.py        # Dep. auth (Firebase), admin_required, current_employee
│  │  └─ cors.py            # CORS (Netlify/local)
│  ├─ db/
│  │  ├─ base.py            # Declarative Base
│  │  ├─ session.py         # Engine/AsyncSession
│  │  └─ init_firebase.py   # Inicialización Firebase Admin
│  ├─ models/
│  │  ├─ employee.py
│  │  ├─ time_entry.py
│  │  └─ pay_rule.py        # (base para reglas de pago)
│  ├─ routers/
│  │  ├─ health.py
│  │  ├─ auth.py            # /auth/register, /auth/login, /auth/me
│  │  ├─ employees.py       # CRUD admin + /employees/me/profile
│  │  ├─ time_entries.py    # clock-in / clock-out / list
│  │  └─ reports.py         # reports (WIP)
│  ├─ schemas/
│  │  ├─ auth.py
│  │  ├─ employee.py
│  │  ├─ time_entry.py
│  │  └─ reports.py
│  └─ main.py
├─ alembic/                 # Migraciones
├─ tests/                   # (WIP)
├─ .env.example
├─ requirements.txt
└─ README.md

1) Preparar entorno
# Clonar repo y entrar a la carpeta del backend
git clone
cd time-clocker_backend

# Crear y activar el entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1  # (Windows PowerShell)
# source .venv/bin/activate # (Linux/Mac)

# Instalar dependencias
pip install -r requirements.txt
# Si fuera necesario:
pip install "sqlalchemy[asyncio]" psycopg2-binary==2.9.9

2) Configurar PostgreSQL

Crea una BD y un usuario

-- Como superusuario (p.ej. postgres)
CREATE USER worktime_user WITH PASSWORD '1234';
CREATE DATABASE worktime OWNER worktime_user;
GRANT ALL PRIVILEGES ON DATABASE worktime TO worktime_user;

-- Dentro de la BD worktime
GRANT USAGE ON SCHEMA public TO worktime_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO worktime_user;

3) Configurar Firebase

En Project settings → Service accounts → Generate new private key
Guarda el JSON en secrets/firebase-sa.json.

Copia tu Web API Key de la pestaña General.

4) Variables de entorno

Crea un archivo .env:

APP_NAME=WorkTime API
APP_ENV=local
APP_DEBUG=true

# CORS: origenes del front
CORS_ALLOW_ORIGINS=https://tu-frontend.netlify.app,http://localhost:5173

# Base de datos
DATABASE_URL=postgresql+asyncpg://worktime_user:1234@localhost:5432/worktime

# Firebase
FIREBASE_PROJECT_ID=worktime-f91dc
FIREBASE_CREDENTIALS_PATH=secrets/firebase-sa.json
FIREBASE_WEB_API_KEY=TU_API_KEY_WEB

# Configs de reportes
DEFAULT_TIMEZONE=America/Bogota
DEFAULT_HOURLY_RATE=15000


Importante:

FIREBASE_WEB_API_KEY es obligatorio para /auth/login y /auth/register.

El backend verifica el idToken con Firebase Admin usando FIREBASE_CREDENTIALS_PATH.

5) Migraciones (Alembic)

Si aún no existen tablas, corre:

alembic upgrade head


Si fallara (env vacío), puedes regenerar base inicial:

alembic revision --autogenerate -m "init"
alembic upgrade head

6) Levantar el servidor
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000


Swagger: http://127.0.0.1:8000/docs

OpenAPI JSON: http://127.0.0.1:8000/openapi.json

7) Endpoints y pruebas rápidas
Salud
curl http://127.0.0.1:8000/health
# -> {"status":"ok"}

Registro (público) – /auth/register

Crea usuario en Firebase y su ficha en PostgreSQL.

curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Empleado Demo",
    "email": "empleado@test.com",
    "password": "Test1234!",
    "hourly_rate": 16000
  }'


Respuesta incluye idToken, refreshToken, localId (uid de Firebase) y employee (registro en PG).

Login – /auth/login
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "empleado@test.com",
    "password": "Test1234!",
    "returnSecureToken": true
  }'


Copia el idToken para las rutas protegidas (Authorize en Swagger).

Me – /auth/me
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <ID_TOKEN>"

Registro de jornada

Clock In:

curl -X POST http://127.0.0.1:8000/time-entries/clock-in \
  -H "Authorization: Bearer <ID_TOKEN>"


Clock Out:

curl -X POST http://127.0.0.1:8000/time-entries/clock-out \
  -H "Authorization: Bearer <ID_TOKEN>"


Listar mis marcaciones:

curl http://127.0.0.1:8000/time-entries \
  -H "Authorization: Bearer <ID_TOKEN>"

Empleado (perfil propio)
curl http://127.0.0.1:8000/employees/me/profile \
  -H "Authorization: Bearer <ID_TOKEN>"

Endpoints de Admin (requieren claim role=admin)

GET /employees (listar)

GET /employees/{id} (detalle)

POST /employees (crear manualmente un empleado)

PATCH /employees/{id} (actualizar)

DELETE /employees/{id} (eliminar)

Marcar un usuario como admin (custom claim)

Puedes ejecutar un pequeño script con Firebase Admin (usando tu mismo secrets/firebase-sa.json):

# tools/make_admin.py
import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("secrets/firebase-sa.json")
firebase_admin.initialize_app(cred)

uid = "<UID_DEL_USUARIO>"
auth.set_custom_user_claims(uid, {"role": "admin"})
print("Admin claim set")

# Ejecuta:
# python tools/make_admin.py


Después, el usuario debe volver a loguearse (para que el idToken incluya el claim role=admin).