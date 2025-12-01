import os
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import gspread
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)

# TOKEN из Replit Secrets
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # можно задать в Secrets
SHEET_KEY = os.getenv("GOOGLE_SHEETS_KEY")

# Подключение к Google Sheets
service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
service_account_info = json.loads(service_json)
gc = gspread.service_account_from_dict(service_account_info)
sheet = gc.open_by_key(SHEET_KEY).sheet1


# FSM (состояния анкеты)
class Form(StatesGroup):
    name = State()
    age = State()
    city = State()
    goal = State()
    result = State()
    experience = State()
    stress = State()
    time = State()
    budget = State()
    contact = State()


bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# ---------- КНОПКИ ----------
def kb_goals():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Набрать массу 💪", "Похудение ✨")
    keyboard.add("Гибкость 🧘", "Здоровье 🌿")
    return keyboard

def kb_experience():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Нет опыта", "Домашние тренировки")
    kb.add("Самостоятельно в зале", "Персональные тренировки")
    return kb

def kb_stress():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣")
    return kb

def kb_time():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("2 раза/нед", "3 раза/нед")
    kb.add("4 раза/нед", "5+ раз/нед")
    return kb

def kb_budget():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("10–20 тыс", "20–30 тыс", "30–40 тыс", "40–50 тыс")
    kb.add("Гибкий бюджет")
    return kb


# ---------- ЛОГИКА ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "Привет! 🌿\n"
        "Давай подберу тренировочный план под тебя.\n"
        "Ответы займут 1–2 минуты 🙌\n\n"
        "Как тебя зовут?",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await Form.name.set()


@dp.message_handler(state=Form.name)
async def form_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Сколько тебе лет?")
    await Form.age.set()


@dp.message_handler(state=Form.age)
async def form_age(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.answer("Из какого ты города?")
    await Form.city.set()


@dp.message_handler(state=Form.city)
async def form_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Какая твоя цель?", reply_markup=kb_goals())
    await Form.goal.set()


@dp.message_handler(state=Form.goal)
async def form_goal(message: types.Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await message.answer("Сколько кг хочешь набрать/сбросить?")
    await Form.result.set()


@dp.message_handler(state=Form.result)
async def form_result(message: types.Message, state: FSMContext):
    await state.update_data(result=message.text)
    await message.answer("Какой у тебя тренировочный опыт?", reply_markup=kb_experience())
    await Form.experience.set()


@dp.message_handler(state=Form.experience)
async def form_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await message.answer("Уровень стресса (1–5)?", reply_markup=kb_stress())
    await Form.stress.set()


@dp.message_handler(state=Form.stress)
async def form_stress(message: types.Message, state: FSMContext):
    await state.update_data(stress=message.text)
    await message.answer("Сколько времени готов(а) уделять?", reply_markup=kb_time())
    await Form.time.set()


@dp.message_handler(state=Form.time)
async def form_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer("Какой бюджет подходит?", reply_markup=kb_budget())
    await Form.budget.set()


@dp.message_handler(state=Form.budget)
async def form_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=message.text)
    username = message.from_user.username
    await state.update_data(contact=f"@{username}" if username else "нет username")

    data = await state.get_data()

    # ---------- Сохраняем в Google Sheets ----------
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        data["name"],
        data["age"],
        data["city"],
        data["goal"],
        data["result"],
        data["experience"],
        data["stress"],
        data["time"],
        data["budget"],
        data["contact"],
        message.from_user.id,
    ])

    # ---------- Отправляем админу ----------
    if ADMIN_ID:
        text_admin = (
            "📩 Новая анкета!\n\n"
            f"Имя: {data['name']}\n"
            f"Возраст: {data['age']}\n"
            f"Город: {data['city']}\n"
            f"Цель: {data['goal']}\n"
            f"Результат: {data['result']}\n"
            f"Опыт: {data['experience']}\n"
            f"Стресс: {data['stress']}\n"
            f"Время: {data['time']}\n"
            f"Бюджет: {data['budget']}\n"
            f"Контакт: {data['contact']}\n"
            f"ID: {message.from_user.id}"
        )
        await bot.send_message(ADMIN_ID, text_admin)

    # ---------- Пользователю ----------
    await message.answer(
        "Спасибо! 🌱\n"
        "Тренер получил твою анкету и свяжется в ближайшее время.",
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.finish()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
