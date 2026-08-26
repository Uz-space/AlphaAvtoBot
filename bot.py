import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Matnlar (har bir tilda) ---
TEXTS = {
    "uz_latin": {
        "choose_lang": "🌐 Tilni tanlang / Тилни танланг:",
        "ask_phone": "Xush kelibsiz! Botdan foydalanishni boshlash uchun telefon raqamingizni yuboring:",
        "phone_btn": "📱 Telefon raqamni yuborish",
        "phone_received": "✅ Telefon raqamingiz qabul qilindi!",
    },
    "uz_cyrillic": {
        "choose_lang": "🌐 Tilni tanlang / Тилни танланг:",
        "ask_phone": "Хуш келибсиз! Ботдан фойдаланишни бошлаш учун телефон рақамингизни юборинг:",
        "phone_btn": "📱 Телефон рақамни юбориш",
        "phone_received": "✅ Телефон рақамингиз қабул қилинди!",
    },
}

# --- Til tanlash klaviaturasi (inline) ---
def language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 Oʻzbekcha", callback_data="lang_uz_latin"),
            InlineKeyboardButton("🇺🇿 Кириллча", callback_data="lang_uz_cyrillic"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Telefon so'rash klaviaturasi (reply) ---
def phone_keyboard(lang: str) -> ReplyKeyboardMarkup:
    btn_text = TEXTS[lang]["phone_btn"]
    keyboard = [[KeyboardButton(btn_text, request_contact=True)]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# --- /start komandasi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = "🌐 Tilni tanlang / Тилни танланг:"
    await update.message.reply_text(text, reply_markup=language_keyboard())

# --- Til tanlash callback ---
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    lang_map = {
        "lang_uz_latin": "uz_latin",
        "lang_uz_cyrillic": "uz_cyrillic",
    }

    selected = lang_map.get(query.data)
    if not selected:
        return

    # Tilni saqlash
    context.user_data["lang"] = selected

    # Inline xabarni o'chirish
    await query.edit_message_text(TEXTS[selected]["ask_phone"])

    # Telefon tugmasi yuborish
    await query.message.reply_text(
        TEXTS[selected]["ask_phone"],
        reply_markup=phone_keyboard(selected),
    )

# --- Telefon raqam qabul qilish ---
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    phone = update.message.contact.phone_number

    # Raqamni saqlash
    context.user_data["phone"] = phone

    await update.message.reply_text(
        TEXTS[lang]["phone_received"],
        reply_markup=ReplyKeyboardRemove(),
    )

    # Keyingi qadamlar shu yerdan davom etadi...

# --- Asosiy funksiya ---
def main() -> None:
    TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"  # <-- shu yerga o'z tokeningizni kiriting

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
