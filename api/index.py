import os
from fastapi import FastAPI, Request
from aiogram import types
from src.bot.bot import dp, bot
from src.bot.handlers import router

app = FastAPI()

# Register router
dp.include_router(router)

@app.get("/")
async def root():
    return {"message": "Cloud Bot is active"}

@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        update_data = await request.json()
        update = types.Update(**update_data)
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "error", "message": str(e)}
