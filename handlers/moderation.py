import logging
import time
from collections import defaultdict, deque

from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, Command


# этот router подключим в bot.py
router = Router()

# ====== ГЛОБАЛЬНЫЕ СТРУКТУРЫ ДЛЯ МОДЕРАЦИИ ======

WARN_FOR_MUTE = 3
WARN_FOR_BAN = 6
MUTE_SECONDS = 1800

FLOOD_MAX_MSG = 10
FLOOD_INTERVAL = 30

MIN_LETTERS_FOR_LANG_CHECK = 5
MIN_CYR_RATIO = 0.2

BAD_WORD_PATTERNS = {
    "хуй", "хуе", "хуё", "хуя", "хую", "хуйн", "хуило",
    "пизд", "пизде", "пизди", "пизжу", "пезд", "пи3д",
    "еба", "ёба", "ебл", "ебуч", "ебан", "ёбн", "ебёт", "ебет",
    "бля", "бляд", "бл@д",
    "сука", "сучк", "сучар",
    "говн", "дерьм", "муда", "мудa", "мудил", "мудня",
    "пидор", "пидар", "пидр", "пидорок", "пидарас", "пидарас",
    "шлюх", "ублюд", "мраз", "чмо", "херн", "нахуй", "нахер", "нахрен",
    "дрис", "дрисн", "дрес", "дресь",
    "дерм", "дермо",
    "гавн",
    "поеб", "поёб",
}

BAD_WORDS_EXACT = {
    "хуй", "пизда", "сука", "мразь", "мудак", "пидор",
    "ебать", "ебаный", "ебанутая", "ебанутый",
    "дерьмо", "дермо", "гавно", "дрисьня", "дресьня", "поебота",
    "тварина", "тварь",
}

violations = defaultdict(int)
LAST_MESSAGES = defaultdict(lambda: deque(maxlen=200))
flood_messages = defaultdict(lambda: deque(maxlen=50))
stats_deleted = defaultdict(int)

REPLACE_MAP = str.maketrans({
    "@": "a",
    "4": "a",
    "0": "o",
    "3": "e",
    "1": "i",
    "$": "s",
    "€": "е",
})

LATIN_TO_CYR = str.maketrans({
    "a": "а",
    "b": "б",
    "c": "с",
    "e": "е",
    "h": "н",
    "k": "к",
    "m": "м",
    "o": "о",
    "p": "р",
    "r": "р",
    "t": "т",
    "x": "х",
    "y": "у",
})


def normalize_text(text: str) -> str:
    t = text.lower()
    t = t.translate(REPLACE_MAP)
    t = t.translate(LATIN_TO_CYR)
    return t


def has_bad_word(text: str) -> bool:
    t = normalize_text(text)
    for w in BAD_WORDS_EXACT:
        if w in t:
            return True
    for root in BAD_WORD_PATTERNS:
        if root in t:
            return True
    return False


def is_suspicious_language(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    if len(letters) < MIN_LETTERS_FOR_LANG_CHECK:
        return False
    total = len(letters)
    cyr = sum("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in letters)
    ratio = cyr / total
    return ratio < MIN_CYR_RATIO


def check_flood(user_id: int) -> bool:
    now = time.time()
    q = flood_messages[user_id]
    q.append(now)
    while q and now - q[0] > FLOOD_INTERVAL:
        q.popleft()
    return len(q) > FLOOD_MAX_MSG


async def punish_user(bot: Bot, chat_id: int, user_id: int, count: int):
    if count >= WARN_FOR_BAN:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            logging.info(f"Пользователь {user_id} забанен (нарушений: {count})")
        except Exception as e:
            logging.error(f"Не удалось забанить пользователя {user_id}: {e}")
        return

    if count >= WARN_FOR_MUTE:
        until_date = int(time.time()) + MUTE_SECONDS
        perms = ChatPermissions(can_send_messages=False)
        try:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=perms,
                until_date=until_date,
            )
            logging.info(f"Пользователь {user_id} замучен на {MUTE_SECONDS} сек (нарушений: {count})")
        except Exception as e:
            logging.error(f"Не удалось замутить пользователя {user_id}: {e}")


# ========= ФИЛЬТР ТЕКСТА (мат + язык + флуд) =========

@router.message(F.text & ~F.text.startswith("/"))
async def filter_bad_words(message: Message, bot: Bot):
    logging.info(f"[TXT] chat={message.chat.id} user={message.from_user.id}: {message.text!r}")
    chat_id = message.chat.id
    user_id = message.from_user.id

    # фильтр языка
    if is_suspicious_language(message.text):
        try:
            await message.delete()
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение по языковому фильтру: {e}")
        warn = (
            f"{message.from_user.mention_html()}, сообщение удалено: "
            f"используйте, пожалуйста, русский язык."
        )
        await bot.send_message(chat_id, warn, parse_mode="HTML")
        return

    # антифлуд
    if check_flood(user_id):
        try:
            await message.delete()
        except Exception as e:
            logging.error(f"Не удалось удалить флуд-сообщение: {e}")

        until_date = int(time.time()) + MUTE_SECONDS
        perms = ChatPermissions(can_send_messages=False)
        try:
            await bot.restrict_chat_member(
                chat_id,
                user_id,
                permissions=perms,
                until_date=until_date,
            )
            warn = (
                f"{message.from_user.mention_html()}, не флуди.\n"
                f"Ты замучен на {MUTE_SECONDS} секунд за флуд."
            )
        except Exception as e:
            logging.error(f"Не удалось замутить за флуд пользователя {user_id}: {e}")
            warn = f"{message.from_user.mention_html()}, не флуди (слишком много сообщений)."

        await bot.send_message(chat_id, warn, parse_mode="HTML")
        return

    # сохраняем в буфер для периодической проверки
    LAST_MESSAGES[chat_id].append((message.message_id, message.text, user_id))

    # онлайн-проверка мата
    if not has_bad_word(message.text):
        return

    violations[user_id] += 1
    stats_deleted[user_id] += 1
    count = violations[user_id]

    try:
        await message.delete()
    except Exception as e:
        logging.error(f"Не удалось удалить сообщение: {e}")

    warn_text = (
        f"{message.from_user.mention_html()}, без мата.\n"
        f"Нарушение {count}."
    )
    await bot.send_message(chat_id, warn_text, parse_mode="HTML")

    await punish_user(bot, chat_id, user_id, count)

async def is_admin(bot: Bot, message: Message) -> bool:
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.is_chat_admin()
    except Exception as e:
        logging.error(f"Не удалось проверить админа: {e}")
        return False


# ========= ПРИВЕТСТВИЕ =========

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=True))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.status == "member":
        user = event.new_chat_member.user
        chat_id = event.chat.id
        text = (
            f"Привет, {user.mention_html()}!\n"
            f"В этом чате запрещён мат, флуд и сообщения на других языках.\n"
            f"За нарушения — предупреждения, мут и бан."
        )
        await bot.send_message(chat_id, text, parse_mode="HTML")
