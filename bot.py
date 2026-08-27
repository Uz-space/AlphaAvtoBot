import json
import logging
import os
import threading
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

# --- Bot fayli joylashgan papka (fayllar doim shu yerda saqlanadi) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Admin sozlamalari ---
ADMIN_IDS = {8758410535}  # <-- shu ro'yxatga boshqa adminlarni ham qo'shishingiz mumkin

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")

# --- Fayllarga bir vaqtda ko'p yozilib qolmasligi uchun qulflar ---
# (bir necha foydalanuvchi bir soniyada ro'yxatdan o'tsa ham, ma'lumot
# bir-birining ustidan yozilib ketmasligini kafolatlaydi)
_config_lock = threading.Lock()
_users_lock = threading.Lock()

# --- Tugma kalitlari va ularning admin panelida ko'rinadigan nomlari ---
BUTTON_KEYS = ["exchange", "rate", "settings", "support"]
BUTTON_ADMIN_LABELS = {
    "exchange": "💱 Valyuta ayirboshlash",
    "rate": "📊 Kurs",
    "settings": "⚙️ Sozlamalar",
    "support": "☎️ Aloqa",
}

# --- Mavjud ranglar (Telegram Bot API 9.4 orqali qo'llab-quvvatlanadi) ---
STYLE_OPTIONS = [
    ("default", "⚪ Standart"),
    ("primary", "🔵 Ko'k (Primary)"),
    ("success", "🟢 Yashil (Success)"),
    ("danger", "🔴 Qizil (Danger)"),
]
STYLE_LABELS = dict(STYLE_OPTIONS)

# --- Config faylini yuklash / saqlash ---
def load_config() -> dict:
    with _config_lock:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.exception("Config faylini o'qishda xatolik")
        return {"button_styles": {key: "default" for key in BUTTON_KEYS}}

def save_config(config: dict) -> None:
    with _config_lock:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

def get_button_style(key: str) -> str:
    config = load_config()
    return config.get("button_styles", {}).get(key, "default")

def set_button_style(key: str, style: str) -> None:
    # O'qish va yozish orasida boshqa jarayon kirib qolmasligi uchun
    # ikkalasini bitta qulf ostida bajaramiz
    with _config_lock:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except Exception:
                logger.exception("Config faylini o'qishda xatolik")
                config = {"button_styles": {k: "default" for k in BUTTON_KEYS}}
        else:
            config = {"button_styles": {k: "default" for k in BUTTON_KEYS}}

        config.setdefault("button_styles", {})[key] = style

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

# --- Ro'yxatdan o'tgan foydalanuvchilarni yuklash / saqlash ---
def load_users() -> dict:
    with _users_lock:
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.exception("Users faylini o'qishda xatolik")
        return {}

def save_users(users: dict) -> None:
    with _users_lock:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

def get_user(user_id: int) -> dict | None:
    users = load_users()
    return users.get(str(user_id))

def save_user(user_id: int, lang: str, phone: str, full_name: str) -> None:
    # O'qish va yozish orasida boshqa foydalanuvchi kirib qolmasligi uchun
    # ikkalasini bitta qulf ostida bajaramiz
    with _users_lock:
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r", encoding="utf-8") as f:
                    users = json.load(f)
            except Exception:
                logger.exception("Users faylini o'qishda xatolik")
                users = {}
        else:
            users = {}

        users[str(user_id)] = {"lang": lang, "phone": phone, "full_name": full_name}

        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

# --- Matnlar (har bir tilda) ---
TEXTS = {
    "uz_latin": {
        "ask_phone": "Xush kelibsiz! Botdan foydalanishni boshlash uchun telefon raqamingizni yuboring:",
        "phone_btn": "📱 Telefon raqamni yuborish",
        "phone_received": "Raqamingiz qabul qilindi. Iltimos, ism va familiyangizni kiriting:",
        "name_received": "✅ Rahmat! Quyidagi menyudan foydalaning:",
        "menu": {
            "exchange": "💱 Valyuta ayirboshlash",
            "rate": "📊 Kurs",
            "settings": "⚙️ Sozlamalar",
            "support": "☎️ Aloqa",
        },
        "menu_replies": {
            "exchange": "💱 Valyuta ayirboshlash bo'limi tez orada ishga tushadi.",
            "rate": "📊 Kurs bo'limi tez orada ishga tushadi.",
            "settings": "⚙️ Sozlamalar bo'limi tez orada ishga tushadi.",
            "support": "☎️ Aloqa bo'limi tez orada ishga tushadi.",
        },
    },
    "uz_cyrillic": {
        "ask_phone": "Хуш келибсиз! Ботдан фойдаланишни бошлаш учун телефон рақамингизни юборинг:",
        "phone_btn": "📱 Телефон рақамни юбориш",
        "phone_received": "Рақамингиз қабул қилинди. Илтимос, исм ва фамилиянгизни киритинг:",
        "name_received": "✅ Раҳмат! Қуйидаги менюдан фойдаланинг:",
        "menu": {
            "exchange": "💱 Валюта айирбошлаш",
            "rate": "📊 Курс",
            "settings": "⚙️ Созламалар",
            "support": "☎️ Алоқа",
        },
        "menu_replies": {
            "exchange": "💱 Валюта айирбошлаш бўлими тез орада ишга тушади.",
            "rate": "📊 Курс бўлими тез орада ишга тушади.",
            "settings": "⚙️ Созламалар бўлими тез орада ишга тушади.",
            "support": "☎️ Алоқа бўлими тез орада ишга тушади.",
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

# --- Rangga mos KeyboardButton yaratish ---
def styled_button(text: str, key: str) -> KeyboardButton:
    style = get_button_style(key)
    if style and style != "default":
        return KeyboardButton(text, style=style)
    return KeyboardButton(text)

# --- Asosiy menyu klaviaturasi (reply) ---
def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    m = TEXTS[lang]["menu"]
    keyboard = [
        [styled_button(m["exchange"], "exchange")],
        [styled_button(m["support"], "support"), styled_button(m["rate"], "rate")],
        [styled_button(m["settings"], "settings")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- /start komandasi ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    saved_user = get_user(user_id)

    if saved_user:
        # Foydalanuvchi avval ro'yxatdan o'tgan - to'g'ridan-to'g'ri menyuni ko'rsatamiz
        lang = saved_user.get("lang", "uz_latin")
        context.user_data["lang"] = lang
        context.user_data["phone"] = saved_user.get("phone")
        context.user_data["full_name"] = saved_user.get("full_name")
        context.user_data["awaiting_name"] = False

        await update.message.reply_text(
            TEXTS[lang]["name_received"],
            reply_markup=main_menu_keyboard(lang),
        )
        return

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

    context.user_data["lang"] = selected
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        TEXTS[selected]["ask_phone"],
        reply_markup=phone_keyboard(selected),
    )

# --- Telefon raqam qabul qilish ---
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang")
    if not lang:
        saved_user = get_user(update.effective_user.id)
        lang = saved_user.get("lang", "uz_latin") if saved_user else "uz_latin"
        context.user_data["lang"] = lang

    phone = update.message.contact.phone_number

    context.user_data["phone"] = phone
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
    lang = context.user_data.get("lang")
    if not lang:
        saved_user = get_user(update.effective_user.id)
        lang = saved_user.get("lang", "uz_latin") if saved_user else "uz_latin"
        context.user_data["lang"] = lang

    full_name = update.message.text.strip()
    phone = context.user_data.get("phone", "")

    context.user_data["full_name"] = full_name
    context.user_data["awaiting_name"] = False

    # Ro'yxatdan o'tishni doimiy saqlash - keyingi /start larda qayta so'ralmasin
    user_id = update.effective_user.id
    save_user(user_id, lang, phone, full_name)

    await update.message.reply_text(
        TEXTS[lang]["name_received"],
        reply_markup=main_menu_keyboard(lang),
    )

# --- Asosiy menyu tugmalari ---
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text

    # Foydalanuvchi tilini aniqlash (sessiya yo'qolgan bo'lsa faylga qaraymiz)
    lang = context.user_data.get("lang")
    if not lang:
        saved_user = get_user(update.effective_user.id)
        lang = saved_user.get("lang", "uz_latin") if saved_user else "uz_latin"
        context.user_data["lang"] = lang

    # Bosilgan tugma matnini ikkala tildan ham qidiramiz
    # (bu ekrandagi tugma tili bilan sessiyadagi til mos kelmasa ham ishlashini kafolatlaydi)
    matched_key = None
    matched_lang = lang
    for lng, lng_texts in TEXTS.items():
        for key, value in lng_texts["menu"].items():
            if value == text:
                matched_key = key
                matched_lang = lng
                break
        if matched_key:
            break

    if not matched_key:
        return  # Menyuga tegishli bo'lmagan matn

    # Agar tugma matni sessiyadagi tildan farq qilsa, tilni yangilaymiz
    if matched_lang != lang:
        context.user_data["lang"] = matched_lang

    reply_text = TEXTS[matched_lang]["menu_replies"][matched_key]
    await update.message.reply_text(reply_text)

# =========================================================
# ============ ADMIN PANEL (tugma ranglari) ==============
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- Admin panel asosiy ro'yxati ---
def admin_panel_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key in BUTTON_KEYS:
        current_style = get_button_style(key)
        style_emoji = STYLE_LABELS.get(current_style, "⚪ Standart").split(" ")[0]
        label = f"{style_emoji} {BUTTON_ADMIN_LABELS[key]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin_pick_{key}")])
    return InlineKeyboardMarkup(rows)

# --- Bitta tugma uchun rang tanlash klaviaturasi ---
def color_choice_keyboard(key: str) -> InlineKeyboardMarkup:
    rows = []
    for style_value, style_label in STYLE_OPTIONS:
        rows.append([InlineKeyboardButton(style_label, callback_data=f"admin_set_{key}_{style_value}")])
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(rows)

# --- /admin komandasi ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Sizda admin panelga kirish huquqi yo'q.")
        return

    await update.message.reply_text(
        "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
        reply_markup=admin_panel_keyboard(),
    )

# --- Admin panel callback'lari ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "admin_back":
        await query.edit_message_text(
            "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if data.startswith("admin_pick_"):
        key = data.replace("admin_pick_", "")
        if key not in BUTTON_KEYS:
            return
        current_style = get_button_style(key)
        current_label = STYLE_LABELS.get(current_style, "⚪ Standart")
        await query.edit_message_text(
            f"🎨 {BUTTON_ADMIN_LABELS[key]}\n"
            f"Joriy rang: {current_label}\n\n"
            f"Yangi rangni tanlang:",
            reply_markup=color_choice_keyboard(key),
        )
        return

    if data.startswith("admin_set_"):
        # format: admin_set_<key>_<style>
        remainder = data.replace("admin_set_", "")
        # key hech qachon "_" bo'lmaydi, style ham bitta so'z - shuning uchun rsplit ishlatamiz
        key, style = remainder.rsplit("_", 1)
        if key not in BUTTON_KEYS or style not in STYLE_LABELS:
            return

        set_button_style(key, style)

        await query.answer(f"✅ {BUTTON_ADMIN_LABELS[key]} rangi o'zgartirildi!", show_alert=False)
        await query.edit_message_text(
            "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_panel_keyboard(),
        )
        return

# --- Asosiy funksiya ---
def main() -> None:
    TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"  # <-- shu yerga o'z tokeningizni kiriting

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
