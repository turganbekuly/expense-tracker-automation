from fastapi import APIRouter, Request
from app.services import ocr_service, google_sheet, telegram_bot, activation_code_service
import redis.asyncio as redis
import os

router = APIRouter()

HELP_LINK = "https://wa.me/77064302140"
redis_client = redis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)

async def get_user_stage(chat_id):
    """Fetch the user stage from Redis, defaulting to 'waiting_for_receipt' if not set."""
    try:
        # Ensure chat_id is treated as a string for Redis
        chat_id_str = str(chat_id)
        stage = await redis_client.hget(chat_id_str, "stage")
        print(f"method stage: {stage}")
        return stage if stage else "waiting_for_receipt"
    except Exception as e:
        print(f"Error fetching user stage for {chat_id}: {e}")
        return "waiting_for_receipt"

async def set_user_stage(chat_id, stage):
    """Set the user's current stage in Redis."""
    try:
        # Ensure chat_id is treated as a string for Redis
        chat_id_str = str(chat_id)
        await redis_client.hset(chat_id_str, "stage", stage)
    except Exception as e:
        print(f"Error setting user stage for {chat_id}: {e}")

@router.post("/webhook")
async def receive_telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")
    photo = message.get("photo")
    document = message.get("document")

    # Retrieve the current user stage from Redis
    user_stage = await get_user_stage(chat_id)
    print(f"User {chat_id} is in stage: {user_stage}")

    # Step 1: Process PDF receipt and validate uniqueness of receipt number
    if user_stage == "waiting_for_receipt":
        if photo or (document and document["mime_type"] == "application/pdf"):
            try:
                print(f"Got file in stage: {user_stage}")
                file_id = document["file_id"]
                file_path = await telegram_bot.download_file(file_id)
                receipt_text = ocr_service.process_receipt(file_path)
                is_valid, validation_message, receipt_number = ocr_service.validate_receipt(receipt_text)
                print(f"Got validation result {is_valid} {validation_message} {receipt_number} in stage: {user_stage}")
                if is_valid:
                    # Check for duplicate receipt number
                    if receipt_number and not await activation_code_service.is_activation_code_available(receipt_number):
                        await telegram_bot.send_message(chat_id, f"Пожалуйста, отправьте корректный чек или напишите нам {HELP_LINK}.")
                        return {"status": "failed", "message": "Duplicate receipt number"}

                    # Save receipt number and advance to "waiting_for_phone_number" stage
                    await redis_client.hset(chat_id, mapping={
                        "stage": "waiting_for_phone_number",
                        "receipt_number": receipt_number
                    })
                    print(f"Got validation result {is_valid} {validation_message} {receipt_number} in stage: {user_stage}")
                    await telegram_bot.send_message(chat_id, "Пожалуйста, напишите номер телефона, который участвует в розыгрыше в формате 77023334455")
                    return {"status": "success", "message": "Phone number request sent"}
                else:
                    await telegram_bot.send_message(chat_id, f"Пожалуйста, отправьте корректный чек или напишите нам {HELP_LINK}.")
                    return {"status": "failed", "message": validation_message}
            except Exception as e:
                print(f"Error processing receipt for user {chat_id}: {e}")
                await telegram_bot.send_message(chat_id, f"Внутренняя ошибка при обработке чека: {str(e)}")
                return {"status": "failed", "message": "Internal error during receipt processing"}

        await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
        return {"status": "waiting", "message": "Awaiting receipt upload"}

    # Step 2: Collect user phone number
    elif user_stage == "waiting_for_phone_number" and text and text.startswith("77"):
        try:
            await redis_client.hset(chat_id, "phone_number", text)
            await set_user_stage(chat_id, "waiting_for_device")
            await telegram_bot.send_message(chat_id, "Напишите, пожалуйста, модель вашего телефона. Например: 'iPhone 16 Pro Max'")
            return {"status": "success", "message": "Device model request sent"}
        except Exception as e:
            print(f"Error storing phone number for user {chat_id}: {e}")
            return {"status": "failed", "message": "Internal error during phone number storage"}

    # Step 3: Collect device model and finalize
    elif user_stage == "waiting_for_device" and text:
        try:
            # Store device info and retrieve all necessary user data from Redis
            await redis_client.hset(chat_id, "device", text)
            receipt_number = await redis_client.hget(chat_id, "receipt_number")
            phone_number = await redis_client.hget(chat_id, "phone_number")
            device = await redis_client.hget(chat_id, "device")

            # Check if any data is missing and handle it
            if not (receipt_number and phone_number and device):
                await telegram_bot.send_message(chat_id, "Ошибка: неполные данные. Пожалуйста, начните процесс заново.")
                await redis_client.delete(chat_id)  # Clear incomplete state
                return {"status": "failed", "message": "Incomplete user data"}

            # Attempt to assign an activation code
            while True:
                activation_code_entry = await activation_code_service.get_unused_activation_code()
                
                if not activation_code_entry:
                    await telegram_bot.send_message(chat_id, "Извините, все коды активации были использованы.")
                    return {"status": "failed", "message": "No activation codes available"}

                # Try assigning the activation code
                try:
                    success = await activation_code_service.assign_activation_code(
                        activation_code_entry.code, phone_number, device, receipt_number
                    )
                    if success:
                        google_sheet.append_activation_code_row(
                            activation_code_entry.code, phone_number, device, receipt_number
                        )
                        await telegram_bot.send_message(chat_id, f"Спасибо! Ваш код активации: {activation_code_entry.code}")
                        
                        # Clear user state after successful code assignment
                        await redis_client.delete(chat_id)
                        return {"status": "success", "message": "Activation code sent"}
                except Exception as e:
                    print(f"Error assigning activation code for user {chat_id}: {e}")
                    return {"status": "failed", "message": "Activation code assignment failed"}
        except Exception as e:
            print(f"Error finalizing activation for user {chat_id}: {e}")
            return {"status": "failed", "message": "Internal error during device storage"}

    # Handle unexpected inputs based on the current stage
    else:
        if user_stage == "waiting_for_phone_number":
            await telegram_bot.send_message(chat_id, "Пожалуйста, укажите номер телефона в формате 77023334455.")
        elif user_stage == "waiting_for_device":
            await telegram_bot.send_message(chat_id, "Пожалуйста, укажите модель вашего телефона.")
        elif user_stage == "waiting_for_receipt":
            await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
        else:
            await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
        return {"status": "waiting", "message": "Awaiting correct input"}
