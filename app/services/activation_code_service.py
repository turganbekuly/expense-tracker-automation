# app/services/activation_code_service.py

from app.models.activation_code import ActivationCode
from app.services.database import SessionLocal
from sqlalchemy.future import select

# Add a new activation code to the database
async def add_activation_code(code: str):
    async with SessionLocal() as session:
        async with session.begin():
            new_activation_code = ActivationCode(code=code)
            session.add(new_activation_code)
        await session.commit()

# Retrieve an activation code by its code value
async def get_activation_code(code: str):
    async with SessionLocal() as session:
        result = await session.execute(select(ActivationCode).filter(ActivationCode.code == code))
        return result.scalars().first()

# Update activation code with user details
async def update_activation_code(code: str, phone_number: str, device: str):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(ActivationCode).filter(ActivationCode.code == code))
            activation_code = result.scalars().first()
            if activation_code:
                activation_code.phone_number = phone_number
                activation_code.device = device
            await session.commit()

# Check if a receipt number is unique (available) in the database
async def is_activation_code_available(receipt_number: str):
    async with SessionLocal() as session:
        # Query the database to check if the receipt_number exists
        result = await session.execute(
            select(ActivationCode).filter(ActivationCode.receipt_number == receipt_number)
        )
        # If any record is found, the receipt_number is not available (return False)
        is_available = result.scalar() is None
        print(f"Receipt number {receipt_number} available: {is_available}")  # Debugging output
        return is_available  # True if unique, False if duplicate


# Retrieve an unused activation code from the database
# app/services/activation_code_service.py

async def get_unused_activation_code():
    async with SessionLocal() as session:
        # Fetch an activation code where phone_number, device, and receipt_number are NULL
        result = await session.execute(
            select(ActivationCode).filter(
                ActivationCode.phone_number == None,
                ActivationCode.device == None,
                ActivationCode.receipt_number == None
            )
        )
        activation_code = result.scalars().first()
        print(f"Fetched unused activation code: {activation_code.code if activation_code else 'None available'}")
        return activation_code


# Assign an activation code to a user with phone, device, and receipt number
async def assign_activation_code(code: str, phone_number: str, device: str, receipt_number: str):
    async with SessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(ActivationCode).filter(ActivationCode.code == code, ActivationCode.phone_number == None)
            )
            activation_code = result.scalars().first()
            
            if activation_code:
                activation_code.phone_number = phone_number
                activation_code.device = device
                activation_code.receipt_number = receipt_number  # Save the receipt number
                await session.commit()
                return True
            return False  # If the code was already taken
