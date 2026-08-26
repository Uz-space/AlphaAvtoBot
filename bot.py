import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
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
        "welcome": "✅ Til tanlandi!\n\nSalom! Botga xush kelibsiz! 👋",
        "choose_lang": "🌐 Tilni tanlang / Тилни танланг:",
    },
    "uz_cyrillic": {
        "welcome": "✅ Тил танланди!\n\nСалом! Ботга хуш келибсиз! 👋",
        "choose_lang": "🌐 Tilni tanlang / Тилни танланг:",
    },
}

# --- Til tanlash klaviaturasi ---
def language_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("o'zbekcha", callback_data="lang_uz_latin"),
            InlineKeyboardButton("кирилча", callback_data="lang_uz_cyrillic"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

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

    # Foydalanuvchi tilini saqlash (context.user_data ichida)
    context.user_data["lang"] = selected

    welcome_text = TEXTS[selected]["welcome"]
    await query.edit_message_text(welcome_text)

    # Keyingi qadamlar shu yerdan davom etadi...
    # Masalan: await show_main_menu(query, context)

# --- Asosiy funksiya ---
def main() -> None:
    TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"  # <-- shu yerga o'z tokeningizni kiriting

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
