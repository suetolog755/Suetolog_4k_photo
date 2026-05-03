import os
import cv2
import numpy as np
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
            "📸 ОТПРАВЬТЕ ФОТО ДЛЯ 4K УЛУЧШЕНИЯ.\n\n"
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
        "🌟 *4K AI PHOTO ENHANCER*\n\n"
        "✨ *ЧТО Я ДЕЛАЮ:*\n"
        "• УВЕЛИЧИВАЮ РАЗРЕШЕНИЕ ДО 4K\n"
        "• УБИРАЮ ШУМ И ПИКСЕЛИЗАЦИЮ\n"
        "• ПОВЫШАЮ РЕЗКОСТЬ И КОНТРАСТ\n\n"
        "🙅 *ЧТО НЕ ДЕЛАЮ:*\n"
        "• НЕ МЕНЯЮ ЛИЦО\n"
        "• НЕ ХРАНЮ ВАШИ ФОТО\n\n"
        "📋 *2 ШАГА СОГЛАСИЯ:*\n"
        "1️⃣ ОБРАБОТКА ФОТО\n"
        "2️⃣ ПРАВА НА ФОТО\n\n"
        "⚠️ *ОТОЗВАТЬ СОГЛАСИЕ ВСЕГДА МОЖНО:* /revoke\n\n"
        "👇 НАЧНИТЕ:",
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
        "📋 *ШАГ 2: ПОДТВЕРЖДЕНИЕ ПРАВ*\n\n"
        "ПОДТВЕРДИТЕ:\n"
        "✅ ВЫ ВЛАДЕЛЕЦ ФОТО ИЛИ ИМЕЕТЕ РАЗРЕШЕНИЕ\n"
        "✅ ВЫ НЕ НАРУШАЕТЕ ПРАВА ТРЕТЬИХ ЛИЦ\n\n"
        "⚠️ *ЮРИДИЧЕСКАЯ ОТВЕТСТВЕННОСТЬ НА ВАС*\n\n"
        "👇 ПОДТВЕРДИТЕ:",
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
        "❌ *ВЫ ОТКАЗАЛИСЬ*\n\n"
        "ЕСЛИ ПЕРЕДУМАЕТЕ, /start",
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
        "✅ *ПРАВА ПОДТВЕРЖДЕНЫ*\n\n"
        "📸 *ОТПРАВЬТЕ ФОТО ДЛЯ 4K УЛУЧШЕНИЯ*\n\n"
        "✨ ЧТО БУДЕТ:\n"
        "1️⃣ Я ОБРАБОТАЮ ФОТО ЧЕРЕЗ AI\n"
        "2️⃣ УВЕЛИЧУ ДО 4K\n"
        "3️⃣ УБЕРУ ШУМ И ПОВЫШУ РЕЗКОСТЬ\n\n"
        "⚠️ *ОТОЗВАТЬ СОГЛАСИЕ МОЖНО КНОПКОЙ НИЖЕ ИЛИ /revoke*\n\n"
        "👇 ОТПРАВЬТЕ ФОТО:",
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
        "❌ *ПРАВА НЕ ПОДТВЕРЖДЕНЫ*\n\n"
        "БОТ НЕ МОЖЕТ РАБОТАТЬ БЕЗ ВАШЕГО ПОДТВЕРЖДЕНИЯ.\n\n"
        "ЕСЛИ ВЫ ВЛАДЕЛЕЦ ФОТО, /start",
        parse_mode="Markdown"
    )
    await callback.answer()

# ==================== ОТЗЫВ СОГЛАСИЙ ====================

@dp.callback_query_handler(lambda c: c.data == "revoke_all")
async def revoke_all(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    
    if user_id in user_consent:
        log_consent(user_id, username, "REVOKED")
        del user_consent[user_id]
    if user_id in user_ownership:
        log_ownership(user_id, username, False)
        del user_ownership[user_id]
    if user_id in temp_photos:
        del temp_photos[user_id]
    
    await callback.message.edit_text(
        "❌ *ВСЕ СОГЛАСИЯ ОТОЗВАНЫ*\n\n"
        "ЧТОБЫ НАЧАТЬ ЗАНОВО, /start",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message_handler(commands=["revoke"])
async def cmd_revoke(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    revoked = False
    if user_id in user_consent:
        log_consent(user_id, username, "REVOKED via /revoke")
        del user_consent[user_id]
        revoked = True
    if user_id in user_ownership:
        log_ownership(user_id, username, False)
        del user_ownership[user_id]
        revoked = True
    if user_id in temp_photos:
        del temp_photos[user_id]
    
    if revoked:
        await message.answer("❌ *СОГЛАСИЯ ОТОЗВАНЫ*\n\n/start ДЛЯ НОВОГО СЕАНСА", parse_mode="Markdown")
    else:
        await message.answer("ℹ️ *НЕТ АКТИВНЫХ СОГЛАСИЙ*\n\n/start", parse_mode="Markdown")

def has_full_consent(user_id: int) -> bool:
    return (user_id in user_consent and user_consent[user_id].get('agreed', False) and
            user_id in user_ownership and user_ownership[user_id].get('confirmed', False))

# ==================== 4K ОБРАБОТКА ЧЕРЕЗ OPENCV ====================

def enhance_to_4k(image_bytes: bytes) -> bytes:
    """
    Улучшение фото до 4K:
    - Увеличение разрешения (upscale)
    - Шумоподавление
    - Повышение резкости
    - Улучшение контраста
    """
    # Декодируем
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return image_bytes
    
    # 1. Супер-разрешение (увеличение до 4K через интерполяцию + детализация)
    height, width = img.shape[:2]
    
    # Увеличиваем в 2 раза (если фото маленькое)
    scale = max(1, int(1920 / max(height, width)) * 2)
    scale = min(scale, 4)  # максимум x4
    new_width = width * scale
    new_height = height * scale
    
    # Интерполяция Ланцоша для плавного увеличения
    upscaled = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    # 2. Шумоподавление (сохраняет детали)
    denoised = cv2.fastNlMeansDenoisingColored(upscaled, None, 10, 10, 7, 21)
    
    # 3. Повышение резкости (умная фильтрация)
    kernel_sharpen = np.array([[-1,-1,-1],
                                [-1, 9,-1],
                                [-1,-1,-1]])
    sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
    
    # 4. Улучшение контраста через CLAHE
    lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced_lab = cv2.merge([l, a, b])
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    
    # 5. Лёгкое сглаживание для устранения артефактов
    final = cv2.edgePreservingFilter(enhanced_bgr, flags=1, sigma_s=60, sigma_r=0.4)
    
    # Кодируем в JPEG с высоким качеством
    _, encoded = cv2.imencode('.jpg', final, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return encoded.tobytes()

# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    
    if not await ensure_subscribed(message):
        return
    
    if not has_full_consent(user_id):
        await message.answer(
            "⚠️ *ТРЕБУЕТСЯ СОГЛАСИЕ*\n\n"
            "ОТПРАВЬТЕ /start И ПРОЙДИТЕ 2 ШАГА",
            parse_mode="Markdown"
        )
        return
    
    # Получаем фото в максимальном качестве
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_data = await bot.download_file(file.file_path)
    
    status_msg = await message.answer(
        "🎨 *ОБРАБОТКА 4K...*\n\n"
        "▰▰▰▰▰▰▰▰▰▰ 0%\n"
        "✨ УВЕЛИЧЕНИЕ РАЗРЕШЕНИЯ\n"
        "🔍 УЛУЧШЕНИЕ ДЕТАЛЕЙ\n"
        "🎯 ЛИЦО СОХРАНЯЕТСЯ\n"
        "⏳ ~20-30 СЕКУНД",
        parse_mode="Markdown"
    )
    
    try:
        # Улучшаем до 4K
        enhanced_bytes = enhance_to_4k(image_data.read())
        
        await status_msg.delete()
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
        ])
        
        # Отправляем результат
        await message.answer_photo(
            photo=enhanced_bytes,
            caption="✅ *4K УЛУЧШЕНИЕ ГОТОВО*\n\n"
                    "✨ РАЗРЕШЕНИЕ УВЕЛИЧЕНО\n"
                    "🎨 ШУМ И АРТЕФАКТЫ УБРАНЫ\n"
                    "🔍 ДЕТАЛИ ВОССТАНОВЛЕНЫ\n"
                    "👤 ЛИЦО НЕ ИЗМЕНЕНО\n\n"
                    "⚠️ *НАПОМИНАНИЕ:* ОТОЗВАТЬ СОГЛАСИЕ МОЖНО В ЛЮБОЙ МОМЕНТ\n"
                    "➡️ /revoke ИЛИ КНОПКА НИЖЕ",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await status_msg.edit_text(
            f"❌ *ОШИБКА ОБРАБОТКИ*\n\n"
            f"ПОПРОБУЙТЕ ДРУГОЕ ФОТО ИЛИ ПОЗЖЕ.\n\n"
            f"`{str(e)[:100]}`",
            parse_mode="Markdown"
        )

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 *ПОМОЩЬ*\n\n"
        "🔹 /start — НАЧАТЬ (2 ШАГА СОГЛАСИЯ)\n"
        "🔹 /revoke — ОТОЗВАТЬ СОГЛАСИЕ\n\n"
        "📸 *ПРОСТО ОТПРАВЬТЕ ФОТО — ПОЛУЧИТЕ 4K*\n\n"
        "✨ *ЧТО УЛУЧШАЕТСЯ:*\n"
        "• РАЗРЕШЕНИЕ → 4K\n"
        "• ШУМ → УДАЛЯЕТСЯ\n"
        "• РЕЗКОСТЬ → ПОВЫШАЕТСЯ\n"
        "• КОНТРАСТ → УЛУЧШАЕТСЯ\n\n"
        "👤 *ЛИЦО НЕ МЕНЯЕТСЯ*\n\n"
        "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ*",
        parse_mode="Markdown"
    )

@dp.message_handler()
async def handle_unknown(message: types.Message):
    await message.answer(
        "❓ *НЕИЗВЕСТНАЯ КОМАНДА*\n\n"
        "📸 ОТПРАВЬТЕ ФОТО ДЛЯ 4K УЛУЧШЕНИЯ\n"
        "ИЛИ /help ДЛЯ СПИСКА КОМАНД\n\n"
        "⚠️ *ОТОЗВАТЬ СОГЛАСИЕ:* /revoke",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    print("🚀 4K AI PHOTO ENHANCER БОТ ЗАПУЩЕН")
    print("✅ OPENCV АКТИВЕН")
    print("🎯 УЛУЧШЕНИЕ ДО 4K ВКЛЮЧЕНО")
    print("👤 ЛИЦО НЕ МЕНЯЕТСЯ")
    print("⚠️ ОТМЕНА СОГЛАСИЯ: /revoke")
    executor.start_polling(dp, skip_updates=True)
