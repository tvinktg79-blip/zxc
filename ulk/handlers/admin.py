import asyncio
import logging

from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

from config import ADMIN_ID

router = Router()


async def broadcast(bot: Bot, text: str, user_ids: list[int]):
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
        except Exception as e:
            logging.error(f"Не удалось отправить {uid}: {e}")
        await asyncio.sleep(0.05)  # чтобы не ловить флуд


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, bot: Bot):
    if message.from_user.id != ADMIN_ID:
        await message.answer("У тебя нет прав использовать эту команду.")
        return

    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Напиши текст после команды: /broadcast текст рекламы")
        return

    # тут должен быть список user_ids из БД
    user_ids = [1336313898]  # пока для теста только ты

    await broadcast(bot, text, user_ids)
    await message.answer("Рассылка завершена.")
