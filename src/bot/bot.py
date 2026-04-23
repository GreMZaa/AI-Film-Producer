import logging
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from src.api.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)

# Define States
class DirectorStates(StatesGroup):
    AwaitingBrief = State()
    ScriptApproval = State()
    StoryboardApproval = State()
    Rendering = State()

# Initialize Bot and Dispatcher
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Sarcastic Director Personality Protos
DIRECTOR_QUOTES = {
    "start": "О, приперся очередной 'гений'. Ну че, есть че гениальное или опять будем снимать артхаус про грустный кирпич? Давай свой бриф, только не заставляй меня жалеть о том, что я не ушел в IT.",
    "brief_received": "Хм... '{brief}'. Это либо Оскар, либо мы пойдем по миру. Жди, отправляю на препродакшен в свой гараж.",
    "server_error": "Твою мать! Кажется, мой ноут решил, что он слишком стар для этого дерьма. API лег. Сходи за кофе, пока я пинаю сервак.",
    "script_ready": "Сценарий готов. Перекурил три раза, пока читал. Это... специфично. Посмотри, если кровь из глаз не пойдет — утвердим.",
    "rendering": "Запускаю движок. Вентиляторы воют, как грешники в аду. Не пиши мне, пока не закончу.",
    "help": "Команды? Тут тебе не армия. \n/start — начать новый 'шедевр'. \n/help — эта бесполезная справка."
}
