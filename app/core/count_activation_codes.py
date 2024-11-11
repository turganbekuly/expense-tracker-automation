# app/core/count_activation_codes.py

import asyncio
from sqlalchemy import func
from app.services.database import SessionLocal
from app.models.activation_code import ActivationCode
from sqlalchemy.future import select

async def count_activation_codes():
    async with SessionLocal() as session:
        # Use func.count() to count rows in the activation_codes table
        result = await session.execute(select(func.count()).select_from(ActivationCode))
        total_count = result.scalar()
        print(f"Total activation codes in database: {total_count}")

if __name__ == "__main__":
    asyncio.run(count_activation_codes())
