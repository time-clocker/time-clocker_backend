# WorkTime – Backend (FastAPI + PostgreSQL + Firebase)

Backend del sistema de control de tiempos y reportes.
**Stack:** FastAPI · SQLAlchemy (async) · PostgreSQL · Alembic · Firebase Authentication.

---

## 🚀 Requisitos

* **Python 3.11+**
* **PostgreSQL 14+** (pgAdmin opcional)
* **Cuenta Firebase** con:

  * Authentication habilitado (Email/Password)
  * Web API Key (para login/register desde REST)
  * Service Account JSON (para verificación de tokens en backend)

---

## 📂 Estructura

```
time-clocker_backend/
├─ app/
│  ├─ core/              # config, seguridad, cors
│  ├─ db/                # base, session, init_firebase
│  ├─ models/            # Employee, TimeEntry, PayRule
│  ├─ routers/           # auth, employees, time_entries, reports
│  ├─ schemas/           # Pydantic schemas
│  └─ main.py
├─ alembic/              # Migraciones
├─ scripts/
│  └─ set_admin.py       # Script para asignar rol admin
├─ secrets/
│  └─ firebase-sa.json   # Service account Firebase
├─ .env.example
├─ requirements.txt
└─ README.md
```

---

## ⚙️ 1. Preparar entorno

```bash
# Clonar repo y entrar a la carpeta del backend
git clone <repo>
cd time-clocker_backend

# Crear y activar entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1  # (Windows PowerShell)
# source .venv/bin/activate # (Linux/Mac)

# Instalar dependencias
pip install -r requirements.txt
```

---

## 🗄️ 2. Configurar PostgreSQL

```sql
-- Como superusuario
CREATE USER worktime_user WITH PASSWORD '1234';
CREATE DATABASE worktime OWNER worktime_user;
GRANT ALL PRIVILEGES ON DATABASE worktime TO worktime_user;

-- Dentro de la BD
GRANT USAGE ON SCHEMA public TO worktime_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO worktime_user;
```

---

## 🔥 3. Configurar Firebase

1. En **Project settings → Service accounts → Generate new private key**
   Guarda el JSON en `secrets/firebase-sa.json`.

2. Copia tu **Web API Key** de la pestaña General.

---

## 📑 4. Variables de entorno

`.env` ejemplo:

```env
APP_NAME=WorkTime API
APP_ENV=local
APP_DEBUG=true

# CORS
CORS_ALLOW_ORIGINS=https://tu-frontend.netlify.app,http://localhost:5173

# Base de datos
DATABASE_URL=postgresql+asyncpg://worktime_user:1234@localhost:5432/worktime

# Firebase
FIREBASE_PROJECT_ID=worktime-f91dc
FIREBASE_CREDENTIALS_PATH=secrets/firebase-sa.json
FIREBASE_WEB_API_KEY=TU_API_KEY_WEB

# Reportes
DEFAULT_TIMEZONE=America/Bogota
DEFAULT_HOURLY_RATE=15000
```

---

## 🔄 5. Migraciones (Alembic)

```bash
alembic upgrade head
```

Si fallara por esquema vacío:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## 🖥️ 6. Levantar el servidor

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

* Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* OpenAPI JSON: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 👤 7. Crear usuario Admin (para endpoints protegidos)

### Paso 1. Crear usuario en Firebase

En consola → Authentication → Users → *Add user*
Ejemplo:

* email: `pandoraadmin@example.com`
* password: `pandora`

Copia el **UID** generado.

---

### Paso 2. Asignar rol `admin` vía script

Archivo: `scripts/set_admin.py`

```python
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # añade la raíz al PYTHONPATH

import firebase_admin
from firebase_admin import credentials, auth
from app.core.config import settings

if not firebase_admin._apps:
    if settings.firebase_credentials_dict:
        cred = credentials.Certificate(settings.firebase_credentials_dict)
    else:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)

uid = "UID_COPIADO_DE_FIREBASE"
auth.set_custom_user_claims(uid, {"role": "admin"})
print(f"✅ Rol admin asignado a UID={uid}")
```

Ejecutar:

```bash
python scripts/set_admin.py
```

> 🔄 El usuario debe **volver a iniciar sesión** para que el `idToken` ya traiga el claim `role=admin`.

---

### Paso 3. Registrar el admin en BD

Inserta en `employees`:

```sql
INSERT INTO employees (id, firebase_uid, full_name, email, doc_type, doc_number, hourly_rate, active, created_at)
VALUES (
  gen_random_uuid(),
  'UID_COPIADO_DE_FIREBASE',
  'Pandora Admin',
  'pandoraadmin@example.com',
  'CC',
  '9999999999',
  0,
  TRUE,
  now()
);
```

---

## 🧪 8. Probar endpoints

### Login

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"pandoraadmin@example.com","password":"pandora","returnSecureToken":true}'
```

Copia el `idToken` → úsalo como `Bearer <TOKEN>` en Swagger.

### Endpoints admin disponibles

* `GET /employees` – listar empleados
* `POST /employees` – crear
* `PATCH /employees/{id}` – actualizar
* `DELETE /employees/{id}` – eliminar
* `GET /reports/global` – reportes globales


