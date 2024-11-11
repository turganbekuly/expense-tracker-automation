# app/core/create_db.py

import asyncio
from app.services.database import engine
from app.models.activation_code import Base  # Import the Base from activation_code

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())
