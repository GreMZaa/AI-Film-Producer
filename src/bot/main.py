import asyncio
import sys
from src.bot.bot import dp, bot
from src.bot.handlers import router

async def main():
    # Register router
    dp.include_router(router)
    
    print("🎬 ИИ-Продюсер вышел на площадку. Мотор!")
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🎬 Смена окончена. Все свободны.")
        sys.exit(0)
