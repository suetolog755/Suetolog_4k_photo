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
user_consent = {}          # Согласие на обработку
user_ownership = {}        # Подтверждение прав на фото
temp_photos = {}           # Временные фото

# Пути для логов
CONSENT_LOG = "consent_log.txt"
OWNERSHIP_LOG = "ownership_log.txt"

# ==================== ЛОГИРОВАНИЕ ====================

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
        return chat_member.status in ["member", "administrator", "creator"]
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
        # Показываем главное меню /start
        await cmd_start(callback.message)
    else:
        await callback.answer("❌ Вы не подписаны на канал", show_alert=True)
    await callback.answer()

# ==================== СОГЛАСИЕ (ТОЛЬКО ПРИ /START) ====================

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    if not await ensure_subscribed(message):
        return
    
    # Если уже есть полное согласие
    if has_full_consent(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
        ])
        await message.answer(
            "✅ *У ВАС УЖЕ ЕСТЬ АКТИВНЫЕ СОГЛАСИЯ*\n\n"
            "📸 ОТПРАВЬТЕ ФОТО ДЛЯ ОБРАБОТКИ.\n\n"
            "⚠️ *ВАЖНО:* ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ\n"
            "➡️ КОМАНДОЙ /revoke ИЛИ КНОПКОЙ НИЖЕ\n\n"
            "❌ КНОПКА ОТЗЫВА ВСЕХ СОГЛАСИЙ:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        return
    
    # Шаг 1: Согласие на обработку
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ДАТЬ СОГЛАСИЕ", callback_data="give_consent")],
        [InlineKeyboardButton(text="❌ ОТКАЗАТЬСЯ", callback_data="decline_consent")]
    ])
    
    await message.answer(
        "🌟 *ЮРИДИЧЕСКИ ЗАЩИЩЁННЫЙ AI PHOTO ENHANCER*\n\n"
        "✨ *ЧТО Я ДЕЛАЮ:*\n"
        "• Улучшаю качество фото (шум, резкость, контраст)\n"
        "• Удаляю морщины (по вашему запросу, естественно)\n\n"
        "🙅 *ЧТО НЕ ДЕЛАЮ:*\n"
        "• НЕ меняю лицо\n"
        "• НЕ создаю фейковые фото\n"
        "• НЕ сохраняю ваши фото\n\n"
        "📋 *ДЛЯ РАБОТЫ НУЖНО ПРОЙТИ 2 ШАГА:*\n"
        "1️⃣ СОГЛАСИЕ НА ОБРАБОТКУ ФОТО\n"
        "2️⃣ ПОДТВЕРЖДЕНИЕ ПРАВ НА ЗАГРУЖАЕМЫЕ ФОТО\n\n"
        "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ*\n"
        "➡️ КОМАНДОЙ /revoke\n\n"
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
    
    # Шаг 2: Подтверждение прав на фото
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ ПОДТВЕРЖДАЮ", callback_data="confirm_ownership")],
        [InlineKeyboardButton(text="❌ НЕ ПОДТВЕРЖДАЮ", callback_data="decline_ownership")]
    ])
    
    await callback.message.edit_text(
        "✅ *СОГЛАСИЕ ПОДТВЕРЖДЕНО*\n\n"
        "📋 *ШАГ 2: ПОДТВЕРЖДЕНИЕ ПРАВ НА ФОТО*\n\n"
        "ПРЕЖДЕ ЧЕМ ПРОДОЛЖИТЬ, ЮРИДИЧЕСКИ ПОДТВЕРДИТЕ:\n\n"
        "✅ ВЫ ИМЕЕТЕ ПРАВО НА ОБРАБОТКУ ЗАГРУЖАЕМЫХ ФОТО\n"
        "✅ ВЫ НЕ НАРУШАЕТЕ ПРАВА ТРЕТЬИХ ЛИЦ\n"
        "✅ НА ОБРАБОТКУ ФОТО ЕСТЬ СОГЛАСИЕ ИЗОБРАЖЁННОГО ЛИЦА (ЕСЛИ ЭТО НЕ ВЫ)\n\n"
        "⚠️ *ЮРИДИЧЕСКАЯ ОТВЕТСТВЕННОСТЬ ЗА НАРУШЕНИЕ ПРАВ ТРЕТЬИХ ЛИЦ ЛЕЖИТ ПОЛНОСТЬЮ НА ВАС.*\n\n"
        "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ КОМАНДОЙ /revoke*\n\n"
        "ПОДТВЕРДИТЕ, ЧТОБЫ ПРОДОЛЖИТЬ:",
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
        "✨ *ЧТО БУДЕТ ДАЛЬШЕ:*\n"
        "1️⃣ Я УЛУЧШУ КАЧЕСТВО ФОТО\n"
        "2️⃣ ПОЯВИТСЯ КНОПКА «УБРАТЬ МОРЩИНЫ»\n"
        "3️⃣ ВЫ САМИ РЕШАЕТЕ, НУЖНА ЛИ РЕТУШЬ\n\n"
        "⚠️ *НАПОМИНАНИЕ:*\n"
        "• ВЫ НЕСЁТЕ ПОЛНУЮ ОТВЕТСТВЕННОСТЬ ЗА ЗАГРУЖАЕМЫЕ ФОТО\n"
        "• ФОТО НЕ СОХРАНЯЮТСЯ НА СЕРВЕРЕ\n"
        "• ВЫ МОЖЕТЕ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ В ЛЮБОЙ МОМЕНТ\n"
        "➡️ КНОПКОЙ НИЖЕ ИЛИ КОМАНДОЙ /revoke\n\n"
        "👇 *ОТПРАВЬТЕ ФОТО ДЛЯ ОБРАБОТКИ*",
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
        "БОТ НЕ МОЖЕТ ОБРАБАТЫВАТЬ ФОТО БЕЗ ВАШЕГО ЮРИДИЧЕСКОГО ПОДТВЕРЖДЕНИЯ.\n\n"
        "ЕСЛИ ВЫ ВЛАДЕЛЕЦ ФОТО ИЛИ ИМЕЕТЕ РАЗРЕШЕНИЕ, ОТПРАВЬТЕ /start ЗАНОВО.",
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
        "• СОГЛАСИЕ НА ОБРАБОТКУ ФОТО: ❌ ОТОЗВАНО\n"
        "• ПОДТВЕРЖДЕНИЕ ПРАВ НА ФОТО: ❌ ОТОЗВАНО\n\n"
        "ЧТОБЫ СНОВА ПОЛЬЗОВАТЬСЯ БОТОМ, ОТПРАВЬТЕ /start И ПРОЙДИТЕ ОБА ШАГА ЗАНОВО.\n\n"
        "⚠️ *НАПОМИНАНИЕ:* ВЫ ВСЕГДА МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ КОМАНДОЙ /revoke",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message_handler(commands=["revoke"])
async def cmd_revoke(message: types.Message):
    """Команда быстрого отзыва всех согласий"""
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
            "ЧТОБЫ СНОВА ПОЛЬЗОВАТЬСЯ БОТОМ, ОТПРАВЬТЕ /start.",
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

# ==================== ОБРАБОТКА ФОТО ====================

def enhance_photo_quality(image_bytes: bytes) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return image_bytes
    
    denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    kernel_sharpen = np.array([[-1,-1,-1], [-1, 9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
    
    lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced_lab = cv2.merge([l, a, b])
    enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    final = cv2.edgePreservingFilter(enhanced_bgr, flags=1, sigma_s=60, sigma_r=0.4)
    
    _, encoded = cv2.imencode('.jpg', final, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return encoded.tobytes()

def remove_wrinkles(image_bytes: bytes) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return image_bytes
    
    smoothed = cv2.bilateralFilter(img, d=15, sigmaColor=80, sigmaSpace=80)
    blended = cv2.addWeighted(smoothed, 0.7, img, 0.3, 0)
    kernel = np.ones((3,3), np.float32)/9
    final = cv2.filter2D(blended, -1, kernel)
    
    _, encoded = cv2.imencode('.jpg', final, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return encoded.tobytes()

# ==================== ОБРАБОТЧИК ФОТО ====================

@dp.message_handler(content_types=['photo'])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    
    if not await ensure_subscribed(message):
        return
    
    if not has_full_consent(user_id):
        await message.answer(
            "⚠️ *ТРЕБУЕТСЯ ВАШЕ СОГЛАСИЕ*\n\n"
            "ВЫ НЕ ПРОШЛИ ЮРИДИЧЕСКИЕ ШАГИ 1 И 2.\n\n"
            "ОТПРАВЬТЕ /start И ДАЙТЕ СОГЛАСИЕ.\n\n"
            "⚠️ *НАПОМИНАНИЕ:* ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ КОМАНДОЙ /revoke",
            parse_mode="Markdown"
        )
        return
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_data = await bot.download_file(file.file_path)
    
    status_msg = await message.answer(
        "🎨 *ОБРАБОТКА ФОТО...*\n\n"
        "✨ УЛУЧШЕНИЕ КАЧЕСТВА\n"
        "👤 ЛИЦО ОСТАЁТСЯ ПРЕЖНИМ\n"
        "⏳ 5-10 СЕКУНД",
        parse_mode="Markdown"
    )
    
    try:
        enhanced_bytes = enhance_photo_quality(image_data.read())
        temp_photos[user_id] = enhanced_bytes
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✨ УБРАТЬ МОРЩИНЫ", callback_data="remove_wrinkles")],
            [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
        ])
        
        await status_msg.delete()
        
        await message.answer_photo(
            photo=enhanced_bytes,
            caption="✨ *ФОТО УЛУЧШЕНО!*\n\n"
                    "✅ КАЧЕСТВО ПОВЫШЕНО\n"
                    "✅ ШУМ УБРАН\n"
                    "👤 ЛИЦО НЕ ИЗМЕНЕНО\n\n"
                    "⚠️ *ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ:* /revoke\n\n"
                    "👇 НАЖМИТЕ, ЕСЛИ ХОТИТЕ УБРАТЬ МОРЩИНЫ:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ ОШИБКА: {str(e)[:100]}\n\nПОПРОБУЙТЕ ДРУГОЕ ФОТО.", parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "remove_wrinkles")
async def handle_remove_wrinkles(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in temp_photos:
        await callback.answer("❌ ФОТО НЕ НАЙДЕНО. ОТПРАВЬТЕ ФОТО ЗАНОВО.", show_alert=True)
        return
    
    if not has_full_consent(user_id):
        await callback.answer("❌ СОГЛАСИЕ ОТОЗВАНО. ОТПРАВЬТЕ /start ЗАНОВО.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎨 *УДАЛЯЮ МОРЩИНЫ...*\n\n"
        "⏳ 5-10 СЕКУНД\n"
        "👤 ЛИЦО ОСТАЁТСЯ УЗНАВАЕМЫМ",
        parse_mode="Markdown"
    )
    
    try:
        original_enhanced = temp_photos[user_id]
        retouched_bytes = remove_wrinkles(original_enhanced)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ ОТОЗВАТЬ ВСЕ СОГЛАСИЯ", callback_data="revoke_all")]
        ])
        
        await callback.message.answer_photo(
            photo=retouched_bytes,
            caption="✨ *МОРЩИНЫ УДАЛЕНЫ!*\n\n"
                    "✅ РЕТУШЬ ВЫПОЛНЕНА\n"
                    "👤 ЛИЦО СОХРАНЕНО\n"
                    "💫 ЕСТЕСТВЕННЫЙ РЕЗУЛЬТАТ\n\n"
                    "⚠️ *НАПОМИНАНИЕ:* ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ КОМАНДОЙ /revoke",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        del temp_photos[user_id]
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ ОШИБКА ПРИ РЕТУШИ: {str(e)[:100]}\n\n"
            f"ПОПРОБУЙТЕ ЕЩЁ РАЗ ИЛИ ОТПРАВЬТЕ НОВОЕ ФОТО.",
            parse_mode="Markdown"
        )
    
    await callback.answer()

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 *ПОМОЩЬ И ЮРИДИЧЕСКАЯ ИНФОРМАЦИЯ*\n\n"
        "🔹 *КОМАНДЫ:*\n"
        "• /start — НАЧАТЬ РАБОТУ (ТОЛЬКО ЗДЕСЬ ДАЁТСЯ СОГЛАСИЕ)\n"
        "• /revoke — ОТОЗВАТЬ ВСЕ СОГЛАСИЯ (РАБОТАЕТ В ЛЮБОЙ МОМЕНТ)\n\n"
        "🔹 *ЧТО ДЕЛАЕТ БОТ:*\n"
        "1️⃣ УЛУЧШАЕТ КАЧЕСТВО ФОТО\n"
        "2️⃣ ПО ВАШЕМУ ЗАПРОСУ УДАЛЯЕТ МОРЩИНЫ\n\n"
        "🔹 *ЮРИДИЧЕСКИЕ ГАРАНТИИ:*\n"
        "• ВЫ ДАЁТЕ ЯВНОЕ СОГЛАСИЕ (2 ШАГА)\n"
        "• ВЫ ПОДТВЕРЖДАЕТЕ ПРАВА НА ФОТО\n"
        "• ВЫ НЕСЁТЕ ОТВЕТСТВЕННОСТЬ ЗА КАЖДОЕ ФОТО\n"
        "• БОТ НЕ ХРАНИТ ВАШИ ФОТО\n"
        "• ВЫ МОЖЕТЕ ОТОЗВАТЬ СОГЛАСИЕ В ЛЮБОЙ МОМЕНТ: /revoke\n\n"
        "❌ *ЖАЛОБА НА БОТА:* @BotFather",
        parse_mode="Markdown"
    )

@dp.message_handler()
async def handle_unknown(message: types.Message):
    await message.answer(
        "❓ *НЕИЗВЕСТНАЯ КОМАНДА*\n\n"
        "ОТПРАВЬТЕ /help ДЛЯ СПИСКА КОМАНД\n"
        "ИЛИ ПРОСТО ОТПРАВЬТЕ ФОТО ДЛЯ УЛУЧШЕНИЯ.\n\n"
        "⚠️ *НАПОМИНАНИЕ:* ОТОЗВАТЬ СОГЛАСИЕ МОЖНО В ЛЮБОЙ МОМЕНТ КОМАНДОЙ /revoke",
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    print("🚀 БОТ ЗАПУЩЕН")
    print("✅ СОГЛАСИЕ ТОЛЬКО ПРИ /start")
    print("⚠️ НАПОМИНАНИЕ ОБ ОТМЕНЕ: В ЛЮБОЙ МОМЕНТ /revoke")
    print("👤 ЛИЦО НЕ МЕНЯЕТСЯ")
    executor.start_polling(dp, skip_updates=True)
