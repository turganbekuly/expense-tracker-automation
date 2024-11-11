# app/core/sync_activation_codes.py

import asyncio
from app.services import google_sheet
from app.services.database import SessionLocal
from app.models.activation_code import ActivationCode
from sqlalchemy.future import select

async def sync_activation_codes():
    sheet_codes = google_sheet.get_all_activation_codes()  # Fetch all codes from Google Sheets

    async with SessionLocal() as session:
        async with session.begin():
            for code_entry in sheet_codes:
                # Ensure the code is treated as a string
                code = str(code_entry["code"])  # Convert to string to match database column type
                
                # Check if the activation code already exists in the database
                result = await session.execute(select(ActivationCode).filter(ActivationCode.code == code))
                db_code = result.scalars().first()

                if not db_code:
                    # If the code doesn't exist, add it to the database
                    new_code = ActivationCode(code=code)
                    session.add(new_code)
            await session.commit()

if __name__ == "__main__":
    asyncio.run(sync_activation_codes())
