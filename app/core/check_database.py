# app/core/check_database.py

import asyncio
from app.services.database import SessionLocal
from app.models.activation_code import ActivationCode
from sqlalchemy.future import select

async def check_activation_codes():
    async with SessionLocal() as session:
        # Query all entries in the activation_codes table
        result = await session.execute(select(ActivationCode))
        activation_codes = result.scalars().all()

        # Print each activation code entry
        for code in activation_codes:
            print(f"ID: {code.id}, Code: {code.code}, Phone: {code.phone_number}, Device: {code.device}, Receipt Number: {code.receipt_number}")

if __name__ == "__main__":
    asyncio.run(check_activation_codes())
