import asyncio
import logging
import aiohttp
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN, WEBHOOK_URL

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Список услуг (в реальности можно брать из Google Sheets, но для MVP захардкодим)
SERVICES = {
    "hair": "Стрижка (1500 ₽)",
    "color": "Окрашивание (5000 ₽)",
    "manicure": "Маникюр (2000 ₽)"
}

class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_service = State()
    waiting_for_date = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Здравствуйте! Давайте оформим заявку.\n\nКак вас зовут?")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    # Создаем кнопки для выбора услуги
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"service_{key}")] 
        for key, name in SERVICES.items()
    ])
    
    await message.answer("Выберите услугу:", reply_markup=keyboard)
    await state.set_state(OrderState.waiting_for_service)

@dp.callback_query(OrderState.waiting_for_service, F.data.startswith("service_"))
async def process_service(callback: CallbackQuery, state: FSMContext):
    service_key = callback.data.split("_")[1]
    service_name = SERVICES.get(service_key, "Неизвестно")
    
    await state.update_data(service=service_name)
    await callback.message.edit_text(f"Вы выбрали: {service_name}\n\nНа какую дату вас записать? (Напишите, например: 25.10 в 15:00)")
    await state.set_state(OrderState.waiting_for_date)

@dp.message(OrderState.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data['name']
    service = user_data['service']
    date = message.text
    
    # Формируем данные для отправки
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "name": name,
        "service": service,
        "desired_date": date,
        "user_id": message.from_user.id
    }
    
    # Отправляем в n8n
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=payload) as response:
                if response.status == 200:
                    await message.answer(f"✅ Спасибо, {name}!\nВаша заявка на {service} на {date} принята.")
                else:
                    await message.answer("⚠️ Ошибка отправки данных. Попробуйте позже.")
    except Exception as e:
        logging.error(f"Ошибка Webhook: {e}")
        await message.answer("⚠️ Сервер временно недоступен.")
    
    await state.clear()

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
