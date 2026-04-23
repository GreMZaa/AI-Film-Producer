import os
import sys
import logging
from fastapi import FastAPI, Request

# Add the parent directory to sys.path so Vercel can find 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import types
from src.bot.bot import dp, bot
from src.bot.handlers import router

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from aiogram import types
    from src.bot.bot import dp, bot
    from src.bot.handlers import router
    # Register router
    dp.include_router(router)
except Exception as e:
    logger.error(f"Initialization error: {e}")
    # We define a dummy app if imports fail so we can at least return the error
    app = FastAPI()
    @app.get("/{path:path}")
    async def error_handler(path: str):
        return {"error": "Initialization failed", "details": str(e)}
    # If we are here, we don't want the rest of the code to run normally
    # but FastAPI needs the 'app' object.
else:
    app = FastAPI()

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
