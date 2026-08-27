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
        "phone_received": "Raqamingiz qabul qilindi. Iltimos, ism va familiyangizni kiriting:",
        "name_received": "✅ Rahmat! Quyidagi menyudan foydalaning:",
        "menu": {
            "exchange": "💱 Valyuta ayirboshlash",
            "rate": "📊 Kurs",
            "settings": "⚙️ Sozlamalar",
            "support": "🆘 Qo'llab-quvvatlash",
        },
    },
    "uz_cyrillic": {
        "choose_lang": "🌐 Tilni tanlang / Тилни танланг:",
        "ask_phone": "Хуш келибсиз! Ботдан фойдаланишни бошлаш учун телефон рақамингизни юборинг:",
        "phone_btn": "📱 Телефон рақамни юбориш",
        "phone_received": "Рақамингиз қабул қилинди. Илтимос, исм ва фамилиянгизни киритинг:",
        "name_received": "✅ Раҳмат! Қуйидаги менюдан фойдаланинг:",
        "menu": {
            "exchange": "💱 Валюта айирбошлаш",
            "rate": "📊 Курс",
            "settings": "⚙️ Созламалар",
            "support": "🆘 Қўллаб-қувватлаш",
        },
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

# --- Asosiy menyu klaviaturasi (reply) ---
def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    m = TEXTS[lang]["menu"]
    keyboard = [
        [KeyboardButton(m["exchange"]), KeyboardButton(m["rate"])],
        [KeyboardButton(m["settings"]), KeyboardButton(m["support"])],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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

    # Inline xabarni o'chirish (tugmalarsiz qoldiramiz)
    await query.edit_message_reply_markup(reply_markup=None)

    # Telefon so'rash
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

    # Ism-familiya kutilayotganini belgilash
    context.user_data["awaiting_name"] = True

    await update.message.reply_text(
        TEXTS[lang]["phone_received"],
        reply_markup=ReplyKeyboardRemove(),
    )

# --- Matnli xabarlarni yo'naltirish (ism yoki menyu) ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("awaiting_name"):
        await name_handler(update, context)
    else:
        await menu_handler(update, context)

# --- Ism-familiya qabul qilish ---
async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    full_name = update.message.text.strip()

    # Ism-familiyani saqlash
    context.user_data["full_name"] = full_name
    context.user_data["awaiting_name"] = False

    await update.message.reply_text(
        TEXTS[lang]["name_received"],
        reply_markup=main_menu_keyboard(lang),
    )

# --- Asosiy menyu tugmalari ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    text = update.message.text
    m = TEXTS[lang]["menu"]

    if text == m["exchange"]:
        await update.message.reply_text("💱 Valyuta ayirboshlash bo'limi tez orada ishga tushadi.")
    elif text == m["rate"]:
        await update.message.reply_text("📊 Kurs bo'limi tez orada ishga tushadi.")
    elif text == m["settings"]:
        await update.message.reply_text("⚙️ Sozlamalar bo'limi tez orada ishga tushadi.")
    elif text == m["support"]:
        await update.message.reply_text("🆘 Qo'llab-quvvatlash bo'limi tez orada ishga tushadi.")
    else:
        pass

# --- Asosiy funksiya ---
def main() -> None:
    TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"  # <-- shu yerga o'z tokeningizni kiriting

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
