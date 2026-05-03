import os
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "@brmodels095"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Хранилища
user_consent = {}
user_ownership = {}
temp_photos = {}

# Логи
CONSENT_LOG = "consent_log.txt"
OWNERSHIP_LOG = "ownership_log.txt"

def log_consent(user_id: int, username: str, action: str):
    with open(CONSENT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | User {user_id} (@{username}) | {action}\n")

def log_ownership(user_id: int, username: str, confirmed: bool):
    status = "CONFIRMED" if confirmed else "DECLINED"
    with open(OWNERSHIP_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | User {user_id} (@{username}) | OWNERSHIP {status}\n")

# ==================== ПРОВЕРКА ПОДПИСКИ ====================

async def is_subscribed(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return chat_member.status in ["member", "administrator", "creator", "restricted"]
    except Exception:
        return False

async def ensure_subscribed(message: types.Message) -> bool:
    user_id = message.from_user.id
    subscribed = await is_subscribed(user_id)
    
    if not subscribed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 ПОДПИСАТЬСЯ", url="https://t.me/brmodels095")],
            [InlineKeyboardButton(text="✅ ПРОВЕРИТЬ", callback_data="check_subscribe")]
        ])
        await message.answer(
            "🔒 *ДОСТУП ПО ПОДПИСКЕ*\n\n"
            "Подпишитесь на канал:\n➡️ [@brmodels095](https://t.me/brmodels095)\n\n"
            "После подписки нажмите «ПРОВЕРИТЬ»",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return False
    return True

@dp.callback_query_handler(lambda c: c.data == "check_subscribe")
async def check_subscribe_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    subscribed = await is_subscribed(user_id)
    
    if subscribed:
        await callback.message.delete()
        await cmd_start(callback.message)
    else:
        await callback.answer("❌ Вы не подписаны на канал", show_alert=True)
    await callback.answer()

# ==================== СОГЛАСИЕ ====================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if not await ensure_subscribed(message):
        return
    
    if has_full_consent(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
        ])
        await message.answer(
            "✅ *У ВАС УЖЕ ЕСТЬ АКТИВНЫЕ СОГЛАСИЯ*\n\n"
            "📸 ОТПРАВЬТЕ ФОТО ДЛЯ ОБРАБОТКИ.\n\n"
            "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ:* /revoke",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ДАТЬ СОГЛАСИЕ", callback_data="give_consent")],
        [InlineKeyboardButton(text="❌ ОТКАЗАТЬСЯ", callback_data="decline_consent")]
    ])
    
    await message.answer(
        "🌟 *ЮРИДИЧЕСКИ ЗАЩИЩЁННЫЙ PHOTO ENHANCER*\n\n"
        "📋 *ДЛЯ РАБОТЫ НУЖНО ПРОЙТИ 2 ШАГА:*\n"
        "1️⃣ СОГЛАСИЕ НА ОБРАБОТКУ ФОТО\n"
        "2️⃣ ПОДТВЕРЖДЕНИЕ ПРАВ НА ЗАГРУЖАЕМЫЕ ФОТО\n\n"
        "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ:* /revoke\n\n"
        "👇 НАЧНИТЕ С ШАГА 1:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "give_consent")
async def give_consent(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    user_consent[user_id] = {
        'agreed': True,
        'agreed_at': datetime.now().isoformat(),
        'username': username
    }
    
    log_consent(user_id, username, "AGREED to photo processing")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПОДТВЕРЖДАЮ", callback_data="confirm_ownership")],
        [InlineKeyboardButton(text="❌ НЕ ПОДТВЕРЖДАЮ", callback_data="decline_ownership")]
    ])
    
    await callback.message.edit_text(
        "✅ *СОГЛАСИЕ ПОДТВЕРЖДЕНО*\n\n"
        "📋 *ШАГ 2: ПОДТВЕРЖДЕНИЕ ПРАВ НА ФОТО*\n\n"
        "ПОДТВЕРДИТЕ, ЧТО ВЫ ИМЕЕТЕ ПРАВО НА ЗАГРУЖАЕМЫЕ ФОТО:\n\n"
        "✅ ВЫ ВЛАДЕЛЕЦ ФОТО ИЛИ ИМЕЕТЕ РАЗРЕШЕНИЕ\n"
        "✅ ВЫ НЕ НАРУШАЕТЕ ПРАВА ТРЕТЬИХ ЛИЦ\n\n"
        "⚠️ *ОТВЕТСТВЕННОСТЬ ЗА НАРУШЕНИЕ ЛЕЖИТ НА ВАС*\n\n"
        "👇 ПОДТВЕРДИТЕ, ЧТОБЫ ПРОДОЛЖИТЬ:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "decline_consent")
async def decline_consent(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    log_consent(user_id, username, "DECLINED consent")
    
    await callback.message.edit_text(
        "❌ *ВЫ ОТКАЗАЛИСЬ ОТ ОБРАБОТКИ*\n\n"
        "ЕСЛИ ПЕРЕДУМАЕТЕ, ОТПРАВЬТЕ /start ЗАНОВО.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "confirm_ownership")
async def confirm_ownership(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    user_ownership[user_id] = {
        'confirmed': True,
        'confirmed_at': datetime.now().isoformat(),
        'username': username
    }
    
    log_ownership(user_id, username, True)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
    ])
    
    await callback.message.edit_text(
        "✅ *ПРАВА НА ФОТО ПОДТВЕРЖДЕНЫ*\n\n"
        "📸 *ТЕПЕРЬ ВЫ МОЖЕТЕ ОТПРАВЛЯТЬ ФОТО*\n\n"
        "✨ ПРОСТО ОТПРАВЬТЕ ФОТО — Я ЕГО ПРИМУ\n\n"
        "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ:* /revoke\n\n"
        "👇 ОТПРАВЬТЕ ФОТО",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query_handler(lambda c: c.data == "decline_ownership")
async def decline_ownership(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    log_ownership(user_id, username, False)
    
    await callback.message.edit_text(
        "❌ *ВЫ НЕ ПОДТВЕРДИЛИ ПРАВА НА ФОТО*\n\n"
        "БОТ НЕ МОЖЕТ ОБРАБАТЫВАТЬ ФОТО БЕЗ ПОДТВЕРЖДЕНИЯ.\n\n"
        "ЕСЛИ ВЫ ВЛАДЕЛЕЦ ФОТО, ОТПРАВЬТЕ /start ЗАНОВО.",
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== ОТЗЫВ СОГЛАСИЙ ====================

@dp.callback_query_handler(lambda c: c.data == "revoke_all")
async def revoke_all(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    if user_id in user_consent:
        log_consent(user_id, username, "REVOKED consent")
        del user_consent[user_id]
    
    if user_id in user_ownership:
        log_ownership(user_id, username, False)
        del user_ownership[user_id]
    
    if user_id in temp_photos:
        del temp_photos[user_id]
    
    await callback.message.edit_text(
        "❌ *ВСЕ СОГЛАСИЯ ОТОЗВАНЫ*\n\n"
        "ЧТОБЫ СНОВА ПОЛЬЗОВАТЬСЯ БОТОМ, ОТПРАВЬТЕ /start.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message_handler(commands=["revoke"])
async def cmd_revoke(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    revoked_anything = False
    
    if user_id in user_consent:
        log_consent(user_id, username, "REVOKED via /revoke")
        del user_consent[user_id]
        revoked_anything = True
    
    if user_id in user_ownership:
        log_ownership(user_id, username, False)
        del user_ownership[user_id]
        revoked_anything = True
    
    if user_id in temp_photos:
        del temp_photos[user_id]
    
    if revoked_anything:
        await message.answer(
            "❌ *ВСЕ СОГЛАСИЯ ОТОЗВАНЫ*\n\n"
            "ОТПРАВЬТЕ /start, ЧТОБЫ НАЧАТЬ ЗАНОВО.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "ℹ️ *У ВАС НЕТ АКТИВНЫХ СОГЛАСИЙ*\n\n"
            "ОТПРАВЬТЕ /start, ЧТОБЫ НАЧАТЬ.",
            parse_mode="Markdown"
        )

def has_full_consent(user_id: int) -> bool:
    return (user_id in user_consent and user_consent[user_id].get('agreed', False) and
            user_id in user_ownership and user_ownership[user_id].get('confirmed', False))

# ==================== ОБРАБОТКА ФОТО (БЕЗ CV2) ====================

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    
    if not await ensure_subscribed(message):
        return
    
    if not has_full_consent(user_id):
        await message.answer(
            "⚠️ *ТРЕБУЕТСЯ ВАШЕ СОГЛАСИЕ*\n\n"
            "ОТПРАВЬТЕ /start И ДАЙТЕ СОГЛАСИЕ.\n\n"
            "⚠️ *ОТОЗВАТЬ СОГЛАСИЕ МОЖНО В ЛЮБОЙ МОМЕНТ:* /revoke",
            parse_mode="Markdown"
        )
        return
    
    # Получаем фото
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_data = await bot.download_file(file.file_path)
    
    status_msg = await message.answer(
        "📸 *ПОЛУЧАЮ ФОТО...*\n\n"
        "⏳ ПОДОЖДИТЕ НЕСКОЛЬКО СЕКУНД",
        parse_mode="Markdown"
    )
    
    try:
        await status_msg.delete()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
        ])
        
        await message.answer_photo(
            photo=image_data.read(),
            caption="✅ *ФОТО ПРИНЯТО*\n\n"
                    "⚠️ *НАПОМИНАНИЕ:* ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ\n"
                    "➡️ КОМАНДОЙ /revoke ИЛИ КНОПКОЙ НИЖЕ",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ ОШИБКА: {str(e)[:100]}", parse_mode="Markdown")

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 *ПОМОЩЬ*\n\n"
        "🔹 *КОМАНДЫ:*\n"
        "• /start — НАЧАТЬ РАБОТУ\n"
        "• /revoke — ОТОЗВАТЬ ВСЕ СОГЛАСИЯ\n\n"
        "🔹 *ЧТО ДЕЛАЕТ БОТ:*\n"
        "• ПРИНИМАЕТ ВАШИ ФОТО\n"
        "• СОБИРАЕТ ЮРИДИЧЕСКИЕ СОГЛАСИЯ\n"
        "• ВЕДЁТ ЛОГИ ДЕЙСТВИЙ\n\n"
        "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ:* /revoke",
        parse_mode="Markdown"
    )

@dp.message_handler()
async def handle_unknown(message: types.Message):
    await message.answer(
        "❓ *НЕИЗВЕСТНАЯ КОМАНДА*\n\n"
        "ОТПРАВЬТЕ /help ДЛЯ СПИСКА КОМАНД\n"
        "ИЛИ ПРОСТО ОТПРАВЬТЕ ФОТО.\n\n"
        "⚠️ *ОТОЗВАТЬ СОГЛАСИЕ МОЖНО В ЛЮБОЙ МОМЕНТ:* /revoke",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    print("🚀 БОТ ЗАПУЩЕН")
    print("✅ БЕЗ OPENCV — ТОЛЬКО ПРИЁМ ФОТО")
    print("⚠️ ОТОЗВАТЬ СОГЛАСИЕ: /revoke")
    executor.start_polling(dp, skip_updates=True)
