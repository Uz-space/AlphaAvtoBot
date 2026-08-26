"""
Referral Telegram Bot (aiogram 3.x)
-----------------------------------------------------------
Oqim:
  1. /start -> guruh/kanalga a'zolik tekshiriladi
  2. A'zolik tasdiqlansa -> telefon raqam so'raladi
  3. Telefon raqam kiritilsa -> asosiy menyu (doimiy pastki tugmalar) ochiladi

Asosiy menyu tugmalari:
  - Pul ishlash        -> referal havola (izoh + ogohlantirish + Ulashish tugmasi)
  - Pulni yechish       -> ALPHA hamyon manzili va summa yuboradi
  - Hisobim             -> shaxsiy statistika
  - Qo'llab Quvvatlash  -> murojaat yuborish (adminlarga forward qilinadi)
  - To'lovlar           -> to'lovlar kanaliga havola

Admin panel (/admin):
  - Statistika
  - Guruh/Kanal qo'shish (majburiy a'zolik)
  - Minimal yechish summasini o'zgartirish (ALPHA)
  - Referal bonusini o'zgartirish (ALPHA)
  - To'lovlar kanali havolasini o'zgartirish
  - Yechish so'rovlarini tasdiqlash/rad etish

Formatlash: MarkdownV2 (to'lovlar kanaliga yuboriladigan formatdek).

Vaqt zonasi: barcha ko'rsatiladigan vaqtlar Toshkent (UTC+5) bo'yicha,
serverning qaysi vaqt zonasida ishlashidan qat'iy nazar.

Ishga tushirish:
    pip install -r requirements.txt
    pastdagi BOT_TOKEN va ADMIN_IDS ni to'g'irlang
    python bot.py
"""

import asyncio
import logging
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

import aiosqlite
import aiohttp

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, CopyTextButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramMigrateToChat

# =========================================================
# KONFIGURATSIYA - bu yerga o'zingizning ma'lumotlaringizni yozing
# =========================================================

BOT_TOKEN = "8749302193:AAFOeDLDoimdjHSVDO728nAtsBngqncy8Uk"   # @BotFather'dan olgan tokeningiz
ADMIN_IDS = [8758410535, 7029627367]                   # sizning Telegram user_id'ingiz (bir nechtasi: [111111111, 222222222])

DB_PATH = "refbot.db"

# Toshkent vaqt zonasi (UTC+5) - server qaysi vaqt zonasida ishlashidan qat'iy nazar
# barcha foydalanuvchiga ko'rinadigan vaqtlar shu zona bo'yicha hisoblanadi
TASHKENT_TZ = timezone(timedelta(hours=5))

logging.basicConfig(level=logging.INFO)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def md_code(text) -> str:
    """Kod bloki (` yoki ```) ichidagi matn uchun escape (faqat ` va \\ escape qilinadi)."""
    if text is None:
        return ""
    return str(text).replace("\\", "\\\\").replace("`", "\\`")


def card(body: str) -> str:
    """Matnni to'lovlar kanalidagi kabi monospace 'karta' (kod bloki) ko'rinishida qaytaradi."""
    return "```\n" + md_code(body) + "\n```"


def fmt_money(value: float) -> str:
    """0.00150000 -> '0.0015' (ortiqcha nollarni olib tashlab, ALPHA formatida ko'rsatadi)"""
    formatted = f"{float(value):.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def now_str() -> str:
    """Toshkent (UTC+5) vaqti bo'yicha joriy sana/vaqtni qaytaradi."""
    return datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y | %H:%M")


def format_channel_announcement(tx_type: str, username: str, user_id: int, amount: float, asset: str = "ALPHA") -> str:
    username_display = "@" + username if username else "N/A"
    date_str = datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M")
    return (
        "TYPE: " + tx_type + "\n\n"
        "USERNAME: " + username_display + "\n"
        "ID: " + str(user_id) + "\n\n"
        "ASSET: " + asset + "\n"
        "AMOUNT: " + fmt_money(amount) + " " + asset + "\n\n"
        "STATUS: COMPLETED\n"
        "DATE: " + date_str
    )


# =========================================================
# MA'LUMOTLAR BAZASI
# =========================================================

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    phone_number TEXT,
    referrer_id INTEGER,
    balance REAL DEFAULT 0,
    total_withdrawn REAL DEFAULT 0,
    verified INTEGER DEFAULT 0,
    referral_credited INTEGER DEFAULT 0,
    joined_at TEXT DEFAULT (datetime('now')),
    last_active_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS required_chats (
    chat_id INTEGER PRIMARY KEY,
    title TEXT,
    invite_link TEXT,
    type TEXT
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    wallet_address TEXT,
    network TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now')),
    processed_at TEXT
);

CREATE TABLE IF NOT EXISTS withdrawal_networks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS support_threads (
    admin_id INTEGER,
    message_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (admin_id, message_id)
);
"""

DEFAULT_SETTINGS = {
    "referral_bonus": "0.001",
    "min_withdrawal": "0.01",
    "payments_channel_url": "",
    "alpha_usd_rate": "0.01",
}


async def init_db():
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.executescript(CREATE_TABLES_SQL)
        # Eski bazalarda "last_active_at" ustuni bo'lmasligi mumkin - xavfsiz qo'shamiz
        try:
            await conn.execute(
                "ALTER TABLE users ADD COLUMN last_active_at TEXT DEFAULT (datetime('now'))"
            )
        except Exception:
            pass
        # Eski bazalarda "network" ustuni bo'lmasligi mumkin - xavfsiz qo'shamiz
        try:
            await conn.execute("ALTER TABLE withdrawals ADD COLUMN network TEXT")
        except Exception:
            pass
        try:
            await conn.execute("ALTER TABLE withdrawals ADD COLUMN crypto_amount REAL")
        except Exception:
            pass
        try:
            await conn.execute("ALTER TABLE withdrawals ADD COLUMN usd_value REAL")
        except Exception:
            pass
        for key, value in DEFAULT_SETTINGS.items():
            await conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        await conn.commit()


# ---------- USERS ----------

async def add_user_if_not_exists(user_id: int, username: str, full_name: str, referrer_id):
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if await cur.fetchone():
            return False
        if referrer_id == user_id:
            referrer_id = None
        await conn.execute(
            "INSERT INTO users (user_id, username, full_name, referrer_id) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, referrer_id),
        )
        await conn.commit()
        return True


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def set_verified(user_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET verified = 1 WHERE user_id = ?", (user_id,))
        await conn.commit()


async def touch_last_active(user_id: int):
    """Foydalanuvchi botga har qanday xabar/tugma orqali murojaat qilganda
    'last_active_at' vaqtini yangilaydi - shu orqali 'faol foydalanuvchilar' hisoblanadi."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET last_active_at = datetime('now') WHERE user_id = ?", (user_id,)
        )
        await conn.commit()


async def set_phone(user_id: int, phone_number: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET phone_number = ? WHERE user_id = ?", (phone_number, user_id)
        )
        await conn.commit()


async def credit_referral_if_needed(user_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT referrer_id, referral_credited FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cur.fetchone()
        if not row or not row["referrer_id"] or row["referral_credited"]:
            return None

        referrer_id = row["referrer_id"]
        cur = await conn.execute("SELECT value FROM settings WHERE key = 'referral_bonus'")
        setting = await cur.fetchone()
        bonus = float(setting[0]) if setting else 1000

        await conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bonus, referrer_id))
        await conn.execute("UPDATE users SET referral_credited = 1 WHERE user_id = ?", (user_id,))
        await conn.commit()
        return referrer_id, bonus


async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else 0.0


async def count_referrals(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id = ? AND referral_credited = 1", (user_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0


# ---------- REQUIRED CHATS ----------

async def add_required_chat(chat_id: int, title: str, invite_link: str, chat_type: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO required_chats (chat_id, title, invite_link, type) VALUES (?, ?, ?, ?)",
            (chat_id, title, invite_link, chat_type),
        )
        await conn.commit()


async def migrate_required_chat_id(old_chat_id: int, new_chat_id: int):
    """Oddiy guruh supergroup'ga aylanganda Telegram yangi chat_id beradi.
    Bazadagi eski ID'ni yangisiga avtomatik almashtiradi (o'z-o'zini tuzatish)."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE OR REPLACE required_chats SET chat_id = ? WHERE chat_id = ?",
            (new_chat_id, old_chat_id),
        )
        await conn.commit()


async def get_required_chats():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM required_chats")
        return await cur.fetchall()


# ---------- WITHDRAWALS / KRIPTOVALYUTALAR ----------

# Qo'llab-quvvatlanadigan kriptovalyutalar -> CoinGecko API identifikatori
SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "LTC": "litecoin",
    "TRX": "tron",
    "DOGE": "dogecoin",
    "USDT": "tether",
    "TON": "the-open-network",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "NOT": "notcoin",
}


async def get_crypto_usd_price(symbol: str):
    """Berilgan kriptovalyutaning HOZIRGI USD narxini CoinGecko API orqali oladi.
    Xatolik yoki tarmoq muammosi bo'lsa None qaytaradi (chaqiruvchi tomon buni tekshirishi shart)."""
    coingecko_id = SYMBOL_TO_COINGECKO_ID.get(symbol.upper())
    if not coingecko_id:
        return None
    url = "https://api.coingecko.com/api/v3/simple/price"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, params={"ids": coingecko_id, "vs_currencies": "usd"}) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return float(data[coingecko_id]["usd"])
    except Exception:
        return None


async def get_withdrawal_networks():
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM withdrawal_networks ORDER BY id ASC")
        return await cur.fetchall()


async def add_withdrawal_network(name: str) -> bool:
    """Yangi kriptovalyuta qo'shadi. Nomi tanish (SYMBOL_TO_COINGECKO_ID) bo'lishi,
    allaqachon 10 tadan kam bo'lishi va takrorlanmasligi shart."""
    symbol = name.upper()
    if symbol not in SYMBOL_TO_COINGECKO_ID:
        return False
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT COUNT(*) FROM withdrawal_networks")
        (count,) = await cur.fetchone()
        if count >= 10:
            return False
        try:
            await conn.execute("INSERT INTO withdrawal_networks (name) VALUES (?)", (symbol,))
            await conn.commit()
            return True
        except aiosqlite.IntegrityError:
            return False


async def remove_withdrawal_network(network_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("DELETE FROM withdrawal_networks WHERE id = ?", (network_id,))
        await conn.commit()


async def create_withdrawal(
    user_id: int, amount: float, wallet_address: str, network: str = None,
    crypto_amount: float = None, usd_value: float = None,
) -> int:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        cur = await conn.execute(
            "INSERT INTO withdrawals (user_id, amount, wallet_address, network, crypto_amount, usd_value) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, amount, wallet_address, network, crypto_amount, usd_value),
        )
        await conn.commit()
        return cur.lastrowid


async def get_withdrawal(withdrawal_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        return await cur.fetchone()


async def update_withdrawal_status(withdrawal_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE withdrawals SET status = ?, processed_at = datetime('now') WHERE id = ?",
            (status, withdrawal_id),
        )
        await conn.commit()


async def refund_withdrawal(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await conn.commit()


async def mark_withdrawn(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "UPDATE users SET total_withdrawn = total_withdrawn + ? WHERE user_id = ?", (amount, user_id)
        )
        await conn.commit()


# ---------- SETTINGS / STATS ----------

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await conn.commit()


async def get_setting(key: str, default=None):
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-7 days')"
        )
        users_7_days = (await cur.fetchone())[0]

        cur = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE joined_at >= datetime('now', '-30 days')"
        )
        users_30_days = (await cur.fetchone())[0]

        cur = await conn.execute(
            "SELECT COUNT(*) FROM users WHERE last_active_at >= datetime('now', '-1 day')"
        )
        active_users = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "users_7_days": users_7_days,
            "users_30_days": users_30_days,
            "active_users": active_users,
        }


async def get_all_user_ids():
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute("SELECT user_id FROM users")
        rows = await cur.fetchall()
        return [row[0] for row in rows]


async def save_support_thread(admin_id: int, message_id: int, user_id: int):
    """Adminga yuborilgan murojaat xabarining ID'sini foydalanuvchi ID'siga bog'lab
    saqlaydi - admin shu xabarga \"Reply\" qilsa, javob to'g'ri userga yuborilishi uchun."""
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO support_threads (admin_id, message_id, user_id) VALUES (?, ?, ?)",
            (admin_id, message_id, user_id),
        )
        await conn.commit()


async def get_support_thread_user(admin_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as conn:
        cur = await conn.execute(
            "SELECT user_id FROM support_threads WHERE admin_id = ? AND message_id = ?",
            (admin_id, message_id),
        )
        row = await cur.fetchone()
        return row[0] if row else None


# =========================================================
# KLAVIATURALAR
# =========================================================

MENU_PUL_ISHLASH = "Pul ishlash"
MENU_PULNI_YECHISH = "Pulni yechish"
MENU_HISOBIM = "Hisobim"
MENU_SUPPORT = "Qo'llab Quvvatlash"
MENU_TOLOVLAR = "To'lovlar"
MENU_ORQAGA = "Orqaga"


def main_menu_reply_kb():
    kbb = ReplyKeyboardBuilder()
    kbb.button(text=MENU_PUL_ISHLASH, style="success")
    kbb.button(text=MENU_HISOBIM, style="primary")
    kbb.button(text=MENU_SUPPORT, style="danger")
    kbb.button(text=MENU_TOLOVLAR, style="danger")
    kbb.adjust(1, 1, 2)
    return kbb.as_markup(resize_keyboard=True)


def phone_request_kb():
    kbb = ReplyKeyboardBuilder()
    kbb.button(text="Telefon raqamni yuborish", request_contact=True, style="success")
    kbb.adjust(1)
    return kbb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def back_reply_kb():
    kbb = ReplyKeyboardBuilder()
    kbb.button(text=MENU_ORQAGA, style="danger")
    kbb.adjust(1)
    return kbb.as_markup(resize_keyboard=True)


def check_membership_kb(required_chats):
    kbb = InlineKeyboardBuilder()
    for chat in required_chats:
        chat_title = chat["title"]
        chat_link = chat["invite_link"]
        if chat_link:
            kbb.button(text=chat_title, url=chat_link)
    kbb.button(text="Tekshirish", callback_data="check_membership", style="success")
    kbb.adjust(1)
    return kbb.as_markup()


def share_kb(ref_link: str, share_text: str):
    kbb = InlineKeyboardBuilder()
    share_url = "https://t.me/share/url?url=" + quote(ref_link) + "&text=" + quote(share_text)
    kbb.button(text="Havolani nusxalash", copy_text=CopyTextButton(text=ref_link), style="success")
    kbb.button(text="Ulashish", url=share_url, style="success")
    kbb.adjust(1)
    return kbb.as_markup()


def hisobim_withdraw_kb():
    kbb = InlineKeyboardBuilder()
    kbb.button(text="Pulni yechish", callback_data="start_withdraw", style="primary")
    kbb.adjust(1)
    return kbb.as_markup()


def payments_channel_kb(url: str):
    kbb = InlineKeyboardBuilder()
    kbb.button(text="To'lovlar kanali", url=url, style="danger")
    kbb.adjust(1)
    return kbb.as_markup()


def cancel_inline_kb():
    kbb = InlineKeyboardBuilder()
    kbb.button(text="Bekor qilish", callback_data="cancel_action")
    kbb.adjust(1)
    return kbb.as_markup()


# ---------- ADMIN ----------

ADMIN_MENU_STATS = "Statistika"
ADMIN_MENU_CHANNELS = "Kanal va Guruhlar"
ADMIN_MENU_BROADCAST = "Xabar yuborish"
ADMIN_MENU_NETWORKS = "Kriptovalyutalar"
ADMIN_MENU_PAYMENT_SETTINGS = "ALPHA"
ADMIN_MENU_CANCEL = "Bekor qilish"

# Barcha doimiy menyu tugmalari (user + admin) - FSM oqimlari ichida bularni "matn" deb
# noto'g'ri qabul qilmaslik uchun ishlatiladi
RESERVED_MENU_TEXTS = {
    MENU_PUL_ISHLASH,
    MENU_PULNI_YECHISH,
    MENU_HISOBIM,
    MENU_SUPPORT,
    MENU_TOLOVLAR,
    MENU_ORQAGA,
    ADMIN_MENU_PAYMENT_SETTINGS,
    ADMIN_MENU_CANCEL,
}


async def is_reserved_menu_text(message: Message, state: FSMContext) -> bool:
    """Agar foydalanuvchi FSM oqimi ichida bo'lib, biror menyu tugmasini bossa,
    oqimni bekor qilib, foydalanuvchini asosiy menyuga qaytaradi."""
    if (message.text or "") not in RESERVED_MENU_TEXTS:
        return False
    await state.clear()
    await message.answer(
        card("Avvalgi amal bekor qilindi. Tugmani qayta bosing."),
        reply_markup=main_menu_reply_kb() if not is_admin(message.from_user.id) else admin_menu_reply_kb(),
    )
    return True

# "To'lov Sozlamalari" ichidagi pastki tugmalar
PAYSET_SUB_BONUS = "Referal bonusi"
PAYSET_SUB_MIN_WITHDRAWAL = "Minimal yechish summasi"
PAYSET_SUB_PAYMENTS_CHANNEL = "To'lovlar kanali havolasi"
PAYSET_SUB_RATE = "1 ALPHA narxi (USD)"


def admin_menu_reply_kb():
    kbb = ReplyKeyboardBuilder()
    kbb.button(text=ADMIN_MENU_PAYMENT_SETTINGS, style="danger")
    kbb.adjust(1)
    return kbb.as_markup(resize_keyboard=True)


def payment_settings_submenu_kb():
    kbb = InlineKeyboardBuilder()
    kbb.button(text=ADMIN_MENU_STATS, callback_data="payset_stats", style="primary")
    kbb.button(text=ADMIN_MENU_CHANNELS, callback_data="payset_addchat", style="primary")
    kbb.button(text=ADMIN_MENU_BROADCAST, callback_data="payset_broadcast", style="primary")
    kbb.button(text=ADMIN_MENU_NETWORKS, callback_data="payset_networks", style="primary")
    kbb.button(text=PAYSET_SUB_BONUS, callback_data="payset_bonus", style="primary")
    kbb.button(text=PAYSET_SUB_RATE, callback_data="payset_rate", style="primary")
    kbb.button(text=PAYSET_SUB_MIN_WITHDRAWAL, callback_data="payset_min", style="primary")
    kbb.button(text=PAYSET_SUB_PAYMENTS_CHANNEL, callback_data="payset_channel", style="danger")
    kbb.adjust(1)
    return kbb.as_markup()


def admin_cancel_reply_kb():
    kbb = ReplyKeyboardBuilder()
    kbb.button(text=ADMIN_MENU_CANCEL, style="danger")
    kbb.adjust(1)
    return kbb.as_markup(resize_keyboard=True)


def withdrawal_decision_kb(withdrawal_id: int):
    kbb = InlineKeyboardBuilder()
    kbb.button(text="Tasdiqlash", callback_data="wd_approve_" + str(withdrawal_id), style="success")
    kbb.button(text="Rad etish", callback_data="wd_reject_" + str(withdrawal_id), style="danger")
    kbb.adjust(2)
    return kbb.as_markup()


def networks_admin_kb(networks):
    kbb = InlineKeyboardBuilder()
    for net in networks:
        kbb.button(text="❌ " + net["name"], callback_data="delnet_" + str(net["id"]), style="danger")
    if len(networks) < 10:
        kbb.button(text="Kriptovalyuta qo'shish", callback_data="addnet", style="success")
    kbb.adjust(1)
    return kbb.as_markup()


def networks_choice_kb(networks):
    kbb = InlineKeyboardBuilder()
    for net in networks:
        kbb.button(text=net["name"], callback_data="widnet_" + str(net["id"]), style="primary")
    kbb.button(text="Bekor qilish", callback_data="cancel_action")
    kbb.adjust(1)
    return kbb.as_markup()


# =========================================================
# FSM HOLATLARI
# =========================================================

class RegFlow(StatesGroup):
    waiting_phone = State()


class Withdraw(StatesGroup):
    waiting_network = State()
    waiting_address = State()
    waiting_amount = State()


class Support(StatesGroup):
    waiting_message = State()


class SetSetting(StatesGroup):
    waiting_value = State()


class AddChat(StatesGroup):
    waiting_link = State()


class Broadcast(StatesGroup):
    waiting_message = State()


class AddNetwork(StatesGroup):
    waiting_name = State()


# =========================================================
# FOYDALANUVCHI ROUTERI
# =========================================================

user_router = Router()


def parse_start_payload(text: str):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    if payload.isdigit():
        return int(payload)
    if payload.startswith("ref_") and payload[4:].isdigit():
        return int(payload[4:])
    return None


async def notify_referrer_if_credited(bot: Bot, result):
    if result:
        referrer_id, bonus = result
        try:
            await bot.send_message(
                referrer_id,
                card(
                    "Sizning referal havolangiz orqali yangi a'zo qo'shildi!\n\n"
                    "BONUS: " + fmt_money(bonus) + " ALPHA\n"
                    "Hisobingizga qo'shildi.",
                ),
            )
        except TelegramBadRequest:
            pass


async def get_not_joined_chats(bot: Bot, user_id: int, required_chats):
    """Har bir majburiy guruh/kanal uchun foydalanuvchining HOZIRGI a'zolik holatini
    Telegram'dan real vaqtda tekshiradi (bazadagi eski 'verified' flagiga ishonmaydi).
    A'zo bo'lmagan yoki guruhdan chiqib ketgan chatlar ro'yxatini qaytaradi."""
    not_joined = []
    for chat in required_chats:
        chat_id = chat["chat_id"]
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(chat)
        except TelegramMigrateToChat as e:
            # Oddiy guruh supergroup'ga aylangan - yangi ID bilan bazani
            # tuzatib, shu yangi ID orqali tekshiruvni qaytadan bajaramiz.
            new_chat_id = e.migrate_to_chat_id
            await migrate_required_chat_id(chat_id, new_chat_id)
            try:
                member = await bot.get_chat_member(new_chat_id, user_id)
                if member.status in ("left", "kicked"):
                    not_joined.append(chat)
            except (TelegramBadRequest, TelegramForbiddenError):
                not_joined.append(chat)
        except (TelegramBadRequest, TelegramForbiddenError):
            not_joined.append(chat)
    return not_joined


async def start_registration_flow(message_or_cb, user_id: int, bot: Bot, state: FSMContext):
    """A'zolikni tekshiradi -> telefon so'raydi -> yoki asosiy menyuni ko'rsatadi."""
    required_chats = await get_required_chats()

    if required_chats:
        text = card(
            "Botdan foydalanish uchun quyidagilarga obuna bo'ling:\n\n"
            "Obuna bo'lgach, \"Tekshirish\" tugmasini bosing."
        )
        markup = check_membership_kb(required_chats)
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, reply_markup=markup)
        else:
            await message_or_cb.message.edit_text(text, reply_markup=markup)
        return

    await set_verified(user_id)
    await state.set_state(RegFlow.waiting_phone)
    await ask_phone_number(message_or_cb, bot)


async def ask_phone_number(message_or_cb, bot: Bot):
    text = card("Davom etish uchun telefon raqamingizni yuboring:")
    if isinstance(message_or_cb, Message):
        await message_or_cb.answer(text, reply_markup=phone_request_kb())
    else:
        await message_or_cb.message.answer(text, reply_markup=phone_request_kb())


async def show_main_menu(message: Message):
    await message.answer(
        card(
            "Pul ishlash biz bilan oson va tez!\n\n"
            "Botimizga qo'shiling va har bir do'stingizni taklif qilganingizda, darhol bonus pulini oling!\n\n"
            "Referal tizimi orqali pul ishlash imkoniyati - cheksiz!"
        ),
        reply_markup=main_menu_reply_kb(),
    )


@user_router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext):
    await state.clear()
    referrer_id = parse_start_payload(message.text or "")
    await add_user_if_not_exists(
        user_id=message.from_user.id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name,
        referrer_id=referrer_id,
    )
    user = await get_user(message.from_user.id)

    # Majburiy guruh/kanallar mavjud bo'lsa, foydalanuvchi ilgari a'zo bo'lgan
    # (bazada verified=1) bo'lsa ham, HOZIRGI a'zolik holatini qayta tekshiramiz.
    # Aks holda guruhdan chiqib ketgan foydalanuvchi ham botdan foydalanaveradi.
    required_chats = await get_required_chats()
    if required_chats:
        not_joined = await get_not_joined_chats(bot, message.from_user.id, required_chats)
        if not_joined:
            text = card(
                "Botdan foydalanish uchun quyidagilarga obuna bo'ling:\n\n"
                "Obuna bo'lgach, \"Tekshirish\" tugmasini bosing."
            )
            await message.answer(text, reply_markup=check_membership_kb(required_chats))
            return
        # Barcha majburiy chatlarga a'zo - verified flagini yangilab qo'yamiz
        await set_verified(message.from_user.id)
        user = await get_user(message.from_user.id)

    if user and user["verified"] and user["phone_number"]:
        await show_main_menu(message)
        return

    if user and user["verified"] and not user["phone_number"]:
        await state.set_state(RegFlow.waiting_phone)
        await ask_phone_number(message, bot)
        return

    await start_registration_flow(message, message.from_user.id, bot, state)


@user_router.callback_query(F.data == "check_membership")
async def check_membership(callback: CallbackQuery, bot: Bot, state: FSMContext):
    user_id = callback.from_user.id
    required_chats = await get_required_chats()

    not_joined_chats = await get_not_joined_chats(bot, user_id, required_chats)

    if not_joined_chats:
        titles = ", ".join(c["title"] for c in not_joined_chats)
        await callback.answer(
            "Siz hali quyidagilarga a'zo bo'lmagansiz: " + titles,
            show_alert=True,
        )
        return

    await set_verified(user_id)

    # Foydalanuvchi ilgari ro'yxatdan o'tib, telefon raqamini allaqachon saqlagan bo'lishi
    # mumkin (masalan guruhdan chiqib ketib, qayta obuna bo'lgan holat). Bunday holda
    # telefon raqamni qayta so'ramaymiz, to'g'ridan-to'g'ri asosiy menyuga qaytaramiz.
    user = await get_user(user_id)
    if user and user["phone_number"]:
        await state.clear()
        await callback.message.edit_text(card("Tabriklaymiz! Qaytadan xush kelibsiz."))
        await callback.message.answer(
            card("Asosiy menyuga qaytdingiz."),
            reply_markup=main_menu_reply_kb(),
        )
        return

    await callback.message.edit_text(card("Tabriklaymiz! Endi ro'yxatdan o'tishni yakunlaymiz."))
    await state.set_state(RegFlow.waiting_phone)
    await ask_phone_number(callback, bot)


@user_router.message(RegFlow.waiting_phone, F.contact)
async def receive_phone(message: Message, state: FSMContext, bot: Bot):
    contact = message.contact
    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(card("Iltimos, faqat o'zingizning telefon raqamingizni yuboring."))
        return

    await set_phone(message.from_user.id, contact.phone_number)
    await state.clear()

    result = await credit_referral_if_needed(message.from_user.id)
    await notify_referrer_if_credited(bot, result)

    await show_main_menu(message)


@user_router.message(RegFlow.waiting_phone)
async def receive_phone_invalid(message: Message, state: FSMContext):
    if await is_reserved_menu_text(message, state):
        return
    await message.answer(
        card("Iltimos, pastdagi tugma orqali telefon raqamingizni yuboring.")
    )


# ---------- ASOSIY MENYU: PUL ISHLASH ----------

async def ensure_ready(message: Message, bot: Bot, state: FSMContext) -> bool:
    """5 ta asosiy tugmadan biri bosilganda ishlatiladi. Foydalanuvchi /start bosmasdan
    to'g'ridan tugmani bossa ham (masalan eski menyu saqlanib qolgan bo'lsa), quyidagilarni
    tekshiradi:
      1. Foydalanuvchi bazada ro'yxatdan o'tganmi
      2. Majburiy guruh/kanal(lar)ga HOZIR ham a'zoligi bormi
      3. Telefon raqami saqlanganmi
    Har qanday shart bajarilmasa, foydalanuvchini kerakli qadamga yo'naltirib False qaytaradi."""
    user_id = message.from_user.id
    user = await get_user(user_id)
    if not user:
        await add_user_if_not_exists(
            user_id=user_id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            referrer_id=None,
        )
        user = await get_user(user_id)

    required_chats = await get_required_chats()
    if required_chats:
        not_joined = await get_not_joined_chats(bot, user_id, required_chats)
        if not_joined:
            await message.answer(
                card(
                    "Davom etish uchun quyidagilarga obuna bo'ling:\n\n"
                    "Obuna bo'lgach, \"Tekshirish\" tugmasini bosing."
                ),
                reply_markup=check_membership_kb(required_chats),
            )
            return False

    if not user["verified"]:
        await set_verified(user_id)
        user = await get_user(user_id)

    if not user["phone_number"]:
        await state.set_state(RegFlow.waiting_phone)
        await ask_phone_number(message, bot)
        return False

    return True


@user_router.message(F.text == MENU_PUL_ISHLASH)
async def menu_pul_ishlash(message: Message, bot: Bot, state: FSMContext):
    if not await ensure_ready(message, bot, state):
        return
    me = await bot.get_me()
    ref_link = "https://t.me/" + me.username + "?start=" + str(message.from_user.id)
    bonus = await get_setting("referral_bonus", "0.001")

    caption = card(
        "Referal uchun: " + fmt_money(float(bonus)) + " ALPHA\n\n"
        "ESLATMA: Bot faqat O'zbekiston (+998) raqamlariga ishlaydi. Boshqa davlatlarga ishlamaydi, hushyor bo'ling.",
    )
    share_text = "Pul ishlash uchun botga qo'shiling!"
    await message.answer(caption, reply_markup=share_kb(ref_link, share_text))


# ---------- ASOSIY MENYU: HISOBIM ----------

@user_router.message(F.text == MENU_HISOBIM)
async def menu_hisobim(message: Message, bot: Bot, state: FSMContext):
    if not await ensure_ready(message, bot, state):
        return
    user = await get_user(message.from_user.id)
    referrals_count = await count_referrals(message.from_user.id)
    username_display = ("@" + user["username"]) if user["username"] else "yo'q"

    text = card(
        "Username: " + username_display + "\n"
        "ID: " + str(message.from_user.id) + "\n"
        "Balans: " + fmt_money(user["balance"]) + " ALPHA\n"
        "Referal: " + str(referrals_count) + " ta",
    )
    await message.answer(text, reply_markup=hisobim_withdraw_kb())


# ---------- ASOSIY MENYU: PULNI YECHISH ----------

async def start_withdraw_flow(message: Message, state: FSMContext):
    balance = await get_balance(message.from_user.id)
    min_withdrawal = float(await get_setting("min_withdrawal", "0.01"))
    if balance < min_withdrawal:
        await message.answer(
            card(
                "Minimal yechish summasi " + fmt_money(min_withdrawal) + " ALPHA.\n"
                "Balansingiz: " + fmt_money(balance) + " ALPHA"
            )
        )
        return

    await state.set_state(Withdraw.waiting_amount)
    await message.answer(
        card(
            "Yechib olmoqchi bo'lgan summani kiriting (ALPHA).\n"
            "Balansingiz: " + fmt_money(balance) + " ALPHA\n"
            "Minimal: " + fmt_money(min_withdrawal) + " ALPHA"
        ),
        reply_markup=cancel_inline_kb(),
    )


@user_router.message(F.text == MENU_PULNI_YECHISH)
async def menu_pulni_yechish(message: Message, state: FSMContext, bot: Bot):
    if not await ensure_ready(message, bot, state):
        return
    await start_withdraw_flow(message, state)


@user_router.callback_query(F.data == "start_withdraw")
async def cb_start_withdraw(callback: CallbackQuery, state: FSMContext, bot: Bot):
    required_chats = await get_required_chats()
    if required_chats:
        not_joined = await get_not_joined_chats(bot, callback.from_user.id, required_chats)
        if not_joined:
            await callback.message.answer(
                card(
                    "Davom etish uchun quyidagilarga obuna bo'ling:\n\n"
                    "Obuna bo'lgach, \"Tekshirish\" tugmasini bosing."
                ),
                reply_markup=check_membership_kb(required_chats),
            )
            return

    balance = await get_balance(callback.from_user.id)
    min_withdrawal = float(await get_setting("min_withdrawal", "0.01"))
    if balance < min_withdrawal:
        await callback.answer(
            "Minimal yechish summasi " + fmt_money(min_withdrawal) + " ALPHA. "
            "Balansingiz: " + fmt_money(balance) + " ALPHA",
            show_alert=True,
        )
        return

    await state.set_state(Withdraw.waiting_amount)
    await callback.message.answer(
        card(
            "Yechib olmoqchi bo'lgan summani kiriting (ALPHA).\n"
            "Balansingiz: " + fmt_money(balance) + " ALPHA\n"
            "Minimal: " + fmt_money(min_withdrawal) + " ALPHA"
        ),
        reply_markup=cancel_inline_kb(),
    )


@user_router.message(Withdraw.waiting_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    if await is_reserved_menu_text(message, state):
        return
    try:
        amount = float(message.text.replace(" ", "").replace(",", "."))
    except ValueError:
        await message.answer(card("Iltimos, faqat raqam kiriting. Masalan: 0.015"))
        return

    balance = await get_balance(message.from_user.id)
    min_withdrawal = float(await get_setting("min_withdrawal", "0.01"))

    if amount < min_withdrawal:
        await message.answer(card("Minimal summa " + fmt_money(min_withdrawal) + " ALPHA."))
        return
    if amount > balance:
        await message.answer(card("Balansingizda yetarli mablag' yo'q. Balans: " + fmt_money(balance) + " ALPHA"))
        return

    await state.update_data(amount=amount)

    networks = await get_withdrawal_networks()
    if networks:
        await state.set_state(Withdraw.waiting_network)
        await message.answer(
            card("Qaysi kriptovalyutada olmoqchisiz?"),
            reply_markup=networks_choice_kb(networks),
        )
        return

    await state.set_state(Withdraw.waiting_address)
    await message.answer(
        card("Hamyon manzilingizni yuboring:"),
        reply_markup=cancel_inline_kb(),
    )


@user_router.callback_query(Withdraw.waiting_network, F.data.startswith("widnet_"))
async def withdraw_choose_network(callback: CallbackQuery, state: FSMContext):
    network_id = int(callback.data.split("_", 1)[1])
    networks = await get_withdrawal_networks()
    network_name = next((n["name"] for n in networks if n["id"] == network_id), None)
    if not network_name:
        await callback.answer("Bu kriptovalyuta endi mavjud emas.", show_alert=True)
        return

    await state.update_data(network=network_name)
    await state.set_state(Withdraw.waiting_address)
    await callback.message.answer(
        card(network_name + " hamyon manzilingizni yuboring:"),
        reply_markup=cancel_inline_kb(),
    )


@user_router.message(Withdraw.waiting_address)
async def withdraw_address(message: Message, state: FSMContext, bot: Bot):
    if await is_reserved_menu_text(message, state):
        return
    address = message.text.strip()
    if len(address) < 20:
        await message.answer(card("Bu hamyon manziliga o'xshamayapti. Qaytadan yuboring."))
        return

    data = await state.get_data()
    amount = data["amount"]
    network = data.get("network")

    # Balansni yana bir bor tekshiramiz (jarayon davomida o'zgargan bo'lishi mumkin)
    balance = await get_balance(message.from_user.id)
    if amount > balance:
        await state.clear()
        await message.answer(
            card("Balansingizda yetarli mablag' yo'q. Balans: " + fmt_money(balance) + " ALPHA"),
            reply_markup=main_menu_reply_kb(),
        )
        return

    usd_value = None
    crypto_amount = None
    if network:
        alpha_usd_rate = float(await get_setting("alpha_usd_rate", "0.01"))
        usd_value = amount * alpha_usd_rate
        price = await get_crypto_usd_price(network)
        if price is None or price <= 0:
            await message.answer(
                card(
                    network + " narxini olishda xatolik yuz berdi. "
                    "Iltimos, birozdan so'ng qaytadan urinib ko'ring."
                ),
                reply_markup=main_menu_reply_kb(),
            )
            await state.clear()
            return
        crypto_amount = usd_value / price

    await state.clear()
    withdrawal_id = await create_withdrawal(
        message.from_user.id, amount, address, network, crypto_amount, usd_value
    )

    if network:
        confirm_text = (
            "SUMMA: " + fmt_money(amount) + " ALPHA (~" + fmt_money(usd_value) + " USD)\n"
            "KRIPTOVALYUTA: " + network + "\n"
            "MIQDOR: " + f"{crypto_amount:.8f}".rstrip("0").rstrip(".") + " " + network + "\n"
            "HAMYON: " + address + "\n\n"
            "Admin tasdiqlagach, mablag' yuboriladi."
        )
        admin_text = (
            "SO'ROV: #" + str(withdrawal_id) + "\n"
            "FOYDALANUVCHI: " + message.from_user.full_name + "\n"
            "ID: " + str(message.from_user.id) + "\n"
            "SUMMA: " + fmt_money(amount) + " ALPHA (~" + fmt_money(usd_value) + " USD)\n"
            "KRIPTOVALYUTA: " + network + "\n"
            "MIQDOR: " + f"{crypto_amount:.8f}".rstrip("0").rstrip(".") + " " + network + "\n"
            "HAMYON: " + address
        )
    else:
        confirm_text = (
            "HAMYON: " + address + "\n"
            "SUMMA: " + fmt_money(amount) + " ALPHA\n\n"
            "Admin tasdiqlagach, mablag' yuboriladi."
        )
        admin_text = (
            "SO'ROV: #" + str(withdrawal_id) + "\n"
            "FOYDALANUVCHI: " + message.from_user.full_name + "\n"
            "ID: " + str(message.from_user.id) + "\n"
            "HAMYON: " + address + "\n"
            "SUMMA: " + fmt_money(amount) + " ALPHA"
        )

    await message.answer(card(confirm_text), reply_markup=main_menu_reply_kb())

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                card(admin_text),
                reply_markup=withdrawal_decision_kb(withdrawal_id),
            )
        except TelegramBadRequest:
            pass


@user_router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(card("Bekor qilindi."))


# ---------- ASOSIY MENYU: QO'LLAB QUVVATLASH ----------

@user_router.message(F.text == MENU_SUPPORT)
async def menu_support(message: Message, state: FSMContext, bot: Bot):
    if not await ensure_ready(message, bot, state):
        return
    await state.set_state(Support.waiting_message)
    await message.answer(card("Murojaat matnini yuboring:"), reply_markup=back_reply_kb())


@user_router.message(Support.waiting_message, F.text == MENU_ORQAGA)
async def support_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(card("Asosiy menyuga qaytdingiz."), reply_markup=main_menu_reply_kb())


@user_router.message(Support.waiting_message)
async def support_receive(message: Message, state: FSMContext, bot: Bot):
    if await is_reserved_menu_text(message, state):
        return
    await state.clear()
    await message.answer(
        card("Murojaatingiz qabul qilindi. Tez orada javob beramiz."),
        reply_markup=main_menu_reply_kb(),
    )

    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(
                admin_id,
                card(
                    "FOYDALANUVCHI: " + message.from_user.full_name + "\n"
                    "ID: " + str(message.from_user.id) + "\n\n"
                    + (message.text or "(matn bo'lmagan xabar)"),
                ),
            )
            await save_support_thread(admin_id, sent.message_id, message.from_user.id)
        except TelegramBadRequest:
            pass


# ---------- ASOSIY MENYU: TO'LOVLAR ----------

@user_router.message(F.text == MENU_TOLOVLAR)
async def menu_tolovlar(message: Message, bot: Bot, state: FSMContext):
    if not await ensure_ready(message, bot, state):
        return
    channel_url = await get_setting("payments_channel_url", "")
    if not channel_url:
        await message.answer(card("Hozircha to'lovlar kanali sozlanmagan."))
        return
    try:
        await message.answer(
            card("Quyidagi kanalda siz botdan pul yechib olganlarni kuzatishingiz mumkin:"),
            reply_markup=payments_channel_kb(channel_url),
        )
    except TelegramBadRequest:
        # Saqlangan havola noto'g'ri formatda (masalan https:// siz yoki @username shaklida).
        # Foydalanuvchi javobsiz qolib ketmasligi uchun oddiy matn ko'rinishida yuboramiz.
        await message.answer(
            card(
                "To'lovlar kanali:\n\n"
                + channel_url
            )
        )


# ---------- ORQAGA (umumiy) ----------

@user_router.message(F.text == MENU_ORQAGA)
async def generic_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(card("Asosiy menyuga qaytdingiz."), reply_markup=main_menu_reply_kb())


# =========================================================
# ADMIN ROUTERI
# =========================================================

admin_router = Router()


def is_private_chat(message: Message) -> bool:
    return message.chat.type == "private"


@admin_router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(
        card("Quyidagi menyudan kerakli bo'limni tanlang."),
        reply_markup=admin_menu_reply_kb(),
    )


@admin_router.message(StateFilter(None), F.reply_to_message)
async def admin_reply_to_support(message: Message, bot: Bot):
    """Admin murojaat xabariga Telegram'ning \"Reply\" funksiyasi orqali javob bersa,
    javob avtomatik o'sha murojaatni yozgan foydalanuvchiga yuboriladi."""
    if not is_admin(message.from_user.id):
        return
    user_id = await get_support_thread_user(message.from_user.id, message.reply_to_message.message_id)
    if not user_id:
        return

    try:
        await bot.send_message(user_id, card("ADMIN JAVOBI:"))
        await bot.copy_message(chat_id=user_id, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.reply(card("Javobingiz foydalanuvchiga yuborildi."))
    except TelegramBadRequest:
        await message.reply(card("Yuborib bo'lmadi - foydalanuvchi botni bloklagan bo'lishi mumkin."))
    except TelegramForbiddenError:
        await message.reply(card("Yuborib bo'lmadi - foydalanuvchi botni bloklagan bo'lishi mumkin."))


@admin_router.message(F.text == ADMIN_MENU_CANCEL)
async def admin_cancel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(card("Admin panel"), reply_markup=admin_menu_reply_kb())


@admin_router.callback_query(F.data == "payset_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    s = await get_stats()
    text = card(
        "JAMI FOYDALANUVCHILAR: " + str(s["total_users"]) + "\n"
        "OXIRGI 7 KUN: " + str(s["users_7_days"]) + "\n"
        "OXIRGI 1 OY: " + str(s["users_30_days"]) + "\n"
        "FAOL (OXIRGI 24 SOAT): " + str(s["active_users"]),
    )
    await callback.message.answer(text, reply_markup=admin_menu_reply_kb())


# ---------- GURUH/KANAL QO'SHISH (username/havola orqali) ----------

def extract_chat_username(text: str):
    """Matndan @username ni ajratib oladi. Shaxsiy (invite-hash) havolalar uchun None qaytaradi."""
    text = text.strip()
    if text.startswith("@"):
        return text
    if "t.me/+" in text or "joinchat" in text:
        return None
    m = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})", text)
    if m:
        return "@" + m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", text):
        return "@" + text
    return None


@admin_router.callback_query(F.data == "payset_addchat")
async def admin_add_chat_instructions(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AddChat.waiting_link)
    await callback.message.answer(
        card(
            "1. Botni guruh yoki kanalga ADMIN qiling\n"
            "(havola yaratish huquqi bilan)\n\n"
            "2. Guruh/kanal username'ini yoki havolasini yuboring:\n\n"
            "Namuna:\n"
            "@mychannel\n"
            "https://t.me/mychannel",
        ),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.message(AddChat.waiting_link, F.text == ADMIN_MENU_CANCEL)
async def cancel_add_chat(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(card("Bekor qilindi."), reply_markup=admin_menu_reply_kb())


@admin_router.message(AddChat.waiting_link)
async def receive_chat_link(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if await is_reserved_menu_text(message, state):
        return

    username = extract_chat_username(message.text or "")
    if not username:
        await message.answer(
            card(
                "Bu shaxsiy (invite-link) guruh/kanalga o'xshaydi, undan username aniqlab bo'lmadi.\n"
                "Iltimos, guruh/kanalning ochiq @username'ini yoki https://t.me/username havolasini yuboring."
            )
        )
        return

    try:
        chat = await bot.get_chat(username)
    except TelegramBadRequest:
        await message.answer(
            card("Bunday guruh/kanal topilmadi. Username to'g'ri yozilganini tekshiring.")
        )
        return

    me = await bot.get_me()
    try:
        member = await bot.get_chat_member(chat.id, me.id)
    except TelegramBadRequest:
        await message.answer(
            card("Bot bu guruh/kanalga umuman qo'shilmagan. Avval botni o'sha yerga qo'shing.")
        )
        return

    if member.status != "administrator":
        await message.answer(
            card("Bot bu yerda hali admin emas. Botga admin huquqini bering va qaytadan urinib ko'ring.")
        )
        return

    try:
        invite_link = await bot.export_chat_invite_link(chat.id)
    except TelegramBadRequest:
        invite_link = "https://t.me/" + username.lstrip("@")

    await add_required_chat(chat.id, chat.title or "Nomsiz", invite_link, chat.type)
    await state.clear()
    await message.answer(
        card("\"" + (chat.title or "Nomsiz") + "\" majburiy a'zolik ro'yxatiga qo'shildi."),
        reply_markup=admin_menu_reply_kb(),
    )


# ---------- TO'LOV SOZLAMALARI (bosh menyu) ----------

@admin_router.message(F.text == ADMIN_MENU_PAYMENT_SETTINGS)
async def admin_payment_settings_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        card("Kerakli bo'limni tanlang."),
        reply_markup=payment_settings_submenu_kb(),
    )


# ---------- YECHISH SO'ROVLARINI TASDIQLASH (avtomatik push orqali keladi) ----------

@admin_router.callback_query(F.data.startswith("wd_approve_"))
async def wd_approve(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    withdrawal_id = int(callback.data.replace("wd_approve_", ""))
    w = await get_withdrawal(withdrawal_id)
    if not w or w["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    await update_withdrawal_status(withdrawal_id, "approved")
    await mark_withdrawn(w["user_id"], w["amount"])
    await callback.message.edit_text(
        card(callback.message.text + "\n\nTASDIQLANDI"),
    )
    if w["network"] and w["crypto_amount"]:
        sent_amount_text = f"{w['crypto_amount']:.8f}".rstrip("0").rstrip(".") + " " + w["network"]
    else:
        sent_amount_text = fmt_money(w["amount"]) + " ALPHA"
    try:
        await bot.send_message(
            w["user_id"],
            card(
                "So'rov #" + str(withdrawal_id) + " tasdiqlandi.\n"
                + sent_amount_text + " hamyoningizga yuborildi.",
            ),
        )
    except TelegramBadRequest:
        pass

    # To'lovlar kanaliga avtomatik e'lon qilish
    channel_url = await get_setting("payments_channel_url", "")
    channel_username = extract_chat_username(channel_url) if channel_url else None
    if channel_username:
        user = await get_user(w["user_id"])
        if w["network"] and w["crypto_amount"]:
            announcement = format_channel_announcement(
                "WITHDRAW",
                user["username"] if user else "",
                w["user_id"],
                w["crypto_amount"],
                asset=w["network"],
            )
        else:
            announcement = format_channel_announcement(
                "WITHDRAW",
                user["username"] if user else "",
                w["user_id"],
                w["amount"],
            )
        try:
            await bot.send_message(
                channel_username,
                card(announcement),
            )
        except TelegramBadRequest:
            pass


@admin_router.callback_query(F.data.startswith("wd_reject_"))
async def wd_reject(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    withdrawal_id = int(callback.data.replace("wd_reject_", ""))
    w = await get_withdrawal(withdrawal_id)
    if not w or w["status"] != "pending":
        await callback.answer("Bu so'rov allaqachon ko'rib chiqilgan.", show_alert=True)
        return
    await update_withdrawal_status(withdrawal_id, "rejected")
    await refund_withdrawal(w["user_id"], w["amount"])
    await callback.message.edit_text(
        card(callback.message.text + "\n\nRAD ETILDI (mablag' qaytarildi)"),
    )
    try:
        await bot.send_message(
            w["user_id"],
            card(
                "So'rov #" + str(withdrawal_id) + " rad etildi.\n"
                "Mablag' balansingizga qaytarildi.",
            ),
        )
    except TelegramBadRequest:
        pass


# ---------- SOZLAMALAR (To'lov Sozlamalari submenyusi ichida) ----------

@admin_router.callback_query(F.data == "payset_bonus")
async def admin_set_bonus(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    current = await get_setting("referral_bonus", "1000")
    await state.set_state(SetSetting.waiting_value)
    await state.update_data(setting_key="referral_bonus", setting_label="Referal bonusi")
    await callback.message.answer(
        card(
            "JORIY QIYMAT: " + fmt_money(float(current)) + " ALPHA\n\n"
            "Yangi qiymatni yuboring (masalan: 0.0015):",
        ),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.callback_query(F.data == "payset_min")
async def admin_set_min(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    current = await get_setting("min_withdrawal", "10000")
    await state.set_state(SetSetting.waiting_value)
    await state.update_data(setting_key="min_withdrawal", setting_label="Minimal yechish summasi")
    await callback.message.answer(
        card(
            "JORIY QIYMAT: " + fmt_money(float(current)) + " ALPHA\n\n"
            "Yangi qiymatni yuboring (masalan: 0.02):",
        ),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.callback_query(F.data == "payset_rate")
async def admin_set_rate(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    current = await get_setting("alpha_usd_rate", "0.01")
    await state.set_state(SetSetting.waiting_value)
    await state.update_data(setting_key="alpha_usd_rate", setting_label="1 ALPHA narxi (USD)")
    await callback.message.answer(
        card(
            "JORIY KURS: 1 ALPHA = " + current + " USD\n\n"
            "Yangi qiymatni USD'da yuboring (masalan: 0.01 - ya'ni 1 sent):",
        ),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.callback_query(F.data == "payset_channel")
async def admin_set_channel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    current = await get_setting("payments_channel_url", "")
    await state.set_state(SetSetting.waiting_value)
    await state.update_data(setting_key="payments_channel_url", setting_label="To'lovlar kanali havolasi")
    await callback.message.answer(
        card(
            "JORIY HAVOLA: " + (current or "sozlanmagan") + "\n\n"
            "Yangi havolani yuboring (masalan: https://t.me/mychannel):",
        ),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.callback_query(F.data == "payset_networks")
async def admin_show_networks(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    networks = await get_withdrawal_networks()
    if networks:
        names = "\n".join("- " + n["name"] for n in networks)
        text = "JORIY KRIPTOVALYUTALAR (" + str(len(networks)) + "/10):\n\n" + names
    else:
        text = "Hozircha hech qanday kriptovalyuta qo'shilmagan."
    await callback.message.answer(card(text), reply_markup=networks_admin_kb(networks))


@admin_router.callback_query(F.data == "addnet")
async def admin_add_network_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AddNetwork.waiting_name)
    await callback.message.answer(
        card("Yangi kriptovalyuta belgisini yuboring (masalan: LTC, TRX, DOGE, USDT):"),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.message(AddNetwork.waiting_name, F.text == ADMIN_MENU_CANCEL)
async def cancel_add_network(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(card("Bekor qilindi."), reply_markup=admin_menu_reply_kb())


@admin_router.message(AddNetwork.waiting_name)
async def receive_network_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if await is_reserved_menu_text(message, state):
        return

    symbol = (message.text or "").strip().upper()
    if symbol not in SYMBOL_TO_COINGECKO_ID:
        await message.answer(
            card(
                "Noma'lum kriptovalyuta. Qo'llab-quvvatlanadigan:\n"
                + ", ".join(SYMBOL_TO_COINGECKO_ID.keys())
            )
        )
        return

    ok = await add_withdrawal_network(symbol)
    await state.clear()
    if ok:
        await message.answer(
            card("\"" + symbol + "\" kriptovalyutalar ro'yxatiga qo'shildi."),
            reply_markup=admin_menu_reply_kb(),
        )
    else:
        await message.answer(
            card("Qo'shib bo'lmadi - bu allaqachon bor yoki limit (10 ta) to'lgan."),
            reply_markup=admin_menu_reply_kb(),
        )


@admin_router.callback_query(F.data.startswith("delnet_"))
async def admin_delete_network(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    network_id = int(callback.data.split("_", 1)[1])
    await remove_withdrawal_network(network_id)
    networks = await get_withdrawal_networks()
    if networks:
        names = "\n".join("- " + n["name"] for n in networks)
        text = "JORIY KRIPTOVALYUTALAR (" + str(len(networks)) + "/10):\n\n" + names
    else:
        text = "Hozircha hech qanday kriptovalyuta qo'shilmagan."
    await callback.message.answer(card("Kriptovalyuta o'chirildi."))
    await callback.message.answer(card(text), reply_markup=networks_admin_kb(networks))


@admin_router.callback_query(F.data == "payset_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(Broadcast.waiting_message)
    await callback.message.answer(
        card("Barcha foydalanuvchilarga yuborish uchun xabar matnini kiriting:"),
        reply_markup=admin_cancel_reply_kb(),
    )


@admin_router.message(Broadcast.waiting_message, F.text == ADMIN_MENU_CANCEL)
async def cancel_broadcast(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(card("Bekor qilindi."), reply_markup=admin_menu_reply_kb())


@admin_router.message(Broadcast.waiting_message)
async def receive_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    if await is_reserved_menu_text(message, state):
        return
    if not message.text:
        await message.answer(card("Iltimos, faqat matn ko'rinishida xabar yuboring."))
        return

    await state.clear()
    broadcast_text = card(message.text)
    user_ids = await get_all_user_ids()

    await message.answer(
        card(str(len(user_ids)) + " ta foydalanuvchiga yuborilmoqda..."),
        reply_markup=admin_menu_reply_kb(),
    )

    sent = 0
    failed = 0
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, broadcast_text)
            sent += 1
        except TelegramBadRequest:
            failed += 1
        except TelegramForbiddenError:
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(
        card(
            "Yuborish yakunlandi.\n\n"
            "YUBORILDI: " + str(sent) + "\n"
            "YUBORILMADI: " + str(failed)
        ),
    )


@admin_router.message(SetSetting.waiting_value, F.text == ADMIN_MENU_CANCEL)
async def cancel_setting(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(card("Bekor qilindi."), reply_markup=admin_menu_reply_kb())


@admin_router.message(SetSetting.waiting_value)
async def receive_setting_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if await is_reserved_menu_text(message, state):
        return
    data = await state.get_data()
    key = data["setting_key"]
    label = data["setting_label"]
    value = message.text.strip()

    if key in ("referral_bonus", "min_withdrawal", "alpha_usd_rate"):
        try:
            float(value.replace(" ", ""))
        except ValueError:
            await message.answer(card("Iltimos, faqat raqam kiriting."))
            return
        value = value.replace(" ", "")

    if key == "payments_channel_url":
        # Telegram inline tugma faqat to'g'ri "url" (masalan https://t.me/username)
        # qabul qiladi. Agar admin @username yoki t.me/username kabi shakl yozsa ham,
        # avtomatik https://t.me/username ko'rinishiga o'tkazamiz - aks holda foydalanuvchi
        # "To'lovlar" tugmasini bosganda bot javob bermay qotib qoladi.
        username = extract_chat_username(value)
        if not username:
            await message.answer(
                card(
                    "Bu havola noto'g'ri formatda.\n"
                    "Iltimos, ochiq kanal username'ini yoki havolasini yuboring:\n\n"
                    "   @mychannel\n"
                    "   https://t.me/mychannel"
                )
            )
            return
        value = "https://t.me/" + username.lstrip("@")

    await set_setting(key, value)
    await state.clear()
    await message.answer(card(label + " muvaffaqiyatli yangilandi."), reply_markup=admin_menu_reply_kb())


# =========================================================
# ISHGA TUSHIRISH
# =========================================================

async def main():
    if BOT_TOKEN == "123456789:AAExampleTokenHereChangeMe" or not BOT_TOKEN:
        raise RuntimeError("bot.py faylining tepasida BOT_TOKEN ni o'zingizning haqiqiy tokeningizga almashtiring!")

    await init_db()

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2))
    dp = Dispatcher(storage=MemoryStorage())

    async def activity_middleware(handler, event, data):
        """Har qanday xabar yoki tugma bosilganda foydalanuvchining 'last_active_at'
        vaqtini yangilaydi - shu orqali admin statistikasida 'Faol' foydalanuvchilar
        soni hisoblanadi."""
        user = data.get("event_from_user")
        if user:
            try:
                await touch_last_active(user.id)
            except Exception:
                pass
        return await handler(event, data)

    dp.update.outer_middleware(activity_middleware)

    dp.include_router(admin_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
