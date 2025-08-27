from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from collections.abc import AsyncGenerator
from app.core.config import settings
import re

def _make_async_url() -> str:
    url = settings.DATABASE_URL

    url = re.sub(r"^postgres://", "postgresql://", url)

    url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    if "postgresql+asyncpg://" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")

    return url

ASYNC_DB_URL = _make_async_url()

engine = create_async_engine(
    ASYNC_DB_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
