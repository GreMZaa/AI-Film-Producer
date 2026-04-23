import os
import logging
from fastapi import FastAPI, Request
from aiogram import types
from src.bot.bot import dp, bot
from src.bot.handlers import router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Register router
dp.include_router(router)

@app.get("/")
async def root():
    return {"message": "Cloud Bot is active"}

@app.get("/set-webhook")
async def set_webhook(request: Request):
    # Construct the webhook URL based on the current request
    base_url = str(request.base_url).rstrip('/')
    webhook_url = f"{base_url}/webhook"
    
    try:
        success = await bot.set_webhook(webhook_url)
        if success:
            return {"status": "ok", "message": f"Webhook set to {webhook_url}"}
        else:
            return {"status": "error", "message": "Failed to set webhook"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        # We need to use the dispatcher to handle the update
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
