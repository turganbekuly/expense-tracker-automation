# app/main.py
from fastapi import FastAPI
from app.routers import webhooks
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI()

# Include webhooks router for Telegram integration
app.include_router(webhooks.router)

@app.get("/")
async def root():
    return {"message": "Expense Tracker API is up and running"}
