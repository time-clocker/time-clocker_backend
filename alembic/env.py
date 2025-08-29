from __future__ import annotations

from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.core.config import settings

from app.models.pay_rate import PayRate 
from app.models.employee import Employee  
from app.models.time_entry import TimeEntry  
from app.models.pay_rule import PayRule 

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("script_location", "alembic")

target_metadata = Base.metadata

def _sync_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg", "postgresql+psycopg2")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url

def run_migrations_offline() -> None:
    url = _sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    url = _sync_url()
    connectable = engine_from_config(
        {"url": url}, 
        prefix="",
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
