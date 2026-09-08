import asyncio
import logging
import time
import base64
import random
import requests
import re
import string
from datetime import datetime, timedelta, timezone
from threading import Thread
import threading

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ButtonStyle
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputRichMessage, InputRichBlockParagraph, InputRichBlockSectionHeading,
    InputRichBlockTable, InputRichBlockPreformatted, InputRichBlockList,
    InputRichBlockListItem, RichTextBold,
)
from aiogram.types.rich_block_table_cell import RichBlockTableCell
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"

# ─── PICK NETWORK CONFIG ─────────────────────────────────────────────────────
PICK_CONFIGS = {
    "TronPick": {
        "domain": "tronpick.io",
        "sitekey": "0x4AAAAAAAW74HiAaujGhyeV",
        "xor_key": "0542f6c18bc7906d742a8401d0b5ef7f50ee304bff4f032348a4ceb3fd2d6bb1",
        "coin": "TRX",
    },
    "LitePick": {
        "domain": "litepick.io",
        "sitekey": "0x4AAAAAAA0-UWDHOKP0OrgS",
        "xor_key": "bd98ddb15b2b9e248ff50123976abe8600e27d3b5c08be9f864267d35e07930b",
        "coin": "LTC",
    },
    "DogePick": {
        "domain": "dogepick.io",
        "sitekey": "0x4AAAAAABbyeJO9QkW9czUo",
        "xor_key": "6d60cca458034d0ccf0e9a81408a5704ac3e4ee33cd267545afe79f3a25a09c1",
        "coin": "DOGE",
    },
}

# ─── CRANES ──────────────────────────────────────────────────────────────────
CRANES = [
    {"name": "TronPick", "emoji": "💎", "active": False, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "LitePick", "emoji": "🔵", "active": False, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "DogePick", "emoji": "🐕", "active": False, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
]

CRANE_TIMERS = {}

def get_crane_timer(crane_name: str):
    if crane_name not in CRANE_TIMERS:
        CRANE_TIMERS[crane_name] = datetime.now(timezone.utc)
    return CRANE_TIMERS[crane_name]

# ─── FSM ─────────────────────────────────────────────────────────────────────
class AddAccount(StatesGroup):
    email    = State()
    password = State()

class SettingsFSM(StatesGroup):
    api_key = State()

# ─── USER SETTINGS ───────────────────────────────────────────────────────────
USER_SETTINGS = {}
LANGUAGES = {
    "uz_latin":    "🇺🇿 O'zbekcha (lotin)",
    "uz_cyrillic": "🇺🇿 Ўзбекча (кирилл)",
}

def get_user_settings(chat_id: int) -> dict:
    return USER_SETTINGS.setdefault(chat_id, {"api_key": None, "language": "uz_latin"})

# ─── TRANSLATIONS ─────────────────────────────────────────────────────────────
TEXTS = {
    "uz_latin": {
        "dashboard_title": "ALPHA",
        "statistics_title": "Statistika",
        "guide_header1": "1",
        "guide_header_mid": "",
        "guide_header2": "2",
        "guide_part1": "🔵🔵🔵🔵",
        "guide_part_mid": "",
        "guide_part2": "🔴🔴🔴🔴",
        "col_account": "Akkauntlar",
        "col_next_claim": "Keyingi olish",
        "col_balance": "Balanslari",
        "btn_settings": "⚙️ Sozlamalar",
        "btn_refresh": "🔄 Yangilash",
        "btn_add_account": "➕ Akkaunt qo'shish",
        "btn_back": "◀️ Orqaga",
        "btn_cancel": "❌ Bekor qilish",
        "btn_api_key": "🔑 API",
        "settings_api_label": "🔑 API",
        "btn_language": "🌐 Til",
        "settings_id_label": "🆔 IDS",
        "btn_support": "🆘 Yordam",
        "btn_main_menu": "🏠 Bosh menyu",
        "btn_back_to_crane": "◀️ {crane}ga qaytish",
        "not_found": "Topilmadi!",
        "updated": "♻️ Yangilandi!",
        "cancelled": "❌ Bekor qilindi.",
        "plain_text_warning": "⚠️ Iltimos, oddiy matn yuboring.\n\n/cancel — bekor qilish uchun.",
        "crane_no_accounts": "Faol akkaunt yo'q - qo'shish uchun + bosing",
        "stats_col_account": "🏷️ Akkaunt",
        "stats_col_next_claim": "⏱️ Keyingi olish",
        "stats_col_balance": "💰 Balans",
        "add_account_title": "{emoji} Akkaunt qo'shish - {crane}",
        "field_label": "Belgi: {label}",
        "add_account_send_email": "Akkaunt emailini yuboring:",
        "email_line": "Email: {email}",
        "send_password": "Endi parolni yuboring:",
        "password_line": "Parol: ✅",
        "cancel_hint": "/cancel — bekor qilish uchun.",
        "account_added": "Akkaunt qo'shildi!",
        "next_claim_in": "⏱️ Keyingi olish: 60:00",
        "settings_title": "⚙️ Sozlamalar",
        "api_key_set": "✅ O'rnatilgan",
        "api_key_not_set": "❌ O'rnatilmagan",
        "send_api_key": "🔑 API kalitingizni yuboring:",
        "api_key_saved": "✅ API Kalit saqlandi!",
        "choose_language": "🌐 Tilni tanlang:",
        "no_api_key": "⚠️ Avval Sozlamalar > API Kalit orqali XEVIL API kalitini o'rnating!",
        "started": "🚀 {count} ta akkaunt ishga tushirildi!",
        "stopped": "⏹️ {count} ta akkaunt to'xtatildi!",
    },
    "uz_cyrillic": {
        "dashboard_title": "ALPHA",
        "statistics_title": "Статистика",
        "guide_header1": "1",
        "guide_header_mid": "",
        "guide_header2": "2",
        "guide_part1": "🔵🔵🔵🔵",
        "guide_part_mid": "",
        "guide_part2": "🔴🔴🔴🔴",
        "col_account": "Аккаунтлар",
        "col_next_claim": "Кейинги олиш",
        "col_balance": "Баланслари",
        "btn_settings": "⚙️ Созламалар",
        "btn_refresh": "🔄 Янгилаш",
        "btn_add_account": "➕ Аккаунт қўшиш",
        "btn_back": "◀️ Орқага",
        "btn_cancel": "❌ Бекор қилиш",
        "btn_api_key": "🔑 API",
        "settings_api_label": "🔑 API",
        "btn_language": "🌐 Тил",
        "settings_id_label": "🆔 IDS",
        "btn_support": "🆘 Ёрдам",
        "btn_main_menu": "🏠 Бош меню",
        "btn_back_to_crane": "◀️ {crane}га қайтиш",
        "not_found": "Топилмади!",
        "updated": "♻️ Янгиланди!",
        "cancelled": "❌ Бекор қилинди.",
        "plain_text_warning": "⚠️ Илтимос, оддий матн юборинг.\n\n/cancel — бекор қилиш учун.",
        "crane_no_accounts": "Фаол аккаунт йўқ - қўшиш учун + босинг",
        "stats_col_account": "🏷️ Аккаунт",
        "stats_col_next_claim": "⏱️ Кейинги олиш",
        "stats_col_balance": "💰 Баланс",
        "add_account_title": "{emoji} Аккаунт қўшиш - {crane}",
        "field_label": "Белги: {label}",
        "add_account_send_email": "Аккаунт email'ини юборинг:",
        "email_line": "Email: {email}",
        "send_password": "Энди паролни юборинг:",
        "password_line": "Парол: ✅",
        "cancel_hint": "/cancel — бекор қилиш учун.",
        "account_added": "Аккаунт қўшилди!",
        "next_claim_in": "⏱️ Кейинги олиш: 60:00",
        "settings_title": "⚙️ Созламалар",
        "api_key_set": "✅ Ўрнатилган",
        "api_key_not_set": "❌ Ўрнатилмаган",
        "send_api_key": "🔑 API калитингизни юборинг:",
        "api_key_saved": "✅ API Калит сақланди!",
        "choose_language": "🌐 Тилни танланг:",
        "no_api_key": "⚠️ Аввал Созламалар > API Калит орқали XEVIL API калитини ўрнатинг!",
        "started": "🚀 {count} та аккаунт ишга туширилди!",
        "stopped": "⏹️ {count} та аккаунт тўхтатилди!",
    },
}

def t(chat_id: int, key: str, **kwargs) -> str:
    lang = get_user_settings(chat_id).get("language", "uz_latin")
    table = TEXTS.get(lang, TEXTS["uz_latin"])
    template = table.get(key, TEXTS["uz_latin"].get(key, key))
    return template.format(**kwargs) if kwargs else template

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_crane(name: str):
    return next((c for c in CRANES if c["name"] == name), None)

def cancel_keyboard(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_add", style=ButtonStyle.DANGER)]
    ])

def settings_cancel_keyboard(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_settings", style=ButtonStyle.DANGER)]
    ])

def format_countdown(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"

def get_countdown(timer_start: datetime) -> str:
    elapsed = (datetime.now(timezone.utc) - timer_start).total_seconds()
    remaining = max(0, 3600 - elapsed)
    return format_countdown(remaining)

def get_account_countdown(next_claim_at) -> str:
    if not next_claim_at:
        return "--:--"
    remaining = (next_claim_at - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        return "🟢 Ready"
    return format_countdown(remaining)

def add_log(crane: dict, text: str):
    crane.setdefault("logs", []).append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "text": text,
    })
    crane["logs"] = crane["logs"][-20:]

async def require_text(message: Message) -> str | None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return None
    return message.text.strip()

# ─── PICK BOT CLASS ──────────────────────────────────────────────────────────
class PickBot:
    def __init__(self, email: str, password: str, api_key: str, config: dict):
        self.session  = requests.Session()
        self.email    = email
        self.password = password
        self.api_key  = api_key
        self.config   = config
        self.domain   = config["domain"]
        self.balance  = "0.00000000"
        self.claim_time_remaining = 0
        self.fp = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        self.ua = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Origin":  f"https://{self.domain}",
            "Referer": f"https://{self.domain}/login.php",
        }

    def solve_captcha(self) -> str | None:
        try:
            r = requests.post("https://api.sctg.xyz/in.php", data={
                "key": self.api_key, "method": "turnstile",
                "sitekey": self.config["sitekey"],
                "pageurl": f"https://{self.domain}/faucet.php",
                "json": 1,
            }, timeout=30).json()
            if r.get("status") != 1:
                return None
            rid = r["request"]
            for _ in range(40):
                time.sleep(3)
                g = requests.get(
                    f"https://api.sctg.xyz/res.php?key={self.api_key}&action=get&id={rid}&json=1",
                    timeout=30
                ).json()
                if g.get("status") == 1:
                    return g["request"]
                if g.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    break
        except Exception:
            pass
        return None

    def login(self) -> tuple[bool, str]:
        try:
            self.session.cookies.set("fp", self.fp, domain=self.domain)
            self.session.get(f"https://{self.domain}/login.php",
                             headers={"User-Agent": self.ua}, timeout=20)
            csrf = self.session.cookies.get("csrf_cookie_name")
            if not csrf:
                return False, "CSRF Missing"
            token = self.solve_captcha()
            if not token:
                return False, "Captcha Failed"
            res = self.session.post(
                f"https://{self.domain}/process.php",
                data={
                    "action": "login", "email": self.email,
                    "password": self.password, "captcha_type": "3",
                    "c_captcha_response": token, "csrf_test_name": csrf,
                    "twofa": "", "g-recaptcha-response": "",
                    "_iconcaptcha-token": "",
                    "ic-rq": "", "ic-wid": "", "ic-cid": "", "ic-hp": "",
                    "h-captcha-response": "", "pcaptcha_token": "",
                },
                headers=self.headers, timeout=30,
            ).json()
            if res.get("ret") == 1:
                return True, "Success"
            return False, res.get("mes", "Unknown")
        except Exception as e:
            return False, str(e)

    def update_info(self) -> None:
        try:
            html = self.session.get(
                f"https://{self.domain}/faucet.php",
                headers={"User-Agent": self.ua}, timeout=20
            ).text
            m = re.search(r'user_balance">([\d.]+)', html)
            if m:
                self.balance = m.group(1)
            tmr = re.search(r'show_countdown_clock\((\d+)\)', html)
            self.claim_time_remaining = int(tmr.group(1)) if tmr else 0
        except Exception:
            pass

    def claim(self) -> tuple[bool, str]:
        try:
            token = self.solve_captcha()
            if not token:
                return False, "Captcha failed"
            csrf = self.session.cookies.get("csrf_cookie_name")
            if not csrf:
                return False, "No CSRF"
            ts       = int(time.time())
            data_str = f"{random.randint(100,200)}:{random.randint(10,50)}:{ts}"
            xk       = self.config["xor_key"]
            hashed   = base64.b64encode(
                "".join(chr(ord(c) ^ ord(xk[i % len(xk)])) for i, c in enumerate(data_str)).encode()
            ).decode()
            res = self.session.post(
                f"https://{self.domain}/process.php",
                data={
                    "action": "claim_hourly_faucet", "hash": hashed,
                    "captcha_type": "3", "c_captcha_response": token,
                    "csrf_test_name": csrf,
                },
                headers=self.headers, timeout=30,
            ).json()
            if res.get("ret") == 1:
                if "balance" in res:
                    self.balance = str(float(res["balance"]) / 100_000_000)
                self.update_info()
                return True, res.get("mes", "Success")
            return False, res.get("mes", "Failed")
        except Exception as e:
            return False, str(e)

# ─── WORKER ───────────────────────────────────────────────────────────────────
STOP_EVENTS: dict[str, threading.Event] = {}

def pick_bot_worker(crane_name: str, acc_idx: int, stop: threading.Event, chat_id: int) -> None:
    crane = get_crane(crane_name)
    if not crane:
        return
    account = crane["accounts"][acc_idx]
    cfg     = PICK_CONFIGS.get(crane_name)
    if not cfg:
        return
    api_key = get_user_settings(chat_id).get("api_key")
    if not api_key:
        add_log(crane, f"❌ API key yo'q: {account['email']}")
        return

    pb = PickBot(account["email"], account["password"], api_key, cfg)
    ok, msg = pb.login()
    if ok:
        account["active"] = True
        add_log(crane, f"✅ Login: {account['email']}")
    else:
        account["active"] = False
        add_log(crane, f"❌ Login xato ({msg}): {account['email']}")
        return

    while not stop.is_set():
        try:
            pb.update_info()
            if pb.claim_time_remaining <= 0:
                add_log(crane, f"⏳ Claiming: {account['email']}")
                ok, m = pb.claim()
                if ok:
                    account["balance"] = float(pb.balance)
                    crane["claims"] += 1
                    crane["balance"] = sum(a.get("balance", 0.0) for a in crane["accounts"])
                    add_log(crane, f"✅ Claimed {cfg['coin']}: {account['email']} | {m}")
                else:
                    add_log(crane, f"❌ Claim xato ({m}): {account['email']}")
                pb.claim_time_remaining = 3600
                account["next_claim_at"] = datetime.now(timezone.utc) + timedelta(minutes=60)
            time.sleep(1)
        except Exception as e:
            add_log(crane, f"⚠️ {account['email']}: {e}")
            time.sleep(10)

# ─── RICH MESSAGE BUILDERS ───────────────────────────────────────────────────
def build_main_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    alpha_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "dashboard_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )

    guide_table = InputRichBlockTable(
        cells=[
            [
                cell(t(chat_id, "guide_header1"), header=True, align="center"),
                cell(t(chat_id, "guide_header_mid"), header=True, align="center"),
                cell(t(chat_id, "guide_header2"), header=True, align="center"),
            ],
            [
                cell(t(chat_id, "guide_part1"), align="center"),
                cell(t(chat_id, "guide_part_mid"), align="center"),
                cell(t(chat_id, "guide_part2"), align="center"),
            ],
        ],
        is_bordered=True,
        is_striped=True,
    )

    return InputRichMessage(blocks=[alpha_table, guide_table])


def build_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for c in CRANES:
        row.append(InlineKeyboardButton(
            text=f"{c['emoji']} {c['name']}",
            callback_data=f"crane_{c['name']}",
            style=ButtonStyle.PRIMARY,
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_support"), url="https://t.me/alphadevlab", style=ButtonStyle.DANGER),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_settings"), callback_data="settings", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text=t(chat_id, "btn_refresh"),  callback_data="refresh",  style=ButtonStyle.SUCCESS),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_crane_rich_message(chat_id: int, crane: dict) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    blocks = []

    # Statistika sarlavhasi
    blocks.append(InputRichBlockTable(
        cells=[[cell(t(chat_id, "statistics_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    ))

    # Akkauntlar jadvali
    accounts = crane.get("accounts", [])
    header_row = [
        cell(t(chat_id, "stats_col_account"),    header=True, align="left"),
        cell(t(chat_id, "stats_col_next_claim"), header=True, align="center"),
        cell(t(chat_id, "stats_col_balance"),    header=True, align="right"),
    ]

    if not accounts:
        data_rows = [[
            cell(crane["name"], align="left"),
            cell(get_countdown(get_crane_timer(crane["name"])), align="center"),
            cell("0.000000", align="right"),
        ]]
    else:
        data_rows = []
        for acc in accounts:
            email   = acc.get("email", "")[:15]
            balance = acc.get("balance", 0.0)
            cd      = get_account_countdown(acc.get("next_claim_at"))
            status  = "🟢" if acc.get("active", False) else "🔴"
            data_rows.append([
                cell(f"{status} {email}", align="left"),
                cell(cd, align="center"),
                cell(f"{balance:.6f}", align="right"),
            ])

    blocks.append(InputRichBlockTable(
        cells=[header_row] + data_rows,
        is_bordered=True,
        is_striped=True,
    ))

    # Loglar
    logs = crane.get("logs", [])
    if logs:
        log_text = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-8:])
        blocks.append(InputRichBlockPreformatted(text=log_text))

    return InputRichMessage(blocks=blocks)


def build_crane_keyboard(chat_id: int, crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_add_account"), callback_data=f"add_account_{crane_name}", style=ButtonStyle.DANGER)],
        [
            InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=t(chat_id, "btn_back"),    callback_data="back_main",           style=ButtonStyle.SUCCESS),
        ],
    ])


def build_settings_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    def short_word(text: str) -> str:
        parts = text.split(" ", 1)
        word = parts[1] if len(parts) > 1 else parts[0]
        return word[:10]

    s           = get_user_settings(chat_id)
    raw_key     = s.get("api_key")
    api_status  = raw_key[:10] if raw_key else "----------"
    lang_name   = short_word(LANGUAGES.get(s.get("language", "uz_latin"), "uz_latin"))
    short_id    = str(chat_id % 10_000_000_000).zfill(10)

    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "settings_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )
    info_table = InputRichBlockTable(
        cells=[
            [
                cell(t(chat_id, "settings_api_label"), header=True, align="center"),
                cell(t(chat_id, "btn_language"),        header=True, align="center"),
                cell(t(chat_id, "settings_id_label"),   header=True, align="center"),
            ],
            [
                cell(api_status, align="center"),
                cell(lang_name,  align="center"),
                cell(short_id,   align="center"),
            ],
        ],
        is_bordered=True,
        is_striped=True,
    )
    return InputRichMessage(blocks=[title_table, info_table])


def build_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    api_key_set   = bool(get_user_settings(chat_id).get("api_key"))
    api_key_style = ButtonStyle.SUCCESS if api_key_set else ButtonStyle.DANGER
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_api_key"),  callback_data="settings_api_key",  style=api_key_style)],
        [InlineKeyboardButton(text=t(chat_id, "btn_language"), callback_data="settings_language", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_back"),     callback_data="back_main",         style=ButtonStyle.SUCCESS)],
    ])


def build_language_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"lang_{code}")]
        for code, name in LANGUAGES.items()
    ])

# ─── BOT ─────────────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

active_messages: dict[int, int] = {}
active_screen:   dict[int, str] = {}


async def show_rich(chat_id: int, rich_message: InputRichMessage, reply_markup: InlineKeyboardMarkup | None = None):
    msg_id = active_messages.get(chat_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                rich_message=rich_message, reply_markup=reply_markup,
            )
            return
        except Exception:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
    msg = await bot.send_rich_message(chat_id=chat_id, rich_message=rich_message, reply_markup=reply_markup)
    active_messages[chat_id] = msg.message_id


async def show_text(chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    msg_id = active_messages.get(chat_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=text, reply_markup=reply_markup,
            )
            return
        except Exception:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception:
                pass
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    active_messages[chat_id] = msg.message_id


async def delete_silently(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


async def auto_refresh():
    while True:
        await asyncio.sleep(1)
        try:
            for chat_id, message_id in list(active_messages.items()):
                screen = active_screen.get(chat_id, "")
                try:
                    if screen == "dashboard":
                        await bot.edit_message_text(
                            chat_id=chat_id, message_id=message_id,
                            rich_message=build_main_rich_message(chat_id),
                            reply_markup=build_keyboard(chat_id),
                        )
                    elif screen.startswith("crane:"):
                        crane_name = screen.split(":", 1)[1]
                        crane = get_crane(crane_name)
                        if crane:
                            await bot.edit_message_text(
                                chat_id=chat_id, message_id=message_id,
                                rich_message=build_crane_rich_message(chat_id, crane),
                                reply_markup=build_crane_keyboard(chat_id, crane_name),
                            )
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Auto refresh error: {e}")

# ─── HANDLERS ────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)

    if current_state and current_state.startswith("SettingsFSM"):
        active_screen[chat_id] = "settings"
        await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    elif crane_name and get_crane(crane_name):
        crane = get_crane(crane_name)
        active_screen[chat_id] = f"crane:{crane_name}"
        await show_rich(chat_id, build_crane_rich_message(chat_id, crane), build_crane_keyboard(chat_id, crane_name))
    else:
        active_screen[chat_id] = "dashboard"
        await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.callback_query(F.data == "refresh")
async def cb_refresh(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer(t(chat_id, "updated"))


@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer()


@dp.callback_query(F.data.startswith("crane_"))
async def cb_crane(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("crane_", "")
    crane = get_crane(crane_name)
    chat_id = call.message.chat.id
    if not crane:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return
    active_screen[chat_id] = f"crane:{crane_name}"
    await show_rich(chat_id, build_crane_rich_message(chat_id, crane), build_crane_keyboard(chat_id, crane_name))
    await call.answer()


@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("add_account_", "")
    crane = get_crane(crane_name)
    chat_id = call.message.chat.id
    if not crane:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return

    acc_num = len(crane["accounts"]) + 1
    label   = f"Account {acc_num}"

    await state.set_state(AddAccount.email)
    await state.update_data(crane_name=crane_name, label=label)
    active_screen[chat_id] = "add_account"

    text = (
        f"{t(chat_id, 'add_account_title', emoji=crane['emoji'], crane=crane_name)}\n\n"
        f"{t(chat_id, 'field_label', label=label)}\n\n"
        f"{t(chat_id, 'add_account_send_email')}\n\n"
        f"{t(chat_id, 'cancel_hint')}"
    )
    await show_text(chat_id, text, cancel_keyboard(chat_id))
    await call.answer()


@dp.message(AddAccount.email)
async def fsm_email(message: Message, state: FSMContext):
    email = await require_text(message)
    if email is None:
        return
    await state.update_data(email=email)
    await state.set_state(AddAccount.password)
    chat_id = message.chat.id
    await delete_silently(message)
    text = (
        f"{t(chat_id, 'email_line', email=email)}\n\n"
        f"{t(chat_id, 'send_password')}\n\n"
        f"{t(chat_id, 'cancel_hint')}"
    )
    await show_text(chat_id, text, cancel_keyboard(chat_id))


@dp.message(AddAccount.password)
async def fsm_password(message: Message, state: FSMContext):
    password = await require_text(message)
    if password is None:
        return
    data = await state.get_data()
    crane = get_crane(data["crane_name"])
    chat_id = message.chat.id
    await delete_silently(message)
    if not crane:
        await state.clear()
        return

    new_acc = {
        "label":         data["label"],
        "email":         data["email"],
        "password":      password,
        "active":        False,
        "balance":       0.0,
        "next_claim_at": datetime.now(timezone.utc) + timedelta(minutes=60),
    }
    crane["accounts"].append(new_acc)
    add_log(crane, f"Connecting to {data['crane_name']} Server...")
    add_log(crane, f"Account linked: {data['email']}")

    await state.clear()

    summary = (
        f"{t(chat_id, 'account_added')}\n\n"
        f"{crane['emoji']} {data['crane_name']} #{len(crane['accounts'])}\n"
        f"{t(chat_id, 'field_label', label=data['label'])}\n"
        f"{t(chat_id, 'email_line', email=data['email'])}\n"
        f"{t(chat_id, 'password_line')}\n\n"
        f"{t(chat_id, 'next_claim_in')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_back_to_crane", crane=data['crane_name']), callback_data=f"crane_{data['crane_name']}", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_main_menu"), callback_data="back_main")],
    ])
    active_screen[chat_id] = "account_added"
    await show_text(chat_id, summary, keyboard)


@dp.callback_query(F.data == "cancel_add")
async def cb_cancel_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()
    chat_id = call.message.chat.id
    crane = get_crane(crane_name)
    if crane:
        active_screen[chat_id] = f"crane:{crane_name}"
        await show_rich(chat_id, build_crane_rich_message(chat_id, crane), build_crane_keyboard(chat_id, crane_name))
    else:
        active_screen[chat_id] = "dashboard"
        await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer(t(chat_id, "cancelled"))


@dp.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await call.answer()


@dp.callback_query(F.data == "settings_api_key")
async def cb_settings_api_key(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsFSM.api_key)
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings_api_key"
    text = f"{t(chat_id, 'send_api_key')}\n\n{t(chat_id, 'cancel_hint')}"
    await show_text(chat_id, text, settings_cancel_keyboard(chat_id))
    await call.answer()


@dp.message(SettingsFSM.api_key)
async def fsm_api_key(message: Message, state: FSMContext):
    api_key = await require_text(message)
    if api_key is None:
        return
    get_user_settings(message.chat.id)["api_key"] = api_key
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))


@dp.callback_query(F.data == "settings_language")
async def cb_settings_language(call: CallbackQuery):
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings_language"
    await show_text(chat_id, t(chat_id, "choose_language"), build_language_keyboard(chat_id))
    await call.answer()


@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang_select(call: CallbackQuery):
    code = call.data.replace("lang_", "")
    chat_id = call.message.chat.id
    if code not in LANGUAGES:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return
    get_user_settings(chat_id)["language"] = code
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await call.answer(f"✅ {LANGUAGES[code]}")


@dp.callback_query(F.data == "cancel_settings")
async def cb_cancel_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await call.answer(t(chat_id, "cancelled"))


# ─── MAIN ────────────────────────────────────────────────────────────────────
async def main():
    asyncio.create_task(auto_refresh())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
