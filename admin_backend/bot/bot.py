import os
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

import httpx
from dotenv import load_dotenv
from aiogram.client.default import DefaultBotProperties

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher(storage=MemoryStorage())

from gigachat_ai import ask_gigachat   # <-- ПРАВИЛЬНОЕ МЕСТО ИМПОРТА


# ---------------------------------------------------
#                   API HELPERS
# ---------------------------------------------------

async def api_get(path: str, params: dict | None = None):
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


async def api_post(path: str, data: dict):
    url = f"{API_BASE_URL}{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=data)
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------
#                   FSM BOOKING
# ---------------------------------------------------

class BookingStates(StatesGroup):
    choosing_hotel = State()
    choosing_room = State()
    entering_date_from = State()
    entering_date_to = State()
    entering_guest_name = State()
    entering_phone = State()
    entering_email = State()
    confirming = State()


# ---------------------------------------------------
#                   /start
# ---------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "Привет! Это SmartHotel 360.\n\n"
        "Я помогу подобрать свободный номер и оформить бронирование.\n"
        "Нажми /hotels, чтобы выбрать отель."
    )
    await message.answer(text)


# ---------------------------------------------------
#               /hotels LIST
# ---------------------------------------------------

@dp.message(Command("hotels"))
async def cmd_hotels(message: Message, state: FSMContext):
    await state.clear()

    hotels = await api_get("/hotels/")

    if not hotels:
        await message.answer("Пока нет ни одного отеля в системе.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=h["name"], callback_data=f"hotel:{h['id']}")]
            for h in hotels
        ]
    )

    await message.answer("Выбери отель:", reply_markup=kb)
    await state.set_state(BookingStates.choosing_hotel)


# ---------------------------------------------------
#             HOTEL CHOSEN → FREE ROOMS
# ---------------------------------------------------

@dp.callback_query(F.data.startswith("hotel:"))
async def hotel_chosen(callback: CallbackQuery, state: FSMContext):
    hotel_id = int(callback.data.split(":")[1])
    await state.update_data(hotel_id=hotel_id)

    rooms = await api_get("/rooms/", params={"hotel": hotel_id})

    if not rooms:
        await callback.message.edit_text(
            "В этом отеле нет свободных номеров. Используй /hotels чтобы выбрать другой."
        )
        await state.clear()
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{r['room_number']} — {r['room_type']} ({r['price_per_night']} ₽/ночь)",
                    callback_data=f"room:{r['id']}",
                )
            ]
            for r in rooms
        ]
    )

    await callback.message.edit_text("Выбери номер:", reply_markup=kb)
    await state.set_state(BookingStates.choosing_room)


# ---------------------------------------------------
#               ROOM CHOSEN → DATE FROM
# ---------------------------------------------------

@dp.callback_query(F.data.startswith("room:"))
async def room_chosen(callback: CallbackQuery, state: FSMContext):
    room_id = int(callback.data.split(":")[1])
    data = await state.get_data()

    rooms = await api_get("/rooms/", params={"hotel": data["hotel_id"]})
    room = next((r for r in rooms if r["id"] == room_id), None)

    if room is None:
        await callback.answer("Ошибка. Попробуй снова.")
        return

    await state.update_data(
        room_id=room_id,
        room_price=float(room["price_per_night"]),
        room_number=room["room_number"],
        room_type=room["room_type"],
    )

    await callback.message.edit_text("Введи дату заезда (ДД.ММ.ГГГГ):")
    await state.set_state(BookingStates.entering_date_from)


# ---------------------------------------------------
#                       DATE PARSER
# ---------------------------------------------------

def parse_date(text: str) -> Optional[datetime.date]:
    try:
        return datetime.strptime(text.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


# ---------------------------------------------------
#                   DATE FROM → DATE TO
# ---------------------------------------------------

@dp.message(BookingStates.entering_date_from)
async def enter_date_from(message: Message, state: FSMContext):
    date_from = parse_date(message.text)

    if not date_from:
        await message.answer("Неверный формат! Введи ДД.ММ.ГГГГ.")
        return

    await state.update_data(date_from=str(date_from))
    await message.answer("Теперь введи дату выезда (ДД.ММ.ГГГГ):")
    await state.set_state(BookingStates.entering_date_to)


@dp.message(BookingStates.entering_date_to)
async def enter_date_to(message: Message, state: FSMContext):
    date_to = parse_date(message.text)
    if not date_to:
        await message.answer("Неверный формат! Введи ДД.ММ.ГГГГ.")
        return

    data = await state.get_data()
    date_from = parse_date(data["date_from"])

    if date_to <= date_from:
        await message.answer("Дата выезда должна быть позже заезда.")
        return

    await state.update_data(date_to=str(date_to))
    await message.answer("Как зовут гостя?")
    await state.set_state(BookingStates.entering_guest_name)


# ---------------------------------------------------
#                NAME → PHONE → EMAIL
# ---------------------------------------------------

@dp.message(BookingStates.entering_guest_name)
async def enter_guest_name(message: Message, state: FSMContext):
    await state.update_data(guest_name=message.text.strip())
    await message.answer("Введите номер телефона:")
    await state.set_state(BookingStates.entering_phone)


@dp.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext):
    await state.update_data(guest_phone=message.text.strip())
    await message.answer("Введите Email:")
    await state.set_state(BookingStates.entering_email)


@dp.message(BookingStates.entering_email)
async def enter_email(message: Message, state: FSMContext):
    await state.update_data(guest_email=message.text.strip())

    data = await state.get_data()

    date_from = parse_date(data["date_from"])
    date_to = parse_date(data["date_to"])
    nights = (date_to - date_from).days
    total_price = nights * data["room_price"]

    await state.update_data(total_price=total_price, nights=nights)

    text = (
        "<b>Проверь бронирование:</b>\n\n"
        f"Номер: {data['room_number']} — {data['room_type']}\n"
        f"Даты: {data['date_from']} → {data['date_to']} ({nights} ночей)\n"
        f"Гость: {data['guest_name']}\n"
        f"Телефон: {data['guest_phone']}\n"
        f"Email: {data['guest_email']}\n"
        f"Итого: <b>{total_price:.0f} ₽</b>"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm_yes"),
                InlineKeyboardButton(text="Отменить", callback_data="confirm_no"),
            ]
        ]
    )

    await message.answer(text, reply_markup=kb)
    await state.set_state(BookingStates.confirming)


# ---------------------------------------------------
#                CONFIRMATION
# ---------------------------------------------------

@dp.callback_query(BookingStates.confirming, F.data == "confirm_no")
async def confirm_no(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Бронирование отменено.")
    await callback.answer()


@dp.callback_query(BookingStates.confirming, F.data == "confirm_yes")
async def confirm_yes(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    payload = {
        "hotel": data["hotel_id"],
        "room": data["room_id"],
        "guest_name": data["guest_name"],
        "guest_phone": data["guest_phone"],
        "guest_email": data["guest_email"],
        "date_from": data["date_from"],
        "date_to": data["date_to"],
        "total_price": data["total_price"],
        "is_confirmed": False,
    }

    try:
        booking = await api_post("/booking/", payload)
    except Exception:
        await callback.message.edit_text("Ошибка при создании брони.")
        await state.clear()
        return

    await callback.message.edit_text(
        f"Бронирование создано!\nНомер заявки: <b>{booking['id']}</b>"
    )
    await state.clear()


# ---------------------------------------------------
#                AI ASSISTANT
# ---------------------------------------------------

class AiStates(StatesGroup):
    ai_mode = State()


@dp.message(Command("ai"))
async def activate_ai(message: Message, state: FSMContext):
    await state.set_state(AiStates.ai_mode)
    await message.answer(
        "AI-ассистент активирован.\n"
        "Спроси меня о свободных номерах, отелях или бронировании."
    )


@dp.message(AiStates.ai_mode)
async def ai_answer(message: Message, state: FSMContext):
    system_prompt = (
        "Ты — умный AI-ассистент SmartHotel.\n"
        "Ты помогаешь гостям. Не придумывай данные.\n"
        "Если нужно узнать свободные номера — предложи команду /rooms.\n"
        "Если хотят забронировать — предложи /book или /hotels.\n"
    )

    text_for_ai = f"{system_prompt}\nВопрос: {message.text}"

    try:
        reply = ask_gigachat(text_for_ai)
    except Exception:
        reply = "AI-ассистент временно недоступен."

    await message.answer(reply)


# ---------------------------------------------------
#                ENTRY POINT
# ---------------------------------------------------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
