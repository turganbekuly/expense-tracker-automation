# app/routers/webhooks.py
from fastapi import APIRouter, Request
from app.services import ocr_service, google_sheet, telegram_bot, activation_code_service
import redis.asyncio as redis
import os

router = APIRouter()

# Temporary in-memory storage for tracking user progress
user_state = {}
HELP_LINK = "https://wa.me/77064302140"
redis_url = os.getenv("REDIS_URL", "redis://localhost")
redis_client = redis.from_url(redis_url)

@router.post("/webhook")
async def receive_telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = str(message.get("chat", {}).get("id"))  # Convert chat_id to string for Redis keys
    text = message.get("text")
    photo = message.get("photo")
    document = message.get("document")

    # Get user stage from Redis or default to "waiting_for_receipt"
    user_stage = await redis_client.hget(chat_id, "stage") or "waiting_for_receipt"
    print(f"User {chat_id} is in stage: {user_stage}")  # Debugging

    # Step 1: Process PDF receipt and validate uniqueness of receipt number
    if user_stage == "waiting_for_receipt":
        if photo or (document and document["mime_type"] == "application/pdf"):
            file_id = document["file_id"]
            file_path = await telegram_bot.download_file(file_id)
            receipt_text = ocr_service.process_receipt(file_path)
            is_valid, validation_message, receipt_number = ocr_service.validate_receipt(receipt_text)

            # Step 2: If the receipt is valid, check if the receipt number is unique
            if is_valid:
                if receipt_number and not await activation_code_service.is_activation_code_available(receipt_number):
                    await telegram_bot.send_message(chat_id, f"Duplicate receipt. Please provide a unique receipt or contact us at {HELP_LINK}.")
                    return {"status": "failed", "message": "Duplicate receipt number"}

                # Save receipt number and advance to the next step
                await redis_client.hset(chat_id, mapping={
                    "stage": "waiting_for_phone_number",
                    "receipt_number": receipt_number
                })
                await telegram_bot.send_message(chat_id, "Please enter your phone number in the format 77023334455")
                return {"status": "success", "message": "Phone number request sent"}
            else:
                await telegram_bot.send_message(chat_id, f"Invalid receipt. Please re-upload or contact support at {HELP_LINK}.")
                return {"status": "failed", "message": validation_message}
        else:
            await telegram_bot.send_message(chat_id, "Please send a PDF receipt.")
            return {"status": "waiting", "message": "Awaiting receipt upload"}

    # Step 3: Collect user phone number
    elif user_stage == "waiting_for_phone_number" and text and text.startswith("77"):
        await redis_client.hset(chat_id, "phone_number", text)
        await redis_client.hset(chat_id, "stage", "waiting_for_device")
        await telegram_bot.send_message(chat_id, "Please enter your phone model, e.g., 'iPhone 16 Pro Max'")
        return

    # Step 4: Collect device model and finalize
    elif user_stage == "waiting_for_device" and text:
        # Store device info and retrieve user state data
        await redis_client.hset(chat_id, "device", text)
        receipt_number = await redis_client.hget(chat_id, "receipt_number")
        phone_number = await redis_client.hget(chat_id, "phone_number")
        device = await redis_client.hget(chat_id, "device")

        # Find an available activation code
        while True:
            print("Fetching an available activation code")
            activation_code_entry = await activation_code_service.get_unused_activation_code()
            
            if not activation_code_entry:
                print("No activation codes available")
                await telegram_bot.send_message(chat_id, "Sorry, all activation codes have been used.")
                return {"status": "failed", "message": "No activation codes available"}

            # Attempt to assign activation code in a transaction
            try:
                print(f"Attempting to assign activation code {activation_code_entry.code}")
                success = await activation_code_service.assign_activation_code(
                    activation_code_entry.code, phone_number, device, receipt_number
                )
                if success:
                    google_sheet.append_activation_code_row(
                        activation_code_entry.code, phone_number, device, receipt_number
                    )
                    print(f"Google Sheet appended with code {activation_code_entry.code}")
                    await telegram_bot.send_message(chat_id, f"Thank you! Your activation code: {activation_code_entry.code}")
                    
                    # Clear user state from Redis after successful save
                    await redis_client.delete(chat_id)
                    return {"status": "success", "message": "Activation code sent"}
            except Exception as e:
                print(f"Error assigning activation code: {e}")

    else:
        # Handle unexpected inputs based on the current stage
        if user_stage == "waiting_for_phone_number":
            await telegram_bot.send_message(chat_id, "Please provide your phone number in the format 77023334455.")
        elif user_stage == "waiting_for_device":
            await telegram_bot.send_message(chat_id, "Please specify your phone model.")
        else:
            await telegram_bot.send_message(chat_id, "Please send a PDF receipt.")
        return {"status": "waiting", "message": "Awaiting correct input"}