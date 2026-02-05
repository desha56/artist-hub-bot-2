import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

ARTISTS_FILE = "artists.json"
ADMINS_FILE = "admins.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ================== FSM ==================
class AddArtist(StatesGroup):
    name = State()
    bio = State()
    photo = State()
    telegram = State()
    yandex = State()
    vk = State()

class AddAdmin(StatesGroup):
    user_id = State()

class EditArtist(StatesGroup):
    field = State()
    value = State()
    artist_name = State()

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
def main_menu_keyboard(user_id):
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🎤 Артисты", callback_data="show_artists"))
    if is_admin(user_id):
        kb.add(InlineKeyboardButton("➕ Добавить артиста", callback_data="add_artist"))
        kb.add(InlineKeyboardButton("👑 Админы", callback_data="show_admins"))
        kb.add(InlineKeyboardButton("➕ Добавить админа", callback_data="add_admin"))
    return kb

def artist_keyboard(user_id):
    artists = load_artists()
    kb = InlineKeyboardMarkup(row_width=2)
    for a in artists:
        kb.insert(InlineKeyboardButton(a["name"], callback_data=f"profile_artist:{a['name']}"))
        if is_admin(user_id):
            kb.insert(InlineKeyboardButton("❌", callback_data=f"del_artist:{a['name']}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb

def admins_keyboard(user_id):
    admins = load_admins()
    kb = InlineKeyboardMarkup(row_width=2)
    for a in admins:
        kb.insert(InlineKeyboardButton(str(a), callback_data="noop"))
        if is_admin(user_id):
            kb.insert(InlineKeyboardButton("❌", callback_data=f"del_admin:{a}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb

def profile_keyboard(artist, is_admin_flag=False):
    kb = InlineKeyboardMarkup(row_width=2)
    for platform in ["telegram","yandex_music","vk_group"]:
        link = artist.get("links",{}).get(platform)
        if link:
            kb.insert(InlineKeyboardButton(platform.replace("_"," ").capitalize(), url=link))
    if is_admin_flag:
        kb.insert(InlineKeyboardButton("❌ Удалить артиста", callback_data=f"del_artist:{artist['name']}"))
        kb.insert(InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_artist:{artist['name']}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb

# ================== ХЕНДЛЕРЫ ==================
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("🎶 Главное меню:", reply_markup=main_menu_keyboard(message.from_user.id))

@dp.callback_query_handler(lambda c: c.data=="main_menu")
async def go_main_menu(call: types.CallbackQuery):
    kb = main_menu_keyboard(call.from_user.id)
    await call.message.edit_text("🎶 Главное меню:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data=="show_artists")
async def show_artists(call: types.CallbackQuery):
    kb = artist_keyboard(call.from_user.id)
    await call.message.edit_text("🎤 Наши артисты:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("profile_artist:"))
async def show_artist_profile(call: types.CallbackQuery):
    name = call.data.split(":",1)[1]
    artists = load_artists()
    artist = next((a for a in artists if a["name"]==name), None)
    if not artist:
        await call.answer("Артист не найден", show_alert=True)
        return

    text = f"🎤 {artist['name']}\n\n{artist.get('bio','Нет описания')}"
    kb = profile_keyboard(artist, is_admin_flag=is_admin(call.from_user.id))
    photo = artist.get("photo")

    if photo:
        try:
            media = InputMediaPhoto(media=photo, caption=text, parse_mode="Markdown")
            await call.message.edit_media(media=media, reply_markup=kb)
        except:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await call.answer()

# ---------- ДОБАВЛЕНИЕ АРТИСТА ----------
@dp.callback_query_handler(lambda c: c.data=="add_artist")
async def add_artist_start(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.answer("Введите имя артиста:")
    await AddArtist.name.set()
    await call.answer()

@dp.message_handler(state=AddArtist.name)
async def add_artist_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Введите краткое описание (bio) артиста:")
    await AddArtist.bio.set()

@dp.message_handler(state=AddArtist.bio)
async def add_artist_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text.strip())
    await message.answer("Прикрепите фото артиста (отправьте как фото):")
    await AddArtist.photo.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddArtist.photo)
async def add_artist_photo(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo=photo_file_id)
    await message.answer("Ссылка на Telegram:")
    await AddArtist.telegram.set()

@dp.message_handler(state=AddArtist.telegram)
async def add_artist_telegram(message: types.Message, state: FSMContext):
    await state.update_data(telegram=message.text.strip())
    await message.answer("Ссылка на Яндекс Музыку (или пусто):")
    await AddArtist.yandex.set()

@dp.message_handler(state=AddArtist.yandex)
async def add_artist_yandex(message: types.Message, state: FSMContext):
    await state.update_data(yandex=message.text.strip())
    await message.answer("Ссылка на группу ВКонтакте (или пусто):")
    await AddArtist.vk.set()

@dp.message_handler(state=AddArtist.vk)
async def add_artist_final(message: types.Message, state: FSMContext):
    data = await state.get_data()
    artists = load_artists()
    links = {
        "telegram": data["telegram"],
        "yandex_music": data["yandex"],
        "vk_group": data["vk"]
    }
    artists.append({
        "name": data["name"],
        "bio": data["bio"],
        "photo": data["photo"],
        "links": links
    })
    save_artists(artists)
    await state.finish()

    kb = profile_keyboard(artists[-1], is_admin_flag=True)
    photo = data["photo"]
    text = f"🎤 {data['name']}\n\n{data['bio']}"
    await message.answer_photo(photo, caption=text, reply_markup=kb)

# ---------- РЕДАКТИРОВАНИЕ / УДАЛЕНИЕ АРТИСТОВ и АДМИНОВ ----------
# Используются те же хендлеры как в предыдущей версии, только для фото теперь file_id

# ---------- NOOP ----------
@dp.callback_query_handler(lambda c: c.data=="noop")
async def noop(call: types.CallbackQuery):
    await call.answer()

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
