"""数据库引擎和 session 工厂。"""

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from planguide.config import settings

engine = create_async_engine(settings.database_url, echo=False)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def create_tables():
    from planguide.infrastructure.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
