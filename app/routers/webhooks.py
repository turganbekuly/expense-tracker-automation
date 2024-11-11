# app/routers/webhooks.py
from fastapi import APIRouter, Request
from app.services import ocr_service, google_sheet, telegram_bot, activation_code_service

router = APIRouter()

# Temporary in-memory storage for tracking user progress
user_state = {}
HELP_LINK = "https://wa.me/77064302140"

@router.post("/webhook")
async def receive_telegram_webhook(request: Request):
    data = await request.json()
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text")
    photo = message.get("photo")
    document = message.get("document")

    user_stage = user_state.get(chat_id, {}).get("stage", "waiting_for_receipt")

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
                    await telegram_bot.send_message(chat_id, f"Пожалуйста, отправьте корректный чек или напишите нам {HELP_LINK}.")
                    return {"status": "failed", "message": "Duplicate receipt number"}

                # Save receipt number and advance to the next step
                user_state[chat_id] = {
                    "stage": "waiting_for_phone_number",
                    "receipt_number": receipt_number  # Save receipt number in user state
                }
                await telegram_bot.send_message(chat_id, "Пожалуйста, напишите номер телефона, который участвует в розыгрыше в формате 77023334455")
                return {"status": "success", "message": "Phone number request sent"}
            else:
                await telegram_bot.send_message(chat_id, f"Пожалуйста, отправьте корректный чек или напишите нам {HELP_LINK}.")
                return {"status": "failed", "message": validation_message}
        else:
            await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
            return {"status": "waiting", "message": "Awaiting receipt upload"}

    # Step 3: Collect user information (phone number and device model)
    elif user_stage == "waiting_for_phone_number" and text and text.startswith("77"):
        user_state[chat_id]["phone_number"] = text
        user_state[chat_id]["stage"] = "waiting_for_device"
        await telegram_bot.send_message(chat_id, "Напишите, пожалуйста, модель вашего телефона. Например: 'iPhone 16 Pro Max'")
        return

    elif user_stage == "waiting_for_device" and text:
        # Store device info
        user_state[chat_id]["device"] = text
        receipt_number = user_state[chat_id].get("receipt_number")
        phone_number = user_state[chat_id].get("phone_number")
        device = user_state[chat_id].get("device")

        # Step 4: Find an available row and confirm its availability
        while True:
            print("Fetching an available activation code")  # Debugging
            activation_code_entry = await activation_code_service.get_unused_activation_code()
            
            if not activation_code_entry:
                print("No activation codes available")  # Debugging
                await telegram_bot.send_message(chat_id, "Извините, все коды активации были использованы.")
                return {"status": "failed", "message": "No activation codes available"}

            # Use a database transaction to lock the activation code entry during the update
            try:
                print(f"Attempting to assign activation code {activation_code_entry.code}")  # Debugging
                success = await activation_code_service.assign_activation_code(
                    activation_code_entry.code, phone_number, device, receipt_number
                )
                if success:
                    google_sheet.append_activation_code_row(
                        activation_code_entry.code, phone_number, device, receipt_number
                    )
                    print(f"Google Sheet appended with code {activation_code_entry.code}")

                    print("Activation code successfully assigned")  # Debugging
                    await telegram_bot.send_message(chat_id, f"Спасибо! Ваш код активации: {activation_code_entry.code}")
                    
                    # Clear user state after successful save
                    del user_state[chat_id]
                    return {"status": "success", "message": "Activation code sent"}
            except Exception as e:
                print(f"Error assigning activation code: {e}")  # Debugging
                # Retry in case of error due to concurrent access

    else:
        # Handle unexpected inputs based on the current stage
        if user_stage == "waiting_for_phone_number":
            await telegram_bot.send_message(chat_id, "Пожалуйста, укажите номер телефона в формате 77023334455.")
        elif user_stage == "waiting_for_device":
            await telegram_bot.send_message(chat_id, "Пожалуйста, укажите модель вашего телефона.")
        else:
            await telegram_bot.send_message(chat_id, "Пожалуйста, отправьте чек в формате PDF.")
        return {"status": "waiting", "message": "Awaiting correct input"}