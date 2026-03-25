# handlers/moderation.py
import logging
import time
from collections import defaultdict, deque

from aiogram import Router, F, Bot
from aiogram.types import Message, ChatPermissions, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter

from db import add_warning, is_muted, mute_user  # важно!

router = Router()

# ----- настройки -----

WARN_FOR_MUTE = 3          # после 3 предупреждений — мут
FLOOD_MAX_MSG = 10         # сообщений
FLOOD_INTERVAL = 30        # секунд

MIN_LETTERS_FOR_LANG_CHECK = 3
MIN_CYR_RATIO = 0.2        # доля русских букв

BAD_WORD_PATTERNS = {
    # Мат (твой старый список)
    "хуй", "хуе", "хуё", "хуя", "хую", "хуйн", "хуило",
    "пизд", "пизде", "пизди", "пизжу", "пезд", "пи3д",
    "еба", "ёба", "ебл", "ебуч", "ебан", "ёбн", "ебёт", "ебет",
    "бля", "бляд", "бл@д",
    "сука", "сучк", "сучар",
    "говн", "дерьм", "муда", "мудa", "мудил", "мудня",
    "пидор", "пидар", "пидр", "пидорок", "пидарас",
    "шлюх", "ублюд", "мраз", "чмо", "херн", "нахуй", "нахер", "нахрен",
    "дрис", "дрисн", "дрес", "дресь",
    "дерм", "дермо",
    "гавн",
    "поеб", "поёб",

    # Наркотики + торговля (новое)
    "меф", "мэф", "мет", "метамф", "метамфет", "амф", "амфа", "амфет",
    "мдм", "мдма", "экст", "экстази", "экста",
    "кок", "кокос", "кокс", "кокain",
    "lsd", "лсд", "кислота",
    "гашиш", "гаш", "гашик", "гашикш",
    "трав", "трава", "гасян", "план",
    "шнс", "шняга", "шмаль", "солей",
    "спайс", "спайк", "соль", "соли",
    "гер", "героин", "герка",
    "прода", "продаю", "продам", "куплю", "покупаю", "обмен", "обменяю",
    "товар", "товарчик", "товарик", "товару",

    # Крипта/скам (часто в чатах)
    "btc", "eth", "sol", "ton", "usdt", "bnb",
    "инвест", "влож", "заработ", "пассивн", "сигнал", "памп", "дамп",

    # Спам/реклама
    "сигнал", "памп", "дамп", "канал", "подпис", "подпишись",
    "ссылк", "ссылка", "реф", "реферал", "reflink",

    # Замены/обход фильтров
    "м3ф", "м3фет", "м3т", "м3ф3др",
    "м3т", "м3ф", "м3фа", "м3фет",
    "п3зда", "п3зд", "х3й", "х3у",
    "eбa", "е6a", "ё6a", "3бa",
}


BAD_WORDS_EXACT = {
    "хуй", "пизда", "сука", "мразь", "мудак", "пидор",
    "ебать", "ебаный", "ебанутая", "ебанутый",
    "дерьмо", "дермо", "гавно", "дрисьня", "дресьня", "поебота",
    "тварина", "тварь",
}

# in-memory счётчики (не в БД)
flood_messages = defaultdict(lambda: deque(maxlen=50))

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


# ========= основной фильтр =========

@router.message(F.text & ~F.text.startswith("/"))
async def filter_bad_words(message: Message, bot: Bot):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text or ""

    logging.info(f"[TXT] chat={chat_id} user={user_id}: {text!r}")

    # если пользователь в муте — просто удаляем всё
    if await is_muted(user_id):
        try:
            await message.delete()
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение от замьюченного: {e}")
        return

    # фильтр языка
    if is_suspicious_language(text):
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

        await mute_user(user_id)  # мут через БД
        warn = (
            f"{message.from_user.mention_html()}, не флуди.\n"
            f"Ты замучен на 10 минут за флуд."
        )
        await bot.send_message(chat_id, warn, parse_mode="HTML")
        return

    # мат
    if not has_bad_word(text):
        return

    # удаляем сообщение
    try:
        await message.delete()
    except Exception as e:
        logging.error(f"Не удалось удалить сообщение: {e}")

    # записываем предупреждение в БД
    warns = await add_warning(user_id)

    if warns >= WARN_FOR_MUTE:
        await mute_user(user_id)
        warn_text = (
            f"{message.from_user.mention_html()}, без мата.\n"
            f"Ты получил мут на 10 минут за {warns} нарушений."
        )
    else:
        warn_text = (
            f"{message.from_user.mention_html()}, без мата.\n"
            f"Предупреждение {warns}/{WARN_FOR_MUTE}."
        )

    await bot.send_message(chat_id, warn_text, parse_mode="HTML")


async def is_admin(bot: Bot, message: Message) -> bool:
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.is_chat_admin()
    except Exception as e:
        logging.error(f"Не удалось проверить админа: {e}")
        return False


# ========= приветствие =========

@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=True))
async def on_user_join(event: ChatMemberUpdated, bot: Bot):
    if event.new_chat_member.status == "member":
        user = event.new_chat_member.user
        chat_id = event.chat.id
        text = (
            f"Привет, {user.mention_html()}!\n"
            f"В этом чате запрещён мат, флуд и сообщения на других языках.\n"
            f"За нарушения — предупреждения и мут."
        )
        await bot.send_message(chat_id, text, parse_mode="HTML")

