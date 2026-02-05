import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

ARTISTS_FILE = "artists.json"
ADMINS_FILE = "admins.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ================== СОСТОЯНИЯ ==================

class AddArtist(StatesGroup):
    name = State()
    link = State()

class RemoveArtist(StatesGroup):
    name = State()

class AddAdmin(StatesGroup):
    user_id = State()

class RemoveAdmin(StatesGroup):
    user_id = State()

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

def load_artists():
    return load_json(ARTISTS_FILE, [])

def save_artists(data):
    save_json(ARTISTS_FILE, data)

def load_admins():
    return load_json(ADMINS_FILE, [])

def save_admins(data):
    save_json(ADMINS_FILE, data)

def is_admin(user_id):
    return user_id in load_admins()

# ================== КЛАВИАТУРЫ ==================

def main_menu(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎤 Артисты"))
    if is_admin(user_id):
        kb.add(KeyboardButton("➕ Добавить артиста"),
               KeyboardButton("🗑 Удалить артиста"))
        kb.add(KeyboardButton("👑 Админы"))
    return kb

def artist_keyboard():
    artists = load_artists()
    kb = InlineKeyboardMarkup(row_width=1)
    for a in artists:
        kb.add(InlineKeyboardButton(text=a["name"], url=a["link"]))
    return kb

# ================== ХЕНДЛЕРЫ ==================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🎶 Добро пожаловать! Выбирай действие:", 
                         reply_markup=main_menu(message.from_user.id))

# ---------- АРТИСТЫ ----------

@dp.message_handler(lambda m: m.text == "🎤 Артисты")
async def show_artists(message: types.Message):
    artists = load_artists()
    if not artists:
        await message.answer("Артистов пока нет 😢")
        return
    await message.answer("🎤 Наши артисты:", reply_markup=artist_keyboard())

# ---------- ДОБАВЛЕНИЕ АРТИСТА ----------

@dp.message_handler(lambda m: m.text == "➕ Добавить артиста")
async def add_artist_start(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите имя артиста:")
    await AddArtist.name.set()

@dp.message_handler(state=AddArtist.name)
async def add_artist_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь ссылку на Telegram-канал (https://t.me/...):")
    await AddArtist.link.set()

@dp.message_handler(state=AddArtist.link)
async def add_artist_link(message: types.Message, state: FSMContext):
    data = await state.get_data()
    artists = load_artists()
    artists.append({"name": data["name"], "link": message.text.strip()})
    save_artists(artists)
    await state.finish()
    await message.answer("✅ Артист добавлен!")

# ---------- УДАЛЕНИЕ АРТИСТА ----------

@dp.message_handler(lambda m: m.text == "🗑 Удалить артиста")
async def remove_artist_start(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Введите имя артиста для удаления:")
    await RemoveArtist.name.set()

@dp.message_handler(state=RemoveArtist.name)
async def remove_artist_name(message: types.Message, state: FSMContext):
    artists = load_artists()
    new_list = [a for a in artists if a["name"] != message.text.strip()]
    save_artists(new_list)
    await state.finish()
    await message.answer(f"🗑 Артист {message.text.strip()} удалён!")

# ---------- АДМИНЫ ----------

@dp.message_handler(lambda m: m.text == "👑 Админы")
async def show_admins(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    admins = load_admins()
    await message.answer("👑 Админы:\n" + "\n".join(map(str, admins)))

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
