# alembic/env.py
from __future__ import annotations

from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

# IMPORTA LA METADATA DE TUS MODELOS
from app.db.base import Base  # Base.metadata contiene todos tus modelos
from app.core.config import settings

# Config de Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Opcional (defensivo): asegura que script_location sea "alembic"
# para evitar rarezas si el INI está mal.
config.set_main_option("script_location", "alembic")

target_metadata = Base.metadata


def _sync_url() -> str:
    """
    Alembic necesita una URL síncrona.
    Si vienes con postgresql+asyncpg, cámbiala por postgresql+psycopg2.
    """
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    return url


def run_migrations_offline() -> None:
    """Ejecuta migraciones sin conexión (genera SQL)."""
    url = _sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # compara tipos de columnas
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecuta migraciones con conexión real."""
    url = _sync_url()

    # IMPORTANTE: como usamos prefix="", la clave correcta es "url"
    connectable = engine_from_config(
        {"url": url},
        prefix="",  # no usamos el prefijo de alembic.ini
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
