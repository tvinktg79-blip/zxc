import logging

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart

router = Router()

CHANNEL_USERNAME = "@focusinghrie"  # твой канал


async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        return False


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    if not await check_subscription(bot, message.from_user.id):
        await message.answer(
            "Чтобы пользоваться ботом, подпишись на канал:\n"
            "https://t.me/focusinghrie"
        )
        return

    from handlers.schedule import courses_kb

    await message.answer(
        "Привет, я бот УЛК по расписанию.\n"
        "Выбери курс:",
        reply_markup=courses_kb
    )
