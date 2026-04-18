from app.db.base import *  # noqa: F401,F403
from app.db.session import engine
from app.models.base import Base


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
