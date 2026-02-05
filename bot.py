import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ARTISTS_FILE = "artists.json"
ADMINS_FILE = "admins.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ================== УТИЛИТЫ ==================

def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================== СОСТОЯНИЯ ==================

class AddArtist(StatesGroup):
    name = State()
    link = State()

# ================== КЛАВИАТУРЫ ==================

def main_menu(is_admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎤 Артисты"))
    if is_admin:
        kb.add(KeyboardButton("➕ Добавить артиста"))
    return kb

# ================== ХЕНДЛЕРЫ ==================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    admins = load_json(ADMINS_FILE, [])
    is_admin = message.from_user.id in admins

    await message.answer(
        "🎶 Добро пожаловать!\nВыбери действие:",
        reply_markup=main_menu(is_admin)
    )

# ---------- ПОКАЗ АРТИСТОВ ----------

@dp.message_handler(lambda m: m.text == "🎤 Артисты")
async def show_artists(message: types.Message):
    artists = load_json(ARTISTS_FILE, [])

    if not artists:
        await message.answer("Артистов пока нет 😢")
        return

    kb = InlineKeyboardMarkup()
    for a in artists:
        kb.add(
            InlineKeyboardButton(
                text=a["name"],
                url=a["link"].strip()
            )
        )

    await message.answer("🎤 Наши артисты:", reply_markup=kb)

# ---------- ДОБАВЛЕНИЕ АРТИСТА ----------

@dp.message_handler(lambda m: m.text == "➕ Добавить артиста")
async def add_artist_start(message: types.Message):
    admins = load_json(ADMINS_FILE, [])
    if message.from_user.id not in admins:
        return

    await message.answer("Введи имя артиста:")
    await AddArtist.name.set()

@dp.message_handler(state=AddArtist.name)
async def add_artist_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь ссылку на Telegram-канал (https://t.me/...):")
    await AddArtist.link.set()

@dp.message_handler(state=AddArtist.link)
async def add_artist_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    artists = load_json(ARTISTS_FILE, [])

    artists.append({
        "name": data["name"],
        "link": message.text.strip()
    })

    save_json(ARTISTS_FILE, artists)
    await state.finish()

    await message.answer("✅ Артист добавлен!")

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
