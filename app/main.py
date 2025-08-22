from fastapi import FastAPI
from app.core.config import settings
from app.core.cors import add_cors
from app.db.init_firebase import init_firebase
from app.routers import health, employees, time_entries, reports, auth

def get_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, debug=settings.APP_DEBUG)
    add_cors(app)
    init_firebase()

    app.include_router(health.router)
    app.include_router(employees.router)
    app.include_router(auth.router)
    app.include_router(time_entries.router)
    app.include_router(reports.router)

    return app

app = get_app()
