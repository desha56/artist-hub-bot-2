# bot.py — финальная версия с улучшенной обработкой ссылок и прикреплёнными фото (file_id)
import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in env")

ARTISTS_FILE = "artists.json"
ADMINS_FILE = "admins.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ========== FSM ==========
class AddArtist(StatesGroup):
    name = State()
    bio = State()
    photo = State()
    telegram = State()
    yandex = State()
    vk = State()

class EditArtistField(StatesGroup):
    artist_name = State()
    field = State()
    value = State()

class AddAdmin(StatesGroup):
    user_id = State()

# ========== УТИЛИТЫ ==========
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

# ========== SANITIZE URL ==========
def sanitize_url(platform, raw: str):
    """
    Возвращает корректный URL или None.
    Поддерживает:
      - Полные ссылки http(s)://...
      - vk.ru и vk.com без протокола
      - music.yandex.ru
      - telegram: @username, t.me/username, plain username
    """
    if not raw:
        return None
    s = raw.strip()

    # If already full http(s) url - accept as is
    if s.startswith("http://") or s.startswith("https://"):
        return s

    # Allow vk short domains
    if s.startswith("vk.ru") or s.startswith("www.vk.ru") or s.startswith("vk.com") or s.startswith("www.vk.com"):
        return "https://" + s

    # Yandex music
    if s.startswith("music.yandex.ru") or s.startswith("www.music.yandex.ru") or "yandex" in s:
        return "https://" + s

    # Telegram special handling
    if platform == "telegram":
        if s.startswith("@"):
            return f"https://t.me/{s[1:]}"
        if s.startswith("t.me/") or "t.me/" in s:
            return ("https://" + s) if not s.startswith("http") else s
        if s.startswith("telegram.me/"):
            return ("https://" + s) if not s.startswith("http") else s
        # fallback: username only
        return "https://t.me/" + s.lstrip("@")

    # Generic fallback: add https
    return "https://" + s

# ========== КЛАВИАТУРЫ ==========
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
    # sanitize links
    for platform in ["telegram", "yandex_music", "vk_group"]:
        raw = artist.get("links", {}).get(platform, "") or ""
        url = sanitize_url(platform, raw)
        if url:
            kb.insert(InlineKeyboardButton(platform.replace("_"," ").capitalize(), url=url))
    if is_admin_flag:
        kb.insert(InlineKeyboardButton("❌ Удалить артиста", callback_data=f"del_artist:{artist['name']}"))
        kb.insert(InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_artist:{artist['name']}"))
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    return kb

# ========== ХЕНДЛЕРЫ ==========
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer("🎶 Главное меню:", reply_markup=main_menu_keyboard(message.from_user.id))

@dp.callback_query_handler(lambda c: c.data == "main_menu")
async def cb_main_menu(call: types.CallbackQuery):
    kb = main_menu_keyboard(call.from_user.id)
    try:
        await call.message.edit_text("🎶 Главное меню:", reply_markup=kb)
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("🎶 Главное меню:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "show_artists")
async def cb_show_artists(call: types.CallbackQuery):
    kb = artist_keyboard(call.from_user.id)
    try:
        await call.message.edit_text("🎤 Наши артисты:", reply_markup=kb)
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("🎤 Наши артисты:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("profile_artist:"))
async def cb_profile_artist(call: types.CallbackQuery):
    name = call.data.split(":", 1)[1]
    artists = load_artists()
    artist = next((x for x in artists if x["name"] == name), None)
    if not artist:
        await call.answer("Артист не найден", show_alert=True)
        return

    text = f"🎤 {artist['name']}\n\n{artist.get('bio','Нет описания')}"
    kb = profile_keyboard(artist, is_admin_flag=is_admin(call.from_user.id))
    photo = artist.get("photo")  # file_id or None

    if photo:
        try:
            media = InputMediaPhoto(media=photo, caption=text, parse_mode="Markdown")
            await call.message.edit_media(media=media, reply_markup=kb)
        except Exception:
            try:
                await call.message.delete()
            except Exception:
                pass
            await call.message.answer_photo(photo, caption=text, reply_markup=kb)
    else:
        try:
            await call.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            try:
                await call.message.delete()
            except Exception:
                pass
            await call.message.answer(text, reply_markup=kb, parse_mode="Markdown")

    await call.answer()

# ---------- ADD ARTIST (admin only) ----------
@dp.callback_query_handler(lambda c: c.data == "add_artist")
async def cb_add_artist_start(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.answer("Введите имя артиста:")
    await AddArtist.name.set()
    await call.answer()

@dp.message_handler(state=AddArtist.name)
async def st_add_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    artists = load_artists()
    if any(a["name"] == name for a in artists):
        await message.answer("Артист с таким именем уже есть. Введите другое имя:")
        return
    await state.update_data(name=name)
    await message.answer("Введите краткое описание (bio) артиста:")
    await AddArtist.bio.set()

@dp.message_handler(state=AddArtist.bio)
async def st_add_bio(message: types.Message, state: FSMContext):
    await state.update_data(bio=message.text.strip())
    await message.answer("Прикрепите фото артиста (отправьте как фото). Если фото нет — отправьте слово 'нет'.")
    await AddArtist.photo.set()

@dp.message_handler(content_types=types.ContentType.PHOTO, state=AddArtist.photo)
async def st_add_photo_file(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo=photo_file_id)
    await message.answer("Ссылка на Telegram (t.me/username или @username или ссылка):")
    await AddArtist.telegram.set()

@dp.message_handler(lambda m: m.text and m.text.strip().lower() == "нет", state=AddArtist.photo)
async def st_add_photo_none(message: types.Message, state: FSMContext):
    await state.update_data(photo=None)
    await message.answer("Ссылка на Telegram (t.me/username или @username или ссылка):")
    await AddArtist.telegram.set()

@dp.message_handler(state=AddArtist.photo, content_types=types.ContentType.ANY)
async def st_add_photo_invalid(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, отправьте фото (как фото) или слово 'нет' если фото нет.")

@dp.message_handler(state=AddArtist.telegram)
async def st_add_telegram(message: types.Message, state: FSMContext):
    await state.update_data(telegram=message.text.strip())
    await message.answer("Ссылка на Яндекс Музыку (или пусто):")
    await AddArtist.yandex.set()

@dp.message_handler(state=AddArtist.yandex)
async def st_add_yandex(message: types.Message, state: FSMContext):
    await state.update_data(yandex=message.text.strip())
    await message.answer("Ссылка на группу ВКонтакте (или пусто):")
    await AddArtist.vk.set()

@dp.message_handler(state=AddArtist.vk)
async def st_add_vk(message: types.Message, state: FSMContext):
    data = await state.get_data()
    artists = load_artists()
    links = {
        "telegram": data.get("telegram",""),
        "yandex_music": data.get("yandex",""),
        "vk_group": message.text.strip()
    }
    artist_obj = {
        "name": data.get("name"),
        "bio": data.get("bio",""),
        "photo": data.get("photo"),
        "links": links
    }
    artists.append(artist_obj)
    save_artists(artists)
    await state.finish()

    kb = profile_keyboard(artist_obj, is_admin_flag=True)
    text = f"🎤 {artist_obj['name']}\n\n{artist_obj.get('bio','Нет описания')}"
    if artist_obj.get("photo"):
        await message.answer_photo(artist_obj["photo"], caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

# ---------- EDIT ARTIST ----------
@dp.callback_query_handler(lambda c: c.data.startswith("edit_artist:"))
async def cb_edit_artist_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    artist_name = call.data.split(":",1)[1]
    await state.update_data(artist_name=artist_name)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✏️ Имя", callback_data="edit_field:name"),
        InlineKeyboardButton("✏️ Bio", callback_data="edit_field:bio"),
        InlineKeyboardButton("✏️ Фото", callback_data="edit_field:photo"),
        InlineKeyboardButton("✏️ Telegram", callback_data="edit_field:telegram"),
        InlineKeyboardButton("✏️ Яндекс Музыка", callback_data="edit_field:yandex_music"),
        InlineKeyboardButton("✏️ VK", callback_data="edit_field:vk_group"),
    )
    kb.add(InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    try:
        await call.message.edit_text("Выберите поле для редактирования:", reply_markup=kb)
    except Exception:
        try:
            await call.message.delete()
        except Exception:
            pass
        await call.message.answer("Выберите поле для редактирования:", reply_markup=kb)
    await EditArtistField.artist_name.set()
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("edit_field:"), state=EditArtistField.artist_name)
async def cb_edit_field_select(call: types.CallbackQuery, state: FSMContext):
    field = call.data.split(":",1)[1]
    await state.update_data(field=field)
    if field == "photo":
        await call.message.answer("Отправьте новое фото артиста (как фото):")
    else:
        await call.message.answer(f"Введите новое значение для {field}:")
    await EditArtistField.next()
    await call.answer()

@dp.message_handler(content_types=[types.ContentType.TEXT, types.ContentType.PHOTO], state=EditArtistField.value)
async def st_edit_field_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    artist_name = data.get("artist_name")
    field = data.get("field")
    artists = load_artists()
    artist = next((a for a in artists if a["name"] == artist_name), None)
    if not artist:
        await message.answer("Артист не найден")
        await state.finish()
        return

    if field == "photo":
        if not message.photo:
            await message.answer("Пожалуйста, отправьте фото (как фото).")
            return
        artist["photo"] = message.photo[-1].file_id
    elif field in ["telegram", "yandex_music", "vk_group"]:
        artist.setdefault("links", {})
        artist["links"][field] = message.text.strip()
    else:
        if field == "name":
            if any(a["name"] == message.text.strip() and a is not artist for a in artists):
                await message.answer("Уже есть артист с таким именем. Выберите другое имя.")
                return
        artist[field] = message.text.strip()

    save_artists(artists)
    await state.finish()

    kb = profile_keyboard(artist, is_admin_flag=True)
    text = f"🎤 {artist['name']}\n\n{artist.get('bio','Нет описания')}"
    if artist.get("photo"):
        await message.answer_photo(artist["photo"], caption=text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)

# ---------- DELETE ARTIST (confirm) ----------
@dp.callback_query_handler(lambda c: c.data.startswith("del_artist:"))
async def cb_del_artist(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    name = call.data.split(":",1)[1]
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Да", callback_data=f"confirm_del_artist:{name}:yes"))
    kb.add(InlineKeyboardButton("Отмена", callback_data=f"confirm_del_artist:{name}:no"))
    try:
        await call.message.edit_reply_markup(kb)
    except Exception:
        await call.message.answer("Подтвердите удаление:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("confirm_del_artist:"))
async def cb_confirm_del_artist(call: types.CallbackQuery):
    _, name, action = call.data.split(":",2)
    if action != "yes":
        try:
            await call.message.edit_text("🎤 Наши артисты:", reply_markup=artist_keyboard(call.from_user.id))
        except Exception:
            await call.message.answer("Операция отменена.", reply_markup=artist_keyboard(call.from_user.id))
        await call.answer("Отмена")
        return
    artists = load_artists()
    artists = [a for a in artists if a["name"] != name]
    save_artists(artists)
    try:
        await call.message.edit_text("🎤 Наши артисты:", reply_markup=artist_keyboard(call.from_user.id))
    except Exception:
        await call.message.answer("Артист удалён.", reply_markup=artist_keyboard(call.from_user.id))
    await call.answer(f"Артист {name} удалён")

# ---------- ADMINS ----------
@dp.callback_query_handler(lambda c: c.data == "show_admins")
async def cb_show_admins(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    kb = admins_keyboard(call.from_user.id)
    try:
        await call.message.edit_text("👑 Админы:", reply_markup=kb)
    except Exception:
        await call.message.answer("👑 Админы:", reply_markup=kb)
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "add_admin")
async def cb_add_admin_start(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    await call.message.answer("Введите Telegram ID нового админа (число):")
    await AddAdmin.user_id.set()
    await call.answer()

@dp.message_handler(state=AddAdmin.user_id)
async def st_add_admin(message: types.Message, state: FSMContext):
    try:
        new_admin = int(message.text.strip())
    except ValueError:
        await message.answer("ID должен быть числом. Попробуйте ещё раз.")
        return
    admins = load_admins()
    if new_admin in admins:
        await message.answer("Этот пользователь уже админ.")
    else:
        admins.append(new_admin)
        save_admins(admins)
        await message.answer(f"✅ Пользователь {new_admin} добавлен как админ.")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("del_admin:"))
async def cb_del_admin(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("Нет доступа", show_alert=True)
        return
    admin_id = int(call.data.split(":",1)[1])
    admins = load_admins()
    if admin_id in admins:
        admins.remove(admin_id)
        save_admins(admins)
        try:
            await call.message.edit_text("👑 Админы:", reply_markup=admins_keyboard(call.from_user.id))
        except Exception:
            await call.message.answer("Админ удалён", reply_markup=admins_keyboard(call.from_user.id))
        await call.answer(f"Админ {admin_id} удалён")
    else:
        await call.answer("Пользователь не найден среди админов", show_alert=True)

# NOOP
@dp.callback_query_handler(lambda c: c.data == "noop")
async def cb_noop(call: types.CallbackQuery):
    await call.answer()

# ========== RUN ==========
if __name__ == "__main__":
    # ensure files exist
    load_json(ARTISTS_FILE, [])
    load_json(ADMINS_FILE, [])
    print("Bot started")
    executor.start_polling(dp, skip_updates=True)
