import os
import sys
import logging
from fastapi import FastAPI, Request

# Add the parent directory to sys.path so Vercel can find 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MUST BE AT TOP LEVEL FOR VERCEL
app = FastAPI()

try:
    from aiogram import types
    from src.bot.bot import dp, bot
    from src.bot.handlers import router
    
    # Register router
    dp.include_router(router)
    
    @app.get("/")
    async def root():
        return {"message": "Cloud Bot is active"}

    @app.get("/set-webhook")
    async def set_webhook(request: Request):
        base_url = str(request.base_url).rstrip('/')
        webhook_url = f"{base_url}/webhook"
        try:
            success = await bot.set_webhook(webhook_url)
            if success:
                return {"status": "ok", "message": f"Webhook set to {webhook_url}"}
            return {"status": "error", "message": "Failed to set webhook"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @app.post("/webhook")
    async def webhook_handler(request: Request):
        try:
            update_data = await request.json()
            update = types.Update(**update_data)
            await dp.feed_update(bot, update)
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return {"status": "error", "message": str(e)}

except Exception as ex:
    err = str(ex)
    logger.error(f"Initialization error: {err}")
    
    @app.get("/{path:path}")
    async def error_handler(path: str):
        return {
            "error": "Initialization failed",
            "details": err,
            "message": "Check Vercel environment variables (BOT_TOKEN) and logs."
        }
