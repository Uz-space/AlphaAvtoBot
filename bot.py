import asyncio
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
CURRENCIES_FILE = os.path.join(BASE_DIR, "currencies.json")

# --- Fayllarga bir vaqtda ko'p yozilib qolmasligi uchun qulflar ---
# (bir necha foydalanuvchi bir soniyada ro'yxatdan o'tsa ham, ma'lumot
# bir-birining ustidan yozilib ketmasligini kafolatlaydi)
_config_lock = threading.Lock()
_users_lock = threading.Lock()
_currencies_lock = threading.Lock()

# --- Tugma kalitlari va ularning admin panelida ko'rinadigan nomlari ---
BUTTON_KEYS = ["exchange", "support", "rate", "settings"]
BUTTON_ADMIN_LABELS = {
    "exchange": "💱 Valyuta ayirboshlash",
    "rate": "📊 Kurs",
    "settings": "⚙️ Sozlamalar",
    "support": "☎️ Aloqa",
}

# --- Inline (bir martalik) tugmalar - reply-menyudan farqli, avtomatik yangilanadi,
# shuning uchun "Saqlash va yuborish" kerak emas, rang darhol qo'llanadi ---
INLINE_BUTTON_KEYS = ["lang_latin", "lang_cyrillic", "home", "stg_lang", "stg_name", "stg_phone"]
INLINE_BUTTON_ADMIN_LABELS = {
    "lang_latin": "🇺🇿 Oʻzbekcha (til tanlash)",
    "lang_cyrillic": "🇺🇿 Кириллча (til tanlash)",
    "home": "🏠 Bosh menyu",
    "stg_lang": "🌐 Tilni o'zgartirish (Sozlamalar)",
    "stg_name": "👤 Ismni o'zgartirish (Sozlamalar)",
    "stg_phone": "📞 Telefonni o'zgartirish (Sozlamalar)",
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

# --- Valyutalar ro'yxatini yuklash / saqlash (faqat admin qo'sha/o'chira oladi) ---
def load_currencies() -> list:
    with _currencies_lock:
        if os.path.exists(CURRENCIES_FILE):
            try:
                with open(CURRENCIES_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("currencies", [])
            except Exception:
                logger.exception("Currencies faylini o'qishda xatolik")
        return []

def _save_currencies_unlocked(currencies: list) -> None:
    with open(CURRENCIES_FILE, "w", encoding="utf-8") as f:
        json.dump({"currencies": currencies}, f, ensure_ascii=False, indent=2)

def add_currency(name: str, category: str = "crypto") -> dict:
    import uuid
    with _currencies_lock:
        if os.path.exists(CURRENCIES_FILE):
            try:
                with open(CURRENCIES_FILE, "r", encoding="utf-8") as f:
                    currencies = json.load(f).get("currencies", [])
            except Exception:
                currencies = []
        else:
            currencies = []

        new_entry = {
            "id": uuid.uuid4().hex[:8],
            "name": name,
            "category": category,  # "fiat" (so'm) yoki "crypto" - faqat fiat<->crypto almashinadi
            "give_style": "default",  # 🔷 "bering" tomonidagi rang
            "take_style": "default",  # 🔶 "oling" tomonidagi rang
        }
        currencies.append(new_entry)
        _save_currencies_unlocked(currencies)
        return new_entry

def set_currency_category(currency_id: str, category: str) -> bool:
    with _currencies_lock:
        if os.path.exists(CURRENCIES_FILE):
            try:
                with open(CURRENCIES_FILE, "r", encoding="utf-8") as f:
                    currencies = json.load(f).get("currencies", [])
            except Exception:
                currencies = []
        else:
            currencies = []

        found = False
        for c in currencies:
            if c["id"] == currency_id:
                c["category"] = category
                found = True
                break

        if found:
            _save_currencies_unlocked(currencies)
        return found

def remove_currency(currency_id: str) -> bool:
    with _currencies_lock:
        if os.path.exists(CURRENCIES_FILE):
            try:
                with open(CURRENCIES_FILE, "r", encoding="utf-8") as f:
                    currencies = json.load(f).get("currencies", [])
            except Exception:
                currencies = []
        else:
            currencies = []

        new_list = [c for c in currencies if c["id"] != currency_id]
        removed = len(new_list) != len(currencies)
        if removed:
            _save_currencies_unlocked(new_list)
        return removed

def set_currency_style(currency_id: str, side: str, style: str) -> bool:
    """side: 'give' (🔷 bering) yoki 'take' (🔶 oling)"""
    field = "give_style" if side == "give" else "take_style"
    with _currencies_lock:
        if os.path.exists(CURRENCIES_FILE):
            try:
                with open(CURRENCIES_FILE, "r", encoding="utf-8") as f:
                    currencies = json.load(f).get("currencies", [])
            except Exception:
                currencies = []
        else:
            currencies = []

        found = False
        for c in currencies:
            if c["id"] == currency_id:
                c[field] = style
                # Eski ma'lumotlar bilan moslik uchun (agar eski "style" maydoni bo'lsa)
                c.pop("style", None)
                found = True
                break

        if found:
            _save_currencies_unlocked(currencies)
        return found

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
        "exchange_header": "🔀 Almashuv: qaysi tomondan boshlaysiz (🔷 bering / 🔶 oling):",
        "exchange_empty": "Hozircha valyutalar qo'shilmagan. Admin tez orada qo'shadi.",
        "exchange_selected": "✅ Tanlandi: {name}",
        "exchange_step2_header": "✅ 1-valyutani tanladingiz. Endi 2-valyutani (🔶) tanlang:",
        "exchange_pair_selected": "✅ {give_name} → {take_name}\n\nJuftlik tanlandi.",
        "exchange_disabled_pair": "❌ Bu juftlik mos emas (Fiat↔Fiat yoki Kripto↔Kripto ishlamaydi)",
        "support_prompt": "✍️ Xabaringizni yozing, u to'g'ridan-to'g'ri operatorga yuboriladi:",
        "support_sent": "✅ Xabaringiz yuborildi! Tez orada javob beramiz.",
        "support_admin_reply_prefix": "💬 Operator javobi:\n\n",
        "rate_sell_header": "📉 Sotish kursi",
        "rate_buy_header": "📈 Sotib olish kursi",
        "rate_currency_unit": "so'm",
        "rate_empty": "Hozircha valyutalar qo'shilmagan.",
        "rate_not_set": "belgilanmagan",
        "settings_header": "⚙️ Sozlamalar\n\n👤 Ism: {name}\n🌐 Til: {lang_label}\n📞 Telefon: {phone}\n\nO'zgartirmoqchi bo'lganingizni tanlang 👇",
        "settings_change_lang": "🌐 Tilni o'zgartirish",
        "settings_change_name": "👤 Ismni o'zgartirish",
        "settings_change_phone": "📞 Telefonni o'zgartirish",
        "settings_choose_new_lang": "🌐 Yangi tilni tanlang:",
        "settings_lang_changed": "✅ Til o'zgartirildi!",
        "settings_ask_new_name": "✍️ Yangi ism-familiyangizni kiriting:",
        "settings_name_changed": "✅ Ism yangilandi!",
        "settings_ask_new_phone": "📞 Yangi telefon raqamingizni yuboring:",
        "settings_phone_changed": "✅ Telefon raqam yangilandi!",
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
        "exchange_header": "🔀 Алмашув: қайси томондан бошлайсиз (🔷 беринг / 🔶 олинг):",
        "exchange_empty": "Ҳозирча валюталар қўшилмаган. Админ тез орада қўшади.",
        "exchange_selected": "✅ Танланди: {name}",
        "exchange_step2_header": "✅ 1-валютани танладингиз. Энди 2-валютани (🔶) танланг:",
        "exchange_pair_selected": "✅ {give_name} → {take_name}\n\nЖуфтлик танланди.",
        "exchange_disabled_pair": "❌ Бу жуфтлик мос эмас (Fiat↔Fiat ёки Крипто↔Крипто ишламайди)",
        "support_prompt": "✍️ Хабарингизни ёзинг, у тўғридан-тўғри операторга юборилади:",
        "support_sent": "✅ Хабарингиз юборилди! Тез орада жавоб берамиз.",
        "support_admin_reply_prefix": "💬 Оператор жавоби:\n\n",
        "rate_sell_header": "📉 Сотиш курси",
        "rate_buy_header": "📈 Сотиб олиш курси",
        "rate_currency_unit": "сўм",
        "rate_empty": "Ҳозирча валюталар қўшилмаган.",
        "rate_not_set": "белгиланмаган",
        "settings_header": "⚙️ Созламалар\n\n👤 Исм: {name}\n🌐 Тил: {lang_label}\n📞 Телефон: {phone}\n\nЎзгартирмоқчи бўлганингизни танланг 👇",
        "settings_change_lang": "🌐 Тилни ўзгартириш",
        "settings_change_name": "👤 Исмни ўзгартириш",
        "settings_change_phone": "📞 Телефонни ўзгартириш",
        "settings_choose_new_lang": "🌐 Янги тилни танланг:",
        "settings_lang_changed": "✅ Тил ўзгартирилди!",
        "settings_ask_new_name": "✍️ Янги исм-фамилиянгизни киритинг:",
        "settings_name_changed": "✅ Исм янгиланди!",
        "settings_ask_new_phone": "📞 Янги телефон рақамингизни юборинг:",
        "settings_phone_changed": "✅ Телефон рақам янгиланди!",
    },
}

# --- Til tanlash klaviaturasi (inline) ---
def language_keyboard() -> InlineKeyboardMarkup:
    latin_style = get_button_style("lang_latin")
    cyrillic_style = get_button_style("lang_cyrillic")
    latin_kwargs = {} if latin_style == "default" else {"style": latin_style}
    cyrillic_kwargs = {} if cyrillic_style == "default" else {"style": cyrillic_style}

    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 Oʻzbekcha", callback_data="lang_uz_latin", **latin_kwargs),
            InlineKeyboardButton("🇺🇿 Кириллча", callback_data="lang_uz_cyrillic", **cyrillic_kwargs),
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

# --- Valyuta almashuv klaviaturasi (inline, 2 ustunli: bering / oling) ---
def exchange_keyboard(lang: str, give_currency_id: str = None) -> InlineKeyboardMarkup:
    currencies = load_currencies()
    rows = []

    # Agar "berish" valyutasi allaqachon tanlangan bo'lsa - uning toifasini aniqlaymiz,
    # shunga qarab "olish" tomonida mos kelmaydigan tugmalarni bloklaymiz
    give_category = None
    if give_currency_id:
        selected = next((c for c in currencies if c["id"] == give_currency_id), None)
        give_category = selected.get("category", "crypto") if selected else None

    for currency in currencies:
        give_style = currency.get("give_style", "default")
        take_style = currency.get("take_style", "default")
        give_kwargs = {} if give_style == "default" else {"style": give_style}
        take_kwargs = {} if take_style == "default" else {"style": take_style}

        # --- 🔷 "Berish" tugmasi ---
        is_selected_give = give_currency_id and currency["id"] == give_currency_id
        give_label = f"🔷 {currency['name']} ✅" if is_selected_give else f"🔷 {currency['name']}"
        give_btn = InlineKeyboardButton(give_label, callback_data=f"exch_give_{currency['id']}", **give_kwargs)

        # --- 🔶 "Olish" tugmasi ---
        if give_currency_id:
            currency_category = currency.get("category", "crypto")
            if currency_category == give_category:
                # Fiat<->Fiat yoki Kripto<->Kripto ishlamaydi - bloklaymiz
                take_btn = InlineKeyboardButton("⬛", callback_data="exch_disabled")
            else:
                take_btn = InlineKeyboardButton(f"🔶 {currency['name']}", callback_data=f"exch_take_{currency['id']}", **take_kwargs)
        else:
            take_btn = InlineKeyboardButton(f"🔶 {currency['name']}", callback_data=f"exch_take_{currency['id']}", **take_kwargs)

        rows.append([give_btn, take_btn])

    rows.append(home_button_row(lang))
    return InlineKeyboardMarkup(rows)

# --- "Bosh menyu" tugmasi (bir nechta joyda ishlatiladi, rangi HAMMASIDA bir xil "home" kalitidan) ---
def home_button_row(lang: str) -> list:
    home_style = get_button_style("home")
    home_kwargs = {} if home_style == "default" else {"style": home_style}
    home_label = "🏠 Bosh menyu" if lang == "uz_latin" else "🏠 Бош меню"
    return [InlineKeyboardButton(home_label, callback_data="exch_home", **home_kwargs)]

# --- "Kurs" bo'limi: sotish/sotib olish kurslari ro'yxati (faqat ko'rinish, hozircha statik) ---
def build_rate_text(lang: str) -> str:
    currencies = load_currencies()
    unit = TEXTS[lang]["rate_currency_unit"]
    not_set = TEXTS[lang]["rate_not_set"]

    if not currencies:
        return TEXTS[lang]["rate_empty"]

    sell_lines = [TEXTS[lang]["rate_sell_header"]]
    buy_lines = [TEXTS[lang]["rate_buy_header"]]

    for currency in currencies:
        name = currency["name"]
        # Hozircha faqat ko'rinish - haqiqiy kurs/spred hisob-kitobi keyinroq ulanadi
        sell_rate = currency.get("sell_rate")
        buy_rate = currency.get("buy_rate")
        sell_value = f"{sell_rate:,}".replace(",", " ") if sell_rate else not_set
        buy_value = f"{buy_rate:,}".replace(",", " ") if buy_rate else not_set
        sell_lines.append(f"1 {name} = {sell_value} {unit}")
        buy_lines.append(f"1 {name} = {buy_value} {unit}")

    return "\n".join(sell_lines) + "\n\n" + "\n".join(buy_lines)

def rate_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([home_button_row(lang)])

# --- "Sozlamalar" bo'limi: joriy ma'lumot + o'zgartirish tugmalari ---
def settings_text(lang: str, name: str, phone: str) -> str:
    lang_label = "🇺🇿 Oʻzbekcha (lotin)" if lang == "uz_latin" else "🇺🇿 Кириллча"
    return TEXTS[lang]["settings_header"].format(
        name=name or "—",
        lang_label=lang_label,
        phone=phone or "—",
    )

def settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    def styled(text: str, key: str, callback_data: str) -> InlineKeyboardButton:
        style = get_button_style(key)
        kwargs = {} if style == "default" else {"style": style}
        return InlineKeyboardButton(text, callback_data=callback_data, **kwargs)

    rows = [
        [styled(TEXTS[lang]["settings_change_lang"], "stg_lang", "stg_lang")],
        [styled(TEXTS[lang]["settings_change_name"], "stg_name", "stg_name")],
        [styled(TEXTS[lang]["settings_change_phone"], "stg_phone", "stg_phone")],
    ]
    rows.append(home_button_row(lang))
    return InlineKeyboardMarkup(rows)

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

    # Agar bu "Sozlamalar"dan turib til o'zgartirish bo'lsa - ro'yxatdan o'tish
    # oqimini QAYTA boshlamaymiz, faqat tilni yangilab, asosiy menyuga qaytamiz
    if context.user_data.get("changing_language"):
        context.user_data["changing_language"] = False
        existing = get_user(query.from_user.id) or {}
        phone = existing.get("phone") or context.user_data.get("phone", "")
        full_name = existing.get("full_name") or context.user_data.get("full_name", "")
        context.user_data["lang"] = selected
        save_user(query.from_user.id, selected, phone, full_name)

        try:
            await query.message.delete()
        except Exception:
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=TEXTS[selected]["settings_lang_changed"],
            reply_markup=main_menu_keyboard(selected),
        )
        return

    # Aks holda - bu birinchi marta ro'yxatdan o'tish oqimi
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

    # Agar bu "Sozlamalar"dan turib telefon o'zgartirish bo'lsa
    if context.user_data.get("awaiting_phone_change"):
        context.user_data["awaiting_phone_change"] = False
        existing = get_user(update.effective_user.id) or {}
        full_name = existing.get("full_name") or context.user_data.get("full_name", "")
        context.user_data["phone"] = phone
        save_user(update.effective_user.id, lang, phone, full_name)

        await update.message.reply_text(
            TEXTS[lang]["settings_phone_changed"],
            reply_markup=main_menu_keyboard(lang),
        )
        return

    # Aks holda - bu birinchi marta ro'yxatdan o'tish oqimi
    context.user_data["phone"] = phone
    context.user_data["awaiting_name"] = True

    await update.message.reply_text(
        TEXTS[lang]["phone_received"],
        reply_markup=ReplyKeyboardRemove(),
    )

# --- Matnli xabarlarni yo'naltirish (ism, valyuta nomi yoki menyu) ---
# --- Matn asosiy menyu tugmalaridan biriga mos kelishini tekshirish (ikkala tildan) ---
def find_menu_key(text: str):
    for lng, lng_texts in TEXTS.items():
        for key, value in lng_texts["menu"].items():
            if value == text:
                return key, lng
    return None, None

# --- Matnli xabarlarni yo'naltirish (ism, valyuta nomi yoki menyu) ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Agar foydalanuvchi biror "kutish" holatida bo'lsa-yu (masalan Aloqa xabari,
    # ism o'zgartirish va h.k.), lekin ASOSIY MENYU tugmalaridan birini bosgan bo'lsa -
    # avval barcha kutish holatlarini bekor qilamiz va o'sha tugmaning o'zini bajaramiz.
    # Aks holda masalan "Kurs" tugmasi bosilganda u "Aloqa xabari" deb yuborilib ketardi.
    matched_key, _ = find_menu_key(update.message.text or "")
    if matched_key:
        context.user_data["awaiting_currency_name"] = False
        context.user_data["awaiting_name_change"] = False
        context.user_data["awaiting_support_message"] = False
        context.user_data["awaiting_phone_change"] = False
        context.user_data["changing_language"] = False
        if is_admin(update.effective_user.id):
            context.user_data["awaiting_reply_to"] = None
        await menu_handler(update, context)
        return

    if is_admin(update.effective_user.id) and context.user_data.get("awaiting_reply_to"):
        await admin_reply_handler(update, context)
    elif context.user_data.get("awaiting_currency_name"):
        await currency_name_handler(update, context)
    elif context.user_data.get("awaiting_name"):
        await name_handler(update, context)
    elif context.user_data.get("awaiting_name_change"):
        await name_change_handler(update, context)
    elif context.user_data.get("awaiting_support_message"):
        await support_message_handler(update, context)
    else:
        await menu_handler(update, context)

# --- Sozlamalar: ismni o'zgartirish ---
async def name_change_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "uz_latin")
    context.user_data["awaiting_name_change"] = False
    new_name = update.message.text.strip()

    if not new_name:
        await update.message.reply_text(TEXTS[lang]["settings_ask_new_name"])
        context.user_data["awaiting_name_change"] = True
        return

    existing = get_user(update.effective_user.id) or {}
    phone = existing.get("phone") or context.user_data.get("phone", "")
    context.user_data["full_name"] = new_name
    save_user(update.effective_user.id, lang, phone, new_name)

    await update.message.reply_text(
        TEXTS[lang]["settings_name_changed"],
        reply_markup=main_menu_keyboard(lang),
    )

# --- Admin: yangi valyuta nomini qabul qilish ---
async def currency_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_currency_name"] = False
    name = update.message.text.strip()

    if not name:
        await update.message.reply_text("Bo'sh nom kiritib bo'lmaydi.")
        return

    # Nomni vaqtincha saqlaymiz, endi toifasini so'raymiz (fiat/kripto)
    context.user_data["pending_currency_name"] = name
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 Fiat (so'm)", callback_data="admin_curr_cat_fiat")],
        [InlineKeyboardButton("🪙 Kripto", callback_data="admin_curr_cat_crypto")],
    ])
    await update.message.reply_text(
        f"'{name}' — toifasini tanlang:\n\n"
        f"💵 Fiat — so'm ekvivalenti (masalan UZCARD, HUMO)\n"
        f"🪙 Kripto — kriptovalyuta (masalan USDT, TRX)\n\n"
        f"Eslatma: faqat Fiat↔Kripto almashtiriladi, Fiat↔Fiat va Kripto↔Kripto ishlamaydi.",
        reply_markup=keyboard,
    )

# --- Foydalanuvchi: aloqa xabarini qabul qilish va adminga yuborish ---
async def support_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_support_message"] = False
    lang = context.user_data.get("lang", "uz_latin")
    message_text = update.message.text.strip()

    if not message_text:
        await update.message.reply_text(TEXTS[lang]["support_prompt"])
        context.user_data["awaiting_support_message"] = True
        return

    user = update.effective_user
    user_id = user.id
    saved_user = get_user(user_id) or {}
    full_name = saved_user.get("full_name") or user.full_name or "Noma'lum"
    phone = saved_user.get("phone", "—")
    username = f"@{user.username}" if user.username else "—"

    admin_text = (
        f"📩 Yangi xabar (Aloqa)\n\n"
        f"👤 Ism: {full_name}\n"
        f"📱 Tel: {phone}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: {user_id}\n\n"
        f"💬 Xabar:\n{message_text}"
    )
    reply_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Javob yozish", callback_data=f"admin_reply_{user_id}")]
    ])

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_text, reply_markup=reply_keyboard)
        except Exception:
            logger.exception(f"Admin {admin_id}ga xabar yuborishda xatolik")

    await update.message.reply_text(TEXTS[lang]["support_sent"])

# --- Admin: foydalanuvchiga javob yozish ---
async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    target_user_id = context.user_data.get("awaiting_reply_to")
    context.user_data["awaiting_reply_to"] = None
    reply_text = update.message.text.strip()

    if not target_user_id or not reply_text:
        await update.message.reply_text("Xatolik: javob yuborilmadi.")
        return

    target_user = get_user(target_user_id)
    target_lang = target_user.get("lang", "uz_latin") if target_user else "uz_latin"
    prefix = TEXTS[target_lang]["support_admin_reply_prefix"]

    try:
        await context.bot.send_message(chat_id=target_user_id, text=f"{prefix}{reply_text}")
        await update.message.reply_text("✅ Javob yuborildi.")
    except Exception:
        logger.exception(f"Userga ({target_user_id}) javob yuborishda xatolik")
        await update.message.reply_text("❌ Xatolik: foydalanuvchiga yuborib bo'lmadi (botni bloklagan bo'lishi mumkin).")

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

    # "Valyuta ayirboshlash" alohida - inline klaviatura bilan valyutalar ro'yxatini ko'rsatamiz
    if matched_key == "exchange":
        context.user_data["exch_give_selected"] = None
        currencies = load_currencies()
        if not currencies:
            await update.message.reply_text(TEXTS[matched_lang]["exchange_empty"])
            return
        await update.message.reply_text(
            TEXTS[matched_lang]["exchange_header"],
            reply_markup=exchange_keyboard(matched_lang),
        )
        return

    # "Aloqa" alohida - foydalanuvchidan xabar kutamiz, keyin adminga yuboramiz
    if matched_key == "support":
        context.user_data["awaiting_support_message"] = True
        await update.message.reply_text(TEXTS[matched_lang]["support_prompt"])
        return

    # "Kurs" alohida - sotish/sotib olish kurslari ro'yxati (hozircha faqat ko'rinish)
    if matched_key == "rate":
        await update.message.reply_text(
            build_rate_text(matched_lang),
            reply_markup=rate_keyboard(matched_lang),
        )
        return

    # "Sozlamalar" alohida - joriy ma'lumot va o'zgartirish tugmalari
    if matched_key == "settings":
        saved_user = get_user(update.effective_user.id) or {}
        name = saved_user.get("full_name") or context.user_data.get("full_name", "")
        phone = saved_user.get("phone") or context.user_data.get("phone", "")
        await update.message.reply_text(
            settings_text(matched_lang, name, phone),
            reply_markup=settings_keyboard(matched_lang),
        )
        return

    reply_text = TEXTS[matched_lang]["menu_replies"][matched_key]
    await update.message.reply_text(reply_text)

# --- Valyuta tanlash callback'i ---
async def exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    lang = context.user_data.get("lang")
    if not lang:
        saved_user = get_user(query.from_user.id)
        lang = saved_user.get("lang", "uz_latin") if saved_user else "uz_latin"

    data = query.data

    if data == "exch_home":
        await query.answer()
        context.user_data["exch_give_selected"] = None
        # Almashuv xabarini butunlay o'chiramiz (ortiqcha matn qolib ketmasligi uchun)
        # va asosiy (reply) menyuni qaytaramiz
        try:
            await query.message.delete()
        except Exception:
            # Ba'zi holatlarda xabarni o'chirib bo'lmasligi mumkin (masalan juda eski) -
            # bunda hech bo'lmasa tugmalarni olib tashlaymiz
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=TEXTS[lang]["name_received"],
            reply_markup=main_menu_keyboard(lang),
        )
        return

    if data == "exch_disabled":
        # Qora kvadrat - fiat<->fiat yoki kripto<->kripto ruxsat etilmagan
        await query.answer(TEXTS[lang]["exchange_disabled_pair"], show_alert=True)
        return

    currencies = load_currencies()

    if data.startswith("exch_give_"):
        currency_id = data.replace("exch_give_", "")
        currency = next((c for c in currencies if c["id"] == currency_id), None)
        if not currency:
            await query.answer()
            return

        # 1-valyuta (berish) tanlandi - endi 2-bosqichga o'tamiz:
        # tanlangan valyutani ✅ bilan belgilaymiz, mos kelmaydigan "olish" tugmalarini bloklaymiz
        context.user_data["exch_give_selected"] = currency_id
        await query.answer()
        await query.edit_message_text(
            TEXTS[lang]["exchange_step2_header"],
            reply_markup=exchange_keyboard(lang, give_currency_id=currency_id),
        )
        return

    if data.startswith("exch_take_"):
        currency_id = data.replace("exch_take_", "")
        take_currency = next((c for c in currencies if c["id"] == currency_id), None)
        if not take_currency:
            await query.answer()
            return

        give_id = context.user_data.get("exch_give_selected")
        give_currency = next((c for c in currencies if c["id"] == give_id), None) if give_id else None

        if not give_currency:
            # "Berish" valyutasi hali tanlanmagan (masalan eski xabarda to'g'ridan-to'g'ri
            # "olish" tugmasi bosilgan) - avval berish valyutasini so'raymiz
            await query.answer(TEXTS[lang]["exchange_selected"].format(name=take_currency["name"]))
            return

        # Juftlik to'liq tanlandi
        context.user_data["exch_give_selected"] = None
        await query.answer()
        await query.edit_message_text(
            TEXTS[lang]["exchange_pair_selected"].format(
                give_name=give_currency["name"],
                take_name=take_currency["name"],
            ),
            reply_markup=InlineKeyboardMarkup([home_button_row(lang)]),
        )
        # Keyingi qadam (summa kiritish, kurs hisoblash) shu yerdan davom etadi -
        # hozircha faqat juftlik tanlovi tasdiqlanadi.
        return

    await query.answer()

# --- Sozlamalar bo'limi callback'i (til/ism/telefon o'zgartirish) ---
async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    lang = context.user_data.get("lang")
    if not lang:
        saved_user = get_user(query.from_user.id)
        lang = saved_user.get("lang", "uz_latin") if saved_user else "uz_latin"
        context.user_data["lang"] = lang

    data = query.data

    if data == "stg_lang":
        context.user_data["changing_language"] = True
        await query.answer()
        await query.message.reply_text(
            TEXTS[lang]["settings_choose_new_lang"],
            reply_markup=language_keyboard(),
        )
        return

    if data == "stg_name":
        context.user_data["awaiting_name_change"] = True
        await query.answer()
        await query.message.reply_text(TEXTS[lang]["settings_ask_new_name"])
        return

    if data == "stg_phone":
        context.user_data["awaiting_phone_change"] = True
        await query.answer()
        await query.message.reply_text(
            TEXTS[lang]["settings_ask_new_phone"],
            reply_markup=phone_keyboard(lang),
        )
        return

    await query.answer()

# =========================================================
# ============ ADMIN PANEL (tugma ranglari) ==============
# =========================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- Hali userlarga yuborilmagan o'zgarishlar ro'yxati ---
# ("Saqlash" bosilmaguncha xotirada turadi)
PENDING_CHANGES: set[str] = set()

# --- Admin panel asosiy ro'yxati ---
def admin_panel_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key in BUTTON_KEYS:
        current_style = get_button_style(key)
        style_emoji = STYLE_LABELS.get(current_style, "⚪ Standart").split(" ")[0]
        dot = " 🔸" if key in PENDING_CHANGES else ""
        label = f"{style_emoji} {BUTTON_ADMIN_LABELS[key]}{dot}"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin_pick_{key}")])

    if PENDING_CHANGES:
        rows.append([
            InlineKeyboardButton(
                f"💾 Saqlash va yuborish ({len(PENDING_CHANGES)} ta o'zgarish)",
                callback_data="admin_save",
            )
        ])
    rows.append([InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin_home")])
    return InlineKeyboardMarkup(rows)

# --- Valyutalarni boshqarish paneli ---
def admin_currencies_keyboard() -> InlineKeyboardMarkup:
    currencies = load_currencies()
    rows = []
    for currency in currencies:
        give_style = currency.get("give_style", "default")
        take_style = currency.get("take_style", "default")
        give_emoji = STYLE_LABELS.get(give_style, "⚪ Standart").split(" ")[0]
        take_emoji = STYLE_LABELS.get(take_style, "⚪ Standart").split(" ")[0]

        rows.append([
            InlineKeyboardButton(
                f"{give_emoji} 🔷 {currency['name']}",
                callback_data=f"admin_curr_side_{currency['id']}_give",
            ),
            InlineKeyboardButton(
                f"{take_emoji} 🔶 {currency['name']}",
                callback_data=f"admin_curr_side_{currency['id']}_take",
            ),
        ])

    if currencies:
        rows.append([InlineKeyboardButton("🗑 O'chirish", callback_data="admin_currdelmenu")])
    rows.append([InlineKeyboardButton("➕ Valyuta qo'shish", callback_data="admin_curr_add")])
    rows.append([InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin_home")])
    return InlineKeyboardMarkup(rows)

# --- O'chirish uchun valyuta tanlash paneli ---
def admin_currencies_delete_keyboard() -> InlineKeyboardMarkup:
    currencies = load_currencies()
    rows = []
    for currency in currencies:
        rows.append([InlineKeyboardButton(currency["name"], callback_data=f"admin_curr_del_{currency['id']}")])
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_curr_home")])
    return InlineKeyboardMarkup(rows)

# --- Bitta valyuta + tomon uchun rang tanlash klaviaturasi ---
def currency_color_choice_keyboard(currency_id: str, side: str) -> InlineKeyboardMarkup:
    rows = []
    for style_value, style_label in STYLE_OPTIONS:
        rows.append([InlineKeyboardButton(style_label, callback_data=f"admin_curr_set_{currency_id}_{side}_{style_value}")])
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_curr_home")])
    return InlineKeyboardMarkup(rows)

# --- Bitta tugma uchun rang tanlash klaviaturasi ---
def color_choice_keyboard(key: str) -> InlineKeyboardMarkup:
    rows = []
    for style_value, style_label in STYLE_OPTIONS:
        rows.append([InlineKeyboardButton(style_label, callback_data=f"admin_set_{key}_{style_value}")])
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(rows)

# --- Admin bosh menyusi (ranglar / valyutalar / boshqa tugmalar) ---
def admin_home_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🎨 Menyu tugmalari rangi", callback_data="admin_colors")],
        [InlineKeyboardButton("💱 Valyutalar ro'yxati", callback_data="admin_curr_home")],
        [InlineKeyboardButton("🌐 Til / Boshqa tugmalar", callback_data="admin_inl_home")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Til/Boshqa (inline) tugmalar ro'yxati ---
def admin_inline_buttons_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for key in INLINE_BUTTON_KEYS:
        current_style = get_button_style(key)
        style_emoji = STYLE_LABELS.get(current_style, "⚪ Standart").split(" ")[0]
        label = f"{style_emoji} {INLINE_BUTTON_ADMIN_LABELS[key]}"
        rows.append([InlineKeyboardButton(label, callback_data=f"admin_inl_pick_{key}")])
    rows.append([InlineKeyboardButton("⬅️ Admin menyu", callback_data="admin_home")])
    return InlineKeyboardMarkup(rows)

# --- Til/Boshqa tugma uchun rang tanlash klaviaturasi ---
def inline_color_choice_keyboard(key: str) -> InlineKeyboardMarkup:
    rows = []
    for style_value, style_label in STYLE_OPTIONS:
        rows.append([InlineKeyboardButton(style_label, callback_data=f"admin_inl_set_{key}_{style_value}")])
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_inl_home")])
    return InlineKeyboardMarkup(rows)

# --- /admin komandasi ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Sizda admin panelga kirish huquqi yo'q.")
        return

    await update.message.reply_text(
        "🛠 Admin panel\n\nBo'limni tanlang:",
        reply_markup=admin_home_keyboard(),
    )

# --- Admin panel callback'lari ---
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ Ruxsat yo'q.", show_alert=True)
        return

    data = query.data

    if data == "admin_home":
        await query.answer()
        await query.edit_message_text(
            "🛠 Admin panel\n\nBo'limni tanlang:",
            reply_markup=admin_home_keyboard(),
        )
        return

    if data == "admin_inl_home":
        await query.answer()
        await query.edit_message_text(
            "🌐 Til / Boshqa tugmalar\n\n"
            "Bu tugmalar avtomatik yangilanadi - rang darhol qo'llanadi, "
            "\"Saqlash\" tugmasi kerak emas.\n\n"
            "O'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_inline_buttons_keyboard(),
        )
        return

    if data.startswith("admin_inl_pick_"):
        key = data.replace("admin_inl_pick_", "")
        if key not in INLINE_BUTTON_KEYS:
            await query.answer()
            return
        await query.answer()
        current_style = get_button_style(key)
        current_label = STYLE_LABELS.get(current_style, "⚪ Standart")
        await query.edit_message_text(
            f"🎨 {INLINE_BUTTON_ADMIN_LABELS[key]}\n"
            f"Joriy rang: {current_label}\n\n"
            f"Yangi rangni tanlang:",
            reply_markup=inline_color_choice_keyboard(key),
        )
        return

    if data.startswith("admin_inl_set_"):
        # format: admin_inl_set_<key>_<style>
        remainder = data.replace("admin_inl_set_", "")
        key, style = remainder.rsplit("_", 1)
        if key not in INLINE_BUTTON_KEYS or style not in STYLE_LABELS:
            await query.answer()
            return

        set_button_style(key, style)
        # Diqqat: bu yerda PENDING_CHANGES ga QO'SHILMAYDI va broadcast ISHGA TUSHMAYDI -
        # chunki bu inline tugmalar har safar yangidan chiqariladi, reply-menyu emas.

        await query.answer(f"✅ {INLINE_BUTTON_ADMIN_LABELS[key]} rangi o'zgartirildi")
        await query.edit_message_text(
            "🌐 Til / Boshqa tugmalar\n\n"
            "O'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_inline_buttons_keyboard(),
        )
        return

    if data.startswith("admin_reply_"):
        target_user_id_str = data.replace("admin_reply_", "")
        if not target_user_id_str.isdigit():
            await query.answer()
            return
        context.user_data["awaiting_reply_to"] = int(target_user_id_str)
        await query.answer()
        await query.message.reply_text("✍️ Javobingizni yozing:")
        return

    if data == "admin_colors":
        await query.answer()
        await query.edit_message_text(
            "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if data == "admin_back":
        await query.answer()
        await query.edit_message_text(
            "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if data.startswith("admin_pick_"):
        key = data.replace("admin_pick_", "")
        if key not in BUTTON_KEYS:
            await query.answer()
            return
        await query.answer()
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
            await query.answer()
            return

        set_button_style(key, style)
        PENDING_CHANGES.add(key)  # userlarga hali yuborilmagan, "Saqlash" kutilmoqda

        # Callback so'roviga FAQAT BIR MARTA javob beramiz
        await query.answer(f"✅ {BUTTON_ADMIN_LABELS[key]} rangi o'zgartirildi (mahalliy)")
        await query.edit_message_text(
            "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_panel_keyboard(),
        )
        return

    if data == "admin_save":
        if not PENDING_CHANGES:
            await query.answer("Saqlanadigan o'zgarish yo'q.", show_alert=True)
            return

        changed_keys = list(PENDING_CHANGES)
        PENDING_CHANGES.clear()

        # Callback so'roviga FAQAT BIR MARTA javob beramiz
        await query.answer("📤 Yuborilmoqda...")
        await query.edit_message_text(
            "🎨 Tugmalar rangini boshqarish\n\nO'zgartirmoqchi bo'lgan tugmani tanlang:",
            reply_markup=admin_panel_keyboard(),
        )

        # Barcha ro'yxatdan o'tgan foydalanuvchilarga BIR MARTA yangilangan menyuni yuboramiz
        asyncio.create_task(broadcast_menu_update(context, changed_keys))
        return

    if data == "admin_curr_home":
        await query.answer()
        currencies = load_currencies()
        text = "💱 Valyutalar ro'yxati:" if currencies else "💱 Valyutalar ro'yxati hozircha bo'sh."
        await query.edit_message_text(text, reply_markup=admin_currencies_keyboard())
        return

    if data == "admin_currdelmenu":
        await query.answer()
        currencies = load_currencies()
        if not currencies:
            await query.edit_message_text(
                "💱 Valyutalar ro'yxati hozircha bo'sh.",
                reply_markup=admin_currencies_keyboard(),
            )
            return
        await query.edit_message_text(
            "🗑 Qaysi valyutani o'chirmoqchisiz?",
            reply_markup=admin_currencies_delete_keyboard(),
        )
        return

    if data.startswith("admin_curr_side_"):
        # format: admin_curr_side_<id>_<give|take>
        remainder = data.replace("admin_curr_side_", "")
        currency_id, side = remainder.rsplit("_", 1)
        if side not in ("give", "take"):
            await query.answer()
            return

        currencies = load_currencies()
        currency = next((c for c in currencies if c["id"] == currency_id), None)
        if not currency:
            await query.answer("Topilmadi", show_alert=True)
            return

        await query.answer()
        field = "give_style" if side == "give" else "take_style"
        current_style = currency.get(field, "default")
        current_label = STYLE_LABELS.get(current_style, "⚪ Standart")
        side_label = "🔷 Berish" if side == "give" else "🔶 Olish"
        await query.edit_message_text(
            f"🎨 {currency['name']} — {side_label}\n"
            f"Joriy rang: {current_label}\n\n"
            f"Yangi rangni tanlang:",
            reply_markup=currency_color_choice_keyboard(currency_id, side),
        )
        return

    if data.startswith("admin_curr_set_"):
        # format: admin_curr_set_<id>_<give|take>_<style>
        remainder = data.replace("admin_curr_set_", "")
        currency_id, side, style = remainder.rsplit("_", 2)
        if side not in ("give", "take") or style not in STYLE_LABELS:
            await query.answer()
            return

        ok = set_currency_style(currency_id, side, style)
        await query.answer("✅ Rang o'zgartirildi" if ok else "Topilmadi")

        currencies = load_currencies()
        text = "💱 Valyutalar ro'yxati:" if currencies else "💱 Valyutalar ro'yxati hozircha bo'sh."
        await query.edit_message_text(text, reply_markup=admin_currencies_keyboard())
        return

    if data.startswith("admin_curr_del_"):
        currency_id = data.replace("admin_curr_del_", "")
        removed = remove_currency(currency_id)
        await query.answer("✅ O'chirildi" if removed else "Topilmadi")
        currencies = load_currencies()
        text = "💱 Valyutalar ro'yxati:" if currencies else "💱 Valyutalar ro'yxati hozircha bo'sh."
        await query.edit_message_text(text, reply_markup=admin_currencies_keyboard())
        return

    if data == "admin_curr_add":
        await query.answer()
        context.user_data["awaiting_currency_name"] = True
        await query.message.reply_text(
            "✍️ Yangi valyuta nomini yozing (masalan: USDT (Trc20)):"
        )
        return

    if data.startswith("admin_curr_cat_"):
        category = data.replace("admin_curr_cat_", "")  # "fiat" yoki "crypto"
        if category not in ("fiat", "crypto"):
            await query.answer()
            return

        name = context.user_data.pop("pending_currency_name", None)
        if not name:
            await query.answer("Xatolik: nom topilmadi, qaytadan urinib ko'ring.", show_alert=True)
            return

        add_currency(name, category)
        cat_label = "💵 Fiat" if category == "fiat" else "🪙 Kripto"
        await query.answer(f"✅ '{name}' ({cat_label}) qo'shildi!")
        await query.edit_message_text(
            "💱 Valyutalar ro'yxati:",
            reply_markup=admin_currencies_keyboard(),
        )
        return

    # Noma'lum callback - baribir javob berib qo'yamiz, aks holda Telegramda "yuklanmoqda" tursib qoladi
    await query.answer()

# --- Yangilangan menyuni barcha foydalanuvchilarga yuborish ---
async def broadcast_menu_update(context: ContextTypes.DEFAULT_TYPE, changed_keys: list) -> None:
    users = load_users()
    update_texts = {
        "uz_latin": "🔄 Menyu yangilandi:",
        "uz_cyrillic": "🔄 Меню янгиланди:",
    }

    sent = 0
    failed = 0
    for user_id_str, info in users.items():
        lang = info.get("lang", "uz_latin")
        try:
            await context.bot.send_message(
                chat_id=int(user_id_str),
                text=update_texts.get(lang, update_texts["uz_latin"]),
                reply_markup=main_menu_keyboard(lang),
            )
            sent += 1
        except Exception:
            # Foydalanuvchi botni bloklagan yoki boshqa xatolik - o'tkazib yuboramiz
            failed += 1
        # Telegramning flood-limitiga tegib qolmaslik uchun kichik pauza
        await asyncio.sleep(0.05)

    logger.info(f"Menyu yangilanishi yuborildi: {sent} ta muvaffaqiyatli, {failed} ta xato")

# --- Asosiy funksiya ---
def main() -> None:
    TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"  # <-- shu yerga o'z tokeningizni kiriting

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(exchange_callback, pattern="^exch_"))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^stg_"))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
