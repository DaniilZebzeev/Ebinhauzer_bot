"""
Подключение к базе данных PostgreSQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from app.config import settings

# Создание синхронного движка для миграций
sync_engine = create_engine(settings.database_url)

# Создание асинхронного движка для основной работы
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(async_database_url, echo=settings.debug)

# Сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
AsyncSessionLocal = sessionmaker(
    bind=async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()


async def get_async_session():
    """Получить асинхронную сессию БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_sync_session():
    """Получить синхронную сессию БД"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
