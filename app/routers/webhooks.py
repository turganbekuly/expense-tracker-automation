import logging
from fastapi import APIRouter, Request
from app.services import ocr_service, google_sheet, telegram_bot, activation_code_service
import redis.asyncio as redis
import os

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HELP_LINK = "https://wa.me/77064302140"
redis_url = os.getenv("REDIS_URL", "redis://localhost")
redis_client = redis.from_url(redis_url)

async def get_user_stage(chat_id: str):
    try:
        stage = await redis_client.hget(chat_id, "stage") or "waiting_for_receipt"
        logger.info(f"User {chat_id} stage retrieved from Redis: {stage}")
        return stage
    except Exception as e:
        logger.error(f"Error retrieving stage for user {chat_id}: {e}")
        return "waiting_for_receipt"

@router.post("/webhook")
async def receive_telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = str(message.get("chat", {}).get("id"))  # Convert chat_id to string for Redis keys
    text = message.get("text")
    photo = message.get("photo")
    document = message.get("document")

    # Retrieve user stage from Redis
    user_stage = await get_user_stage(chat_id)
    logger.info(f"User {chat_id} is in stage: {user_stage}")

    if user_stage == "waiting_for_receipt":
        if photo or (document and document["mime_type"] == "application/pdf"):
            try:
                file_id = document["file_id"]
                file_path = await telegram_bot.download_file(file_id)
                receipt_text = ocr_service.process_receipt(file_path)
                is_valid, validation_message, receipt_number = ocr_service.validate_receipt(receipt_text)

                if is_valid:
                    if receipt_number and not await activation_code_service.is_activation_code_available(receipt_number):
                        await telegram_bot.send_message(chat_id, f"Пожалуйста, отправьте корректный чек или напишите нам {HELP_LINK}.")
                        return {"status": "failed", "message": "Duplicate receipt number"}

                    # Set stage to "waiting_for_phone_number" and save the receipt number
                    await redis_client.hset(chat_id, mapping={
                        "stage": "waiting_for_phone_number",
                        "receipt_number": receipt_number
                    })
                    logger.info(f"User {chat_id} moved to stage: waiting_for_phone_number with receipt number: {receipt_number}")
                    await telegram_bot.send_message(chat_id, "Пожалуйста, напишите номер телефона, который участвует в розыгрыше в формате 77023334455")
                    return {"status": "success", "message": "Phone number request sent"}
                else:
                    await telegram_bot.send_message(chat_id, f"Пожалуйста, отправьте корректный чек или напишите нам {HELP_LINK}.")
                    return {"status": "failed", "message": validation_message}
            except Exception as e:
                logger.error(f"Error processing receipt for user {chat_id}: {e}")
                return {"status": "failed", "message": "Internal error during receipt processing"}

        await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
        return {"status": "waiting", "message": "Awaiting receipt upload"}

    elif user_stage == "waiting_for_phone_number" and text and text.startswith("77"):
        try:
            await redis_client.hset(chat_id, "phone_number", text)
            await redis_client.hset(chat_id, "stage", "waiting_for_device")
            logger.info(f"User {chat_id} moved to stage: waiting_for_device with phone number: {text}")
            await telegram_bot.send_message(chat_id, "Напишите, пожалуйста, модель вашего телефона. Например: 'iPhone 16 Pro Max'")
            return {"status": "success", "message": "Device model request sent"}
        except Exception as e:
            logger.error(f"Error storing phone number for user {chat_id}: {e}")
            return {"status": "failed", "message": "Internal error during phone number storage"}

    elif user_stage == "waiting_for_device" and text:
        try:
            await redis_client.hset(chat_id, "device", text)
            receipt_number = await redis_client.hget(chat_id, "receipt_number")
            phone_number = await redis_client.hget(chat_id, "phone_number")
            device = await redis_client.hget(chat_id, "device")

            while True:
                logger.info("Fetching an available activation code")
                activation_code_entry = await activation_code_service.get_unused_activation_code()
                
                if not activation_code_entry:
                    logger.info("No activation codes available")
                    await telegram_bot.send_message(chat_id, "Извините, все коды активации были использованы.")
                    return {"status": "failed", "message": "No activation codes available"}

                try:
                    success = await activation_code_service.assign_activation_code(
                        activation_code_entry.code, phone_number, device, receipt_number
                    )
                    if success:
                        google_sheet.append_activation_code_row(
                            activation_code_entry.code, phone_number, device, receipt_number
                        )
                        await telegram_bot.send_message(chat_id, f"Спасибо! Ваш код активации: {activation_code_entry.code}")
                        await redis_client.delete(chat_id)
                        logger.info(f"User {chat_id} activation complete and Redis state cleared")
                        return {"status": "success", "message": "Activation code sent"}
                except Exception as e:
                    logger.error(f"Error assigning activation code for user {chat_id}: {e}")

        except Exception as e:
            logger.error(f"Error finalizing activation for user {chat_id}: {e}")
            return {"status": "failed", "message": "Internal error during device storage"}

    else:
        # Handle unexpected inputs based on the current stage
        if user_stage == "waiting_for_phone_number":
            await telegram_bot.send_message(chat_id, "Пожалуйста, укажите номер телефона в формате 77023334455.")
        elif user_stage == "waiting_for_device":
            await telegram_bot.send_message(chat_id, "Пожалуйста, укажите модель вашего телефона.")
        else:
            await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
        return {"status": "waiting", "message": "Awaiting correct input"}
