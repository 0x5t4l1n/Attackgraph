from backend.storage.models import Base
from backend.storage.database import engine


async def init_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
