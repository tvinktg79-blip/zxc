from aiogram import Router, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, FSInputFile, Message
import os

router = Router()

# клавиатура курсов
courses_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Курс 1"), KeyboardButton(text="Курс 2")],
        [KeyboardButton(text="Курс 3"), KeyboardButton(text="Курс 4")],
        [KeyboardButton(text="Курс 5"), KeyboardButton(text="Курс 6")],
    ],
    resize_keyboard=True
)

# 1 курс
groups_kb_1 = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="КБА-101"), KeyboardButton(text="КЗМ-101")],
        [KeyboardButton(text="КИП-101"), KeyboardButton(text="КСП-101")],
        [KeyboardButton(text="КЛЛ-101"), KeyboardButton(text="КЛЛ-111")],
        [KeyboardButton(text="КТД-101"), KeyboardButton(text="КТД-111")],
        [KeyboardButton(text="КТК-101"), KeyboardButton(text="КТО-101")],
        [KeyboardButton(text="КФЛ-101")],
        [KeyboardButton(text="Назад к выбору курса")],
    ],
    resize_keyboard=True
)

# 2 курс
groups_kb_2 = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="КБА-201"), KeyboardButton(text="КЗМ-201")],
        [KeyboardButton(text="КЗМ-202"), KeyboardButton(text="КИП-201")],
        [KeyboardButton(text="КЛЛ-201"), KeyboardButton(text="КСП-201")],
        [KeyboardButton(text="КТД-201"), KeyboardButton(text="КТО-201")],
        [KeyboardButton(text="КФЛ-201")],
        [KeyboardButton(text="КСП-211"), KeyboardButton(text="КЛЛоз-211")],
        [KeyboardButton(text="КЛЛ-211")],
        [KeyboardButton(text="Назад к выбору курса")],
    ],
    resize_keyboard=True
)

# 3 курс
groups_kb_3 = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="КЗМ-301"), KeyboardButton(text="КЗМ-302")],
        [KeyboardButton(text="КЛЛ-301"), KeyboardButton(text="КЛЛ-302")],
        [KeyboardButton(text="КТД-301"), KeyboardButton(text="КФЛ-301")],
        [KeyboardButton(text="КСП-301"), KeyboardButton(text="КЛЛ-311")],
        [KeyboardButton(text="КЗМ-311")],
        [KeyboardButton(text="Назад к выбору курса")],
    ],
    resize_keyboard=True
)

# 4 курс
groups_kb_4 = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="КЛЛ-401"), KeyboardButton(text="КЛЛ-402")],
        [KeyboardButton(text="КСП-401"), KeyboardButton(text="КТД-401")],
        [KeyboardButton(text="Назад к выбору курса")],
    ],
    resize_keyboard=True
)

# файлы расписаний (пути или file_id – пока пути)
GROUP_FILES = {
    "КБА-101": "files/rasp_kba101.pdf",
    "КЗМ-101": "files/rasp_kzm101.pdf",
    "КИП-101": "files/rasp_kip101.pdf",
    "КСП-101": "files/rasp_ksp101.pdf",
    # ... сюда все остальные группы 1–4 курса
}


@router.message(F.text == "Курс 1")
async def handle_course_1(message: Message):
    await message.answer(
        "Выбери группу 1 курса:",
        reply_markup=groups_kb_1
    )


@router.message(F.text == "Курс 2")
async def handle_course_2(message: Message):
    await message.answer(
        "Выбери группу 2 курса:",
        reply_markup=groups_kb_2
    )


@router.message(F.text == "Курс 3")
async def handle_course_3(message: Message):
    await message.answer(
        "Выбери группу 3 курса:",
        reply_markup=groups_kb_3
    )


@router.message(F.text == "Курс 4")
async def handle_course_4(message: Message):
    await message.answer(
        "Выбери группу 4 курса:",
        reply_markup=groups_kb_4
    )


@router.message(F.text == "Курс 5")
async def handle_course_5(message: Message):
    await message.answer("Для 5 курса группы пока нет, скоро будет 🙂")


@router.message(F.text == "Курс 6")
async def handle_course_6(message: Message):
    await message.answer("Для 6 курса группы пока нет, скоро будет 🙂")


@router.message(F.text == "Назад к выбору курса")
async def back_to_courses(message: Message):
    await message.answer(
        "Снова выбери курс:",
        reply_markup=courses_kb
    )


@router.message(F.text.in_(GROUP_FILES.keys()))
async def send_group_rasp(message: Message):
    filename = GROUP_FILES[message.text]

    if not os.path.exists(filename):
        await message.answer(f"Для группы {message.text} расписание скоро будет 🙂")
        return

    loading_msg = await message.answer("Загрузка...")

    try:
        doc = FSInputFile(filename)
        await message.answer_document(
            document=doc,
            caption=f"Расписание {message.text}"
        )
    finally:
        try:
            await loading_msg.delete()
        except Exception:
            pass
