import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ================== НАСТРОЙКИ ==================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

ARTISTS_FILE = "artists.json"
ADMINS_FILE = "admins.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


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
    return load_json(ARTISTS_FILE, {})

def save_artists(data):
    save_json(ARTISTS_FILE, data)

def load_admins():
    return load_json(ADMINS_FILE, [])

def save_admins(data):
    save_json(ADMINS_FILE, data)

def is_admin(user_id):
    return user_id in load_admins()

# ================== КЛАВИАТУРЫ ==================

def main_menu(admin=False):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("🎶 Артисты"))

    if admin:
        kb.add(
            KeyboardButton("➕ Добавить артиста"),
            KeyboardButton("🗑 Удалить артиста")
        )
        kb.add(
            KeyboardButton("👑 Админы")
        )
    return kb


def artist_keyboard():
    artists = load_artists()
    kb = InlineKeyboardMarkup(row_width=1)

    for name, link in artists.items():
        kb.add(
            InlineKeyboardButton(
                text=f"🎧 {name}",
                url=link.strip()
            )
        )
    return kb

# ================== START ==================

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "🎧 Добро пожаловать.\nВыбирай действие:",
        reply_markup=main_menu(is_admin(message.from_user.id))
    )

# ================== ПОЛЬЗОВАТЕЛИ ==================

@dp.message_handler(lambda m: m.text == "🎶 Артисты")
async def show_artists(message: types.Message):
    artists = load_artists()

    if not artists:
        await message.answer("Пока артистов нет 👀")
        return

    await message.answer(
        "Выбирай артиста:",
        reply_markup=artist_keyboard()
    )

# ================== АДМИНЫ ==================

@dp.message_handler(lambda m: m.text == "👑 Админы")
async def admins_list(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    admins = load_admins()
    text = "👑 Админы:\n\n" + "\n".join(map(str, admins))
    await message.answer(text)

# ================== КОМАНДЫ АДМИНОВ ==================

@dp.message_handler(commands=["add"])
async def add_artist(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        _, name, link = message.text.split(" ", 2)
        artists = load_artists()
        artists[name] = link.strip()
        save_artists(artists)
        await message.answer(f"✅ Артист {name} добавлен")
    except:
        await message.answer("Формат:\n/add Имя https://t.me/канал")


@dp.message_handler(commands=["remove"])
async def remove_artist(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        _, name = message.text.split(" ", 1)
        artists = load_artists()

        if name not in artists:
            await message.answer("❌ Артист не найден")
            return

        del artists[name]
        save_artists(artists)
        await message.answer(f"🗑 Артист {name} удалён")
    except:
        await message.answer("Формат:\n/remove Имя")


@dp.message_handler(commands=["list"])
async def list_artists(message: types.Message):
    artists = load_artists()

    if not artists:
        await message.answer("Артистов пока нет")
        return

    text = "🎶 Артисты:\n\n"
    for name, link in artists.items():
        text += f"{name} — {link}\n"

    await message.answer(text)


@dp.message_handler(commands=["addadmin"])
async def add_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        _, admin_id = message.text.split(" ", 1)
        admin_id = int(admin_id)

        admins = load_admins()
        if admin_id in admins:
            await message.answer("Он уже админ")
            return

        admins.append(admin_id)
        save_admins(admins)
        await message.answer(f"👑 Админ {admin_id} добавлен")
    except:
        await message.answer("Формат:\n/addadmin 123456789")


@dp.message_handler(commands=["removeadmin"])
async def remove_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    try:
        _, admin_id = message.text.split(" ", 1)
        admin_id = int(admin_id)

        admins = load_admins()
        if admin_id not in admins:
            await message.answer("Такого админа нет")
            return

        admins.remove(admin_id)
        save_admins(admins)
        await message.answer(f"❌ Админ {admin_id} удалён")
    except:
        await message.answer("Формат:\n/removeadmin 123456789")

# ================== ЗАПУСК ==================

if __name__ == "__main__":
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)



