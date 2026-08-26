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
        "phone_received": "Raqamingiz muvaffaqiyatli qabul qilindi. Iltimos, ism va familiyangizni kiriting:",
        "name_received": "✅ Maʼlumotlaringiz qabul qilindi.\nQuyidagi menyu tugmalaridan foydalaning.",
    },
    "uz_cyrillic": {
        "choose_lang": "🌐 Tilni tanlang / Тилни танланг:",
        "ask_phone": "Хуш келибсиз! Ботдан фойдаланишни бошлаш учун телефон рақамингизни юборинг:",
        "phone_btn": "📱 Телефон рақамни юбориш",
        "phone_received": "Рақамингиз муваффақиятли қабул қилинди. Илтимос, исм ва фамилиянгизни киритинг:",
        "name_received": "✅ Маълумотларингиз қабул қилинди.\nҚуйидаги меню тугмаларидан фойдаланинг.",
    },
}

# --- Menyu tugmalari (asosiy menyu) ---
def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    if lang == "uz_latin":
        keyboard = [
            ["📋 Profil", "🔄 Sozlamalar"],
            ["ℹ️ Yordam", "📞 Biz bilan bog'lanish"],
        ]
    else:  # uz_cyrillic
        keyboard = [
            ["📋 Профил", "🔄 Созламалар"],
            ["ℹ️ Ёрдам", "📞 Биз билан боғланиш"],
        ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
    # Agar foydalanuvchi avval til tanlagan bo'lsa, to'g'ridan-to'g'ri telefon so'rang
    if "lang" in context.user_data:
        lang = context.user_data["lang"]
        await update.message.reply_text(
            TEXTS[lang]["ask_phone"],
            reply_markup=phone_keyboard(lang),
        )
    else:
        # Til tanlashni so'rang
        await update.message.reply_text(
            TEXTS["uz_latin"]["choose_lang"],
            reply_markup=language_keyboard(),
        )

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

    # Oldingi inline xabarni o'chirish
    await query.delete_message()

    # Yangi xabar yuborish (faqat 1 marta)
    await query.message.reply_text(
        TEXTS[selected]["ask_phone"],
        reply_markup=phone_keyboard(selected),
    )

# --- Telefon raqam qabul qilish ---
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    phone = update.message.contact.phone_number

    # Telefon raqamni saqlash
    context.user_data["phone"] = phone

    # Telefon klaviaturasini o'chirish va ism-familiya so'rash
    await update.message.reply_text(
        TEXTS[lang]["phone_received"],
        reply_markup=ReplyKeyboardRemove(),
    )
    
    logger.info(f"Foydalanuvchi {phone} raqamini yubordi")
    
    # Keyingi qadam: ism-familiya kutish holatiga o'tish
    context.user_data["waiting_for_name"] = True

# --- Ism-familiya qabul qilish ---
async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Faqat ism-familiya kutilayotgan holatda ishlaydi
    if not context.user_data.get("waiting_for_name", False):
        # Agar ism-familiya kutilmayotgan bo'lsa, xabarni ignore qilamiz
        return
    
    lang = context.user_data.get("lang", "uz_latin")
    full_name = update.message.text.strip()
    
    # Ism-familiyani saqlash
    context.user_data["full_name"] = full_name
    
    # Ism-familiya kutilish holatini o'chirish
    context.user_data["waiting_for_name"] = False
    
    # Tasdiqlash xabari va menyuni ko'rsatish
    await update.message.reply_text(
        TEXTS[lang]["name_received"],
        reply_markup=main_menu_keyboard(lang),
    )
    
    logger.info(f"Foydalanuvchi ismi: {full_name}")

# --- Menyu tugmalarini qayta ishlash ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Agar ism-familiya kutilayotgan bo'lsa, bu funksiya ishlamasligi kerak
    if context.user_data.get("waiting_for_name", False):
        return
    
    lang = context.user_data.get("lang", "uz_latin")
    text = update.message.text
    
    if text in ["📋 Profil", "📋 Профил"]:
        await show_profile(update, context)
    elif text in ["🔄 Sozlamalar", "🔄 Созламалар"]:
        await show_settings(update, context)
    elif text in ["ℹ️ Yordam", "ℹ️ Ёрдам"]:
        await show_help(update, context)
    elif text in ["📞 Biz bilan bog'lanish", "📞 Биз билан боғланиш"]:
        await show_contact(update, context)
    else:
        await update.message.reply_text(
            "Iltimos, menyu tugmalaridan birini tanlang." if lang == "uz_latin" else "Илтимос, меню тугмаларидан бирини танланг."
        )

# --- Profil ko'rsatish ---
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    phone = context.user_data.get("phone", "Noma'lum")
    full_name = context.user_data.get("full_name", "Noma'lum")
    
    if lang == "uz_latin":
        text = f"👤 <b>Profil ma'lumotlari</b>\n\n"
        text += f"📛 Ism-familiya: {full_name}\n"
        text += f"📱 Telefon: {phone}"
    else:
        text = f"👤 <b>Профил маълумотлари</b>\n\n"
        text += f"📛 Исм-фамилия: {full_name}\n"
        text += f"📱 Телефон: {phone}"
    
    await update.message.reply_text(text, parse_mode="HTML")

# --- Sozlamalar ko'rsatish ---
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    
    if lang == "uz_latin":
        text = "⚙️ <b>Sozlamalar</b>\n\nHozircha sozlamalar mavjud emas."
    else:
        text = "⚙️ <b>Созламалар</b>\n\nҲозирча созламалар мавжуд эмас."
    
    await update.message.reply_text(text, parse_mode="HTML")

# --- Yordam ko'rsatish ---
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    
    if lang == "uz_latin":
        text = "ℹ️ <b>Yordam</b>\n\nBotdan foydalanish bo'yicha ko'rsatmalar..."
    else:
        text = "ℹ️ <b>Ёрдам</b>\n\nБотдан фойдаланиш бўйича кўрсатмалар..."
    
    await update.message.reply_text(text, parse_mode="HTML")

# --- Bog'lanish ko'rsatish ---
async def show_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    
    if lang == "uz_latin":
        text = "📞 <b>Biz bilan bog'lanish</b>\n\n"
        text += "Telefon: +998 90 123 45 67\n"
        text += "Email: info@example.com"
    else:
        text = "📞 <b>Биз билан боғланиш</b>\n\n"
        text += "Телефон: +998 90 123 45 67\n"
        text += "Email: info@example.com"
    
    await update.message.reply_text(text, parse_mode="HTML")

# --- Asosiy funksiya ---
def main() -> None:
    TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"
    
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
