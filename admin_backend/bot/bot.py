import os
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

import httpx
from dotenv import load_dotenv

# ===================================================
# ЛОГИРОВАНИЕ И КОНФИГУРАЦИЯ
# ===================================================
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

from gigachat_ai import ask_gigachat
from rag import knowledge_query


# ===================================================
# КОНСТАНТЫ
# ===================================================
ROOM_TOURS = {
    "семейный": "https://goguide.ru/tour/1255",
    "стандарт 1": "https://goguide.ru/tour/1248",
    "стандарт 2": "https://goguide.ru/tour/1260",
    "стандарт 3": "https://goguide.ru/tour/1262",
    "стандарт 4": "https://goguide.ru/tour/1254",
    "стандарт 5": "https://goguide.ru/tour/1250",
    "стандарт 6": "https://goguide.ru/tour/1261",
}


def extract_room_query(text: str) -> Optional[str]:
    text = text.lower().strip()
    if "семейн" in text:
        return "семейный"
    for i in range(1, 7):
        if f"номер {i}" in text or text == str(i):
            return f"стандарт {i}"
    if "стандарт" in text:
        return "стандарт 1"
    return None


# ===================================================
# API HELPERS
# ===================================================
async def api_get(path: str, params=None):
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE_URL}{path}", params=params)
        r.raise_for_status()
        return r.json()


# ===================================================
# FSM
# ===================================================
class AiStates(StatesGroup):
    ai_mode = State()


class BookingStates(StatesGroup):
    choosing_hotel = State()
    choosing_room = State()
    entering_date_from = State()
    entering_date_to = State()
    entering_guest_name = State()
    entering_phone = State()
    entering_email = State()
    confirming = State()


# ===================================================
# КЛЮЧЕВЫЕ ФРАЗЫ
# ===================================================
BOOKING_TRIGGER_PHRASES = [
    "забронируй", "хочу забронировать", "давай бронь", "отлично давай", "беру",
    "забираю", "оформи", "хочу снять", "забронировать", "давай его", "забронь",
    "забронировать номер", "хочу забронировать номер", "давай забронируем"
]


# ===================================================
# UI
# ===================================================
def bottom_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏢 Отели"), KeyboardButton(text="🎥 Туры 360°")],
        ],
        resize_keyboard=True
    )


# ===================================================
# КОММАНДЫ И КНОПКИ
# ===================================================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(AiStates.ai_mode)
    await message.answer(
        "Привет! Я виртуальный консьерж SmartHotel.\n"
        "Снизу есть меню — выбирай нужный раздел.",
        reply_markup=bottom_menu(),
    )


@dp.message(F.text == "🏢 Отели")
async def list_hotels(message: Message, state: FSMContext):
    hotels = await api_get("/hotels/")
    if not hotels:
        await message.answer("У нас пока нет отелей.", reply_markup=bottom_menu())
        return

    text = "Вот отели в нашей системе:\n\n"
    for h in hotels:
        desc = h.get("description", "")[:120]
        text += f"🏨 <b>{h['name']}</b>\n📍 {h['address']}\n{desc}...\n\n"
    await message.answer(text, reply_markup=bottom_menu())


@dp.message(F.text == "🎥 Туры 360°")
async def reply_tours(message: Message, state: FSMContext):
    hotels = await api_get("/hotels/")
    if not hotels:
        await message.answer("Нет отелей.", reply_markup=bottom_menu())
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=h["name"], callback_data=f"tourhotel:{h['id']}")]
            for h in hotels
        ]
    )
    await message.answer("Выберите отель:", reply_markup=kb)


# ===================================================
# ОСНОВНОЙ ОБРАБОТЧИК
# ===================================================
@dp.message(AiStates.ai_mode)
async def handle_message(message: Message, state: FSMContext):
    text = message.text.strip()
    data = await state.get_data()
    selected_hotel_name = data.get("selected_hotel_name")

    # --- 1. Проверка: содержит ли текст название какого-то отеля? ---
    hotels = await api_get("/hotels/")
    for h in hotels:
        if h["name"].lower() in text.lower():
            await state.update_data(selected_hotel_id=h["id"], selected_hotel_name=h["name"])
            await message.answer(
                f"✅ Выбран отель: <b>{h['name']}</b>\n"
                "Теперь вы можете спросить про номера, услуги или забронировать.",
                reply_markup=bottom_menu()
            )
            return

    # --- 2. Запрос про конкретный номер ---
    room_key = extract_room_query(text)
    if room_key:
        hotel_id = data.get("selected_hotel_id")
        if not hotel_id:
            await message.answer("Сначала выберите отель через кнопку «Отели».", reply_markup=bottom_menu())
            return

        rooms = await api_get("/rooms/", params={"hotel": hotel_id})
        found = None
        for r in rooms:
            rn = str(r["room_number"])
            if room_key == "семейный" and "семейн" in r["room_type"].lower():
                found = r
                break
            if room_key.endswith(rn):
                found = r
                break

        if found:
            link = ROOM_TOURS.get(room_key)
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="Открыть 360° тур", url=link)]]
            ) if link else None

            await message.answer(
                f"<b>{found['room_type']}</b>\n"
                f"Номер: {found['room_number']}\n"
                f"Цена: {found['price_per_night']} ₽\n\n"
                f"Хочешь забронировать? Напиши «забронировать».",
                reply_markup=kb or bottom_menu(),
            )
            return

    # --- 3. Явный переход к бронированию ---
    if any(phrase in text.lower() for phrase in BOOKING_TRIGGER_PHRASES):
        await start_booking(message, state)
        return

    # --- 4. Общий AI-ответ с контекстом отеля ---
    try:
        context = knowledge_query(text, filter={"hotel": selected_hotel_name}) if selected_hotel_name else ""
    except Exception as e:
        logging.error(f"RAG error: {e}")
        context = ""

    system_prompt = (
    f"Ты — консьерж отеля «{selected_hotel_name}». "
    "Твоя задача — отвечать на вопросы пользователя, используя ТОЛЬКО информацию из предоставленного контекста. "
    "Не выдумывай ничего. Не добавляй свои комментарии. "
    "Если вопрос касается цен, номеров, услуг, питания, трансфера — найди в контексте точную информацию и ответь на неё. "
    "Если в контексте нет ответа — скажи: «Уточните у администратора отеля». "
    "Отвечай кратко, чётко и по делу. "
    "Если пользователь хочет забронировать — скажи: «Перехожу к бронированию...» и передай управление."
     ) if selected_hotel_name else (
    "Ты — консьерж SmartHotel. Пользователь ещё не выбрал отель. "
    "Посоветуй выбрать через кнопку «Отели». "
    "Не выдумывай отели или услуги."
     )

    answer = ask_gigachat(f"{system_prompt}\n\nКонтекст:\n{context}\nВопрос:\n{text}")
    await message.answer(answer, reply_markup=bottom_menu())


# ===================================================
# БРОНИРОВАНИЕ
# ===================================================
async def start_booking(message_or_callback, state: FSMContext):
    hotels = await api_get("/hotels/")
    if not hotels:
        msg = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
        await msg.answer("Нет доступных отелей.", reply_markup=bottom_menu())
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=h["name"], callback_data=f"hotel:{h['id']}")]
            for h in hotels
        ]
    )
    msg = message_or_callback if isinstance(message_or_callback, Message) else message_or_callback.message
    await msg.answer("Выберите отель:", reply_markup=kb)
    await state.set_state(BookingStates.choosing_hotel)


@dp.callback_query(F.data.startswith("hotel:"), BookingStates.choosing_hotel)
async def choose_hotel(callback: CallbackQuery, state: FSMContext):
    hotel_id = int(callback.data.split(":")[1])
    hotels = await api_get("/hotels/")
    hotel = next((h for h in hotels if h["id"] == hotel_id), None)
    if not hotel:
        await callback.answer("Отель не найден.", show_alert=True)
        return

    await state.update_data(selected_hotel_id=hotel_id, selected_hotel_name=hotel["name"])
    rooms = await api_get("/rooms/", params={"hotel": hotel_id})
    available = [r for r in rooms if r.get("is_available", True)]

    if not available:
        await callback.message.edit_text(
            f"В <b>{hotel['name']}</b> нет свободных номеров.", reply_markup=bottom_menu()
        )
        await state.set_state(AiStates.ai_mode)
        return

    text = f"Номера в <b>{hotel['name']}</b>:\n\n" + "\n".join(
        f"• {r['room_number']} — {r['room_type']} ({r['price_per_night']} ₽/ночь)"
        for r in available
    )
    text += "\n\nВыберите номер:"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{r['room_type']} №{r['room_number']}", callback_data=f"room:{r['id']}")]
            for r in available
        ]
    )
    await callback.message.edit_text(text, reply_markup=kb)
    await state.set_state(BookingStates.choosing_room)


@dp.callback_query(F.data.startswith("room:"), BookingStates.choosing_room)
async def choose_room(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split(":")[1])
    room = await api_get(f"/rooms/{room_id}/")
    await state.update_data(selected_room_id=room_id, selected_room_type=room["room_type"])
    await callback.message.edit_text("📅 Введите дату заезда (ДД.ММ.ГГГГ):")
    await state.set_state(BookingStates.entering_date_from)


# Пример следующего шага (можно расширять)
@dp.message(BookingStates.entering_date_from)
async def enter_date_from(message: Message, state: FSMContext):
    await state.update_data(date_from=message.text)
    await message.answer("📅 Введите дату выезда (ДД.ММ.ГГГГ):")
    await state.set_state(BookingStates.entering_date_to)


# ===================================================
# 360° ТУРЫ
# ===================================================
@dp.callback_query(F.data.startswith("tourhotel:"))
async def choose_tour_hotel(callback: CallbackQuery):
    hotel_id = int(callback.data.split(":")[1])
    rooms = await api_get("/rooms/", params={"hotel": hotel_id})
    if not rooms:
        await callback.message.answer("Нет номеров с 360° туром.", reply_markup=bottom_menu())
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=f"{r['room_type']} №{r['room_number']}",
                callback_data=f"tourroom:{r['room_number']}"
            )]
            for r in rooms
        ]
    )
    await callback.message.edit_text("Выберите номер:", reply_markup=kb)


@dp.callback_query(F.data.startswith("tourroom:"))
async def open_tour(callback: CallbackQuery):
    num = callback.data.split(":")[1]
    key = "семейный" if num == "семейный" else f"стандарт {num}"
    link = ROOM_TOURS.get(key)
    if not link:
        await callback.message.answer("Тур не найден.", reply_markup=bottom_menu())
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть 360° тур", url=link)]]
    )
    await callback.message.answer(f"Тур по номеру {num}:", reply_markup=kb)


# ===================================================
# ЗАПУСК
# ===================================================
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())