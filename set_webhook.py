# set_webhook.py

import os
import requests
from dotenv import load_dotenv

# Load environment variables from a specified .env file path
load_dotenv("/root/expense-tracker-automation/.env")

# Retrieve environment variables
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")

if bot_token and webhook_url:
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    response = requests.post(url, data={"url": webhook_url})
    if response.status_code == 200:
        print("Webhook set successfully!")
    else:
        print(f"Failed to set webhook: {response.status_code}, {response.text}")
else:
    print("TELEGRAM_BOT_TOKEN or TELEGRAM_WEBHOOK_URL is missing.")
