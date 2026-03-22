import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import API_TOKEN
from handlers import schedule, moderation, auth, admin

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(API_TOKEN)
    dp = Dispatcher()

    # подключаем роутеры
    dp.include_router(auth.router)        # /start + проверка подписки
    dp.include_router(schedule.router)    # расписание
    dp.include_router(moderation.router)  # мат, антифлуд, приветствие
    dp.include_router(admin.router)       # админ-команды (/broadcast)

    logging.info("Старт polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

