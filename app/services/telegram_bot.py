# app/services/telegram_bot.py
import os
import requests
from PIL import Image
from io import BytesIO
import pytesseract
import fitz  # PyMuPDF

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def download_file(file_id):
    # Step 1: Get the file path from Telegram
    file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    response = requests.get(file_url)
    file_info = response.json()

    # Check if the response was successful
    if not response.ok or "result" not in file_info:
        raise Exception("Failed to get file info from Telegram")

    file_path = file_info["result"]["file_path"]

    # Step 2: Download the file
    file_link = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    file_response = requests.get(file_link)

    # Check if the download was successful
    if not file_response.ok:
        raise Exception("Failed to download file from Telegram")

    # Save the file locally
    local_file_path = "receipt.png"  # You can customize the filename
    with open(local_file_path, "wb") as f:
        f.write(file_response.content)

    return local_file_path

async def send_message(chat_id, message_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message_text}
    response = requests.post(url, json=payload)
    return response.json()

async def get_file_text(file_id, is_pdf=False):
    # Get file path from Telegram
    file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    file_info = requests.get(file_url).json()
    file_path = file_info['result']['file_path']
    
    # Download file
    file_link = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    response = requests.get(file_link)
    
    # Process as PDF if needed
    if is_pdf:
        text = ""
        with BytesIO(response.content) as pdf_file:
            pdf_document = fitz.open(stream=pdf_file, filetype="pdf")
            for page_num in range(pdf_document.page_count):
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap()
                img = Image.open(BytesIO(pix.tobytes("png")))
                text += pytesseract.image_to_string(img) + "\n"
            pdf_document.close()
        return text
    else:
        # Process as image
        img = Image.open(BytesIO(response.content))
        return pytesseract.image_to_string(img)
