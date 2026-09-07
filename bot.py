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
    InputRichMessage, InputRichBlockTable, InputRichBlockPreformatted,
    InputRichBlockParagraph, RichTextBold,
)
from aiogram.types.rich_block_table_cell import RichBlockTableCell
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.CRITICAL)

BOT_TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"

# ─── PICK NETWORK KONFIGURATSIYASI ───────────────────────────────────────────
PICK_CONFIGS = {
    "TronPick": {
        "domain": "tronpick.io",
        "sitekey": "0x4AAAAAAAW74HiAaujGhyeV",
        "xor_key": "0542f6c18bc7906d742a8401d0b5ef7f50ee304bff4f032348a4ceb3fd2d6bb1",
        "coin": "TRX",
        "coin_emoji": "🔴",
    },
    "LitePick": {
        "domain": "litepick.io",
        "sitekey": "0x4AAAAAAA0-UWDHOKP0OrgS",
        "xor_key": "bd98ddb15b2b9e248ff50123976abe8600e27d3b5c08be9f864267d35e07930b",
        "coin": "LTC",
        "coin_emoji": "🌕",
    },
    "DogePick": {
        "domain": "dogepick.io",
        "sitekey": "0x4AAAAAABbyeJO9QkW9czUo",
        "xor_key": "6d60cca458034d0ccf0e9a81408a5704ac3e4ee33cd267545afe79f3a25a09c1",
        "coin": "DOGE",
        "coin_emoji": "🐕",
    },
}

# ─── KRANLAR ──────────────────────────────────────────────────────────────────
CRANES = []
for _name, _config in PICK_CONFIGS.items():
    CRANES.append({
        "name": _name,
        "emoji": _config["coin_emoji"],
        "active": False,
        "claims": 0,
        "balance": 0.0,
        "accounts": [],
        "logs": [],
        "config": _config,
    })

# ─── FSM STATES ──────────────────────────────────────────────────────────────
class AddAccount(StatesGroup):
    email    = State()
    password = State()

class SettingsFSM(StatesGroup):
    api_key = State()

# ─── SETTINGS ─────────────────────────────────────────────────────────────────
USER_SETTINGS: dict[int, dict] = {}

LANGUAGES = {
    "uz_latin":    "🇺🇿 O'zbekcha (lotin)",
    "uz_cyrillic": "🇺🇿 Ўзбекча (кирилл)",
}

def get_user_settings(chat_id: int) -> dict:
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {"api_key": None, "language": "uz_latin"}
    return USER_SETTINGS[chat_id]

# ─── TARJIMALAR ──────────────────────────────────────────────────────────────
TEXTS = {
    "uz_latin": {
        # Dashboard
        "app_name":             "ALPHA",
        "network_name":         "PICK NETWORK",
        "col_crane":            "Kran",
        "col_accounts":         "Akkauntlar",
        "col_balance":          "Balans",
        "col_status":           "Holat",
        "total_label":          "Jami",
        "guide_h1":             "1",
        "guide_h2":             "2",
        "guide_h3":             "3",
        "guide_p1":             "🔵🔵🔵🔵🔵",
        "guide_p2":             "⚪⚪⚪⚪⚪",
        "guide_p3":             "🔴🔴🔴🔴🔴",
        # Buttons
        "btn_settings":         "⚙️ Sozlamalar",
        "btn_refresh":          "🔄 Yangilash",
        "btn_add_account":      "➕ Akkaunt qo'shish",
        "btn_back":             "◀️ Orqaga",
        "btn_cancel":           "❌ Bekor qilish",
        "btn_api_key":          "🔑 API",
        "btn_language":         "🌐 Til",
        "btn_support":          "🆘 Yordam",
        "btn_main_menu":        "🏠 Bosh menyu",
        "btn_back_to_crane":    "◀️ {crane}ga qaytish",
        "btn_start_all":        "▶️ Ishga tushirish",
        "btn_stop_all":         "⏹️ To'xtatish",
        # Messages
        "not_found":            "Topilmadi!",
        "updated":              "♻️ Yangilandi!",
        "cancelled":            "❌ Bekor qilindi.",
        "plain_text_warning":   "⚠️ Iltimos, oddiy matn yuboring.",
        "no_api_key":           "⚠️ Avval Settings → API orqali XEVIL kalitini kiriting!",
        "started":              "🚀 {count} ta akkaunt ishga tushirildi!",
        "stopped":              "⏹️ {count} ta akkaunt to'xtatildi!",
        # Crane panel
        "crane_no_accounts":    "⚠️ Akkaunt yo'q — ➕ tugmasini bosing",
        "col_email":            "Email",
        "col_timer":            "Timer",
        "col_bal":              "Balans",
        "status_online":        "🟢",
        "status_offline":       "🔴",
        "no_logs":              "⏳ Loglar yo'q...",
        # Add account
        "add_account_title":    "➕ {crane} — Akkaunt qo'shish",
        "field_label":          "#{label}",
        "send_email":           "📧 Email yuboring:",
        "email_line":           "📧 Email: {email}",
        "send_password":        "🔑 Parol yuboring:",
        "password_ok":          "🔑 Parol: ✅",
        "cancel_hint":          "/cancel — bekor qilish",
        "account_added":        "✅ Akkaunt qo'shildi!",
        "start_hint":           "▶️ Ishga tushirish uchun bosh menyudan tugmani bosing.",
        # Settings
        "settings_title":       "⚙️ Sozlamalar",
        "settings_api_label":   "🔑 API",
        "settings_lang_label":  "🌐 Til",
        "settings_id_label":    "🆔 IDS",
        "api_key_saved":        "✅ API kalit saqlandi!",
        "choose_language":      "🌐 Tilni tanlang:",
        "send_api_key":         "🔑 XEVIL API kalitingizni yuboring:",
    },
    "uz_cyrillic": {
        # Dashboard
        "app_name":             "ALPHA",
        "network_name":         "PICK NETWORK",
        "col_crane":            "Кран",
        "col_accounts":         "Аккаунтлар",
        "col_balance":          "Баланс",
        "col_status":           "Ҳолат",
        "total_label":          "Жами",
        "guide_h1":             "1",
        "guide_h2":             "2",
        "guide_h3":             "3",
        "guide_p1":             "🔵🔵🔵🔵🔵",
        "guide_p2":             "⚪⚪⚪⚪⚪",
        "guide_p3":             "🔴🔴🔴🔴🔴",
        # Buttons
        "btn_settings":         "⚙️ Созламалар",
        "btn_refresh":          "🔄 Янгилаш",
        "btn_add_account":      "➕ Аккаунт қўшиш",
        "btn_back":             "◀️ Орқага",
        "btn_cancel":           "❌ Бекор қилиш",
        "btn_api_key":          "🔑 API",
        "btn_language":         "🌐 Тил",
        "btn_support":          "🆘 Ёрдам",
        "btn_main_menu":        "🏠 Бош меню",
        "btn_back_to_crane":    "◀️ {crane}га қайтиш",
        "btn_start_all":        "▶️ Ишга тушириш",
        "btn_stop_all":         "⏹️ Тўхтатиш",
        # Messages
        "not_found":            "Топилмади!",
        "updated":              "♻️ Янгиланди!",
        "cancelled":            "❌ Бекор қилинди.",
        "plain_text_warning":   "⚠️ Илтимос, оддий матн юборинг.",
        "no_api_key":           "⚠️ Аввал Settings → API орқали XEVIL калитини киритинг!",
        "started":              "🚀 {count} та аккаунт ишга туширилди!",
        "stopped":              "⏹️ {count} та аккаунт тўхтатилди!",
        # Crane panel
        "crane_no_accounts":    "⚠️ Аккаунт йўқ — ➕ тугмасини босинг",
        "col_email":            "Email",
        "col_timer":            "Таймер",
        "col_bal":              "Баланс",
        "status_online":        "🟢",
        "status_offline":       "🔴",
        "no_logs":              "⏳ Логлар йўқ...",
        # Add account
        "add_account_title":    "➕ {crane} — Аккаунт қўшиш",
        "field_label":          "#{label}",
        "send_email":           "📧 Email юборинг:",
        "email_line":           "📧 Email: {email}",
        "send_password":        "🔑 Парол юборинг:",
        "password_ok":          "🔑 Парол: ✅",
        "cancel_hint":          "/cancel — бекор қилиш",
        "account_added":        "✅ Аккаунт қўшилди!",
        "start_hint":           "▶️ Ишга тушириш учун бош менюдан тугмани босинг.",
        # Settings
        "settings_title":       "⚙️ Созламалар",
        "settings_api_label":   "🔑 API",
        "settings_lang_label":  "🌐 Тил",
        "settings_id_label":    "🆔 IDS",
        "api_key_saved":        "✅ API калит сақланди!",
        "choose_language":      "🌐 Тилни танланг:",
        "send_api_key":         "🔑 XEVIL API калитингизни юборинг:",
    },
}

def t(chat_id: int, key: str, **kwargs) -> str:
    lang  = get_user_settings(chat_id).get("language", "uz_latin")
    table = TEXTS.get(lang, TEXTS["uz_latin"])
    tmpl  = table.get(key, TEXTS["uz_latin"].get(key, key))
    return tmpl.format(**kwargs) if kwargs else tmpl

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
        self.next_claim           = 0
        self.claim_time_remaining = 0
        self.is_logged_in         = False
        self.fp = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        self.ua = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"
        self.headers = {
            "User-Agent":      self.ua,
            "Accept":          "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With":"XMLHttpRequest",
            "Origin":          f"https://{self.domain}",
            "Referer":         f"https://{self.domain}/login.php",
        }

    def solve_captcha(self) -> str | None:
        try:
            payload = {
                "key":     self.api_key,
                "method":  "turnstile",
                "sitekey": self.config["sitekey"],
                "pageurl": f"https://{self.domain}/faucet.php",
                "json":    1,
            }
            res = requests.post("https://api.sctg.xyz/in.php", data=payload, timeout=30).json()
            if res.get("status") != 1:
                return None
            rid = res.get("request")
            for _ in range(40):
                time.sleep(3)
                g = requests.get(
                    f"https://api.sctg.xyz/res.php?key={self.api_key}&action=get&id={rid}&json=1",
                    timeout=30,
                ).json()
                if g.get("status") == 1:
                    return g.get("request")
                if g.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    break
            return None
        except Exception:
            return None

    def login(self) -> tuple[bool, str]:
        try:
            self.session.cookies.set("fp", self.fp, domain=self.domain)
            self.session.get(f"https://{self.domain}/login.php", headers={"User-Agent": self.ua}, timeout=20)
            csrf = self.session.cookies.get("csrf_cookie_name")
            if not csrf:
                return False, "CSRF Missing"
            token = self.solve_captcha()
            if not token:
                return False, "Captcha Failed"
            payload = {
                "action": "login", "email": self.email, "password": self.password,
                "captcha_type": "3", "c_captcha_response": token, "csrf_test_name": csrf,
                "twofa": "", "g-recaptcha-response": "", "_iconcaptcha-token": "",
                "ic-rq": "", "ic-wid": "", "ic-cid": "", "ic-hp": "",
                "h-captcha-response": "", "pcaptcha_token": "",
            }
            res = self.session.post(f"https://{self.domain}/process.php", data=payload, headers=self.headers, timeout=30).json()
            if res.get("ret") == 1:
                self.is_logged_in = True
                return True, "Success"
            return False, res.get("mes", "Unknown error")
        except Exception as e:
            return False, str(e)

    def update_info(self):
        try:
            res = self.session.get(f"https://{self.domain}/faucet.php", headers={"User-Agent": self.ua}, timeout=20)
            bal = re.search(r'user_balance">([\d.]+)', res.text)
            if bal:
                self.balance = bal.group(1)
            tmr = re.search(r"show_countdown_clock\((\d+)\)", res.text)
            if tmr:
                self.next_claim = int(tmr.group(1))
                self.claim_time_remaining = self.next_claim
            else:
                self.next_claim = 0
                self.claim_time_remaining = 0
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
            data_str = f"{random.randint(100, 200)}:{random.randint(10, 50)}:{ts}"
            xk       = self.config["xor_key"]
            hashed   = base64.b64encode(
                "".join(chr(ord(c) ^ ord(xk[i % len(xk)])) for i, c in enumerate(data_str)).encode()
            ).decode()
            payload = {
                "action": "claim_hourly_faucet", "hash": hashed,
                "captcha_type": "3", "c_captcha_response": token, "csrf_test_name": csrf,
            }
            res = self.session.post(f"https://{self.domain}/process.php", data=payload, headers=self.headers, timeout=30).json()
            if res.get("ret") == 1:
                if "balance" in res:
                    self.balance = str(float(res["balance"]) / 100_000_000)
                self.update_info()
                return True, res.get("mes", "Success")
            return False, res.get("mes", "Failed")
        except Exception as e:
            return False, str(e)

# ─── WORKER THREAD ──────────────────────────────────────────────────────────
STOP_EVENTS: dict[str, threading.Event] = {}

def pick_bot_worker(crane_name: str, account_index: int, stop_event: threading.Event, chat_id: int):
    crane = next((c for c in CRANES if c["name"] == crane_name), None)
    if not crane:
        return
    account = crane["accounts"][account_index]
    config  = crane["config"]
    api_key = get_user_settings(chat_id).get("api_key")
    if not api_key:
        _log(crane, f"❌ API kalit yo'q: {account['email']}")
        return

    pick = PickBot(account["email"], account["password"], api_key, config)
    success, msg = pick.login()
    if success:
        _log(crane, f"✅ Login: {account['email']}")
        account["active"] = True
    else:
        _log(crane, f"❌ Login xato ({account['email']}): {msg}")
        account["active"] = False
        return

    while not stop_event.is_set():
        try:
            pick.update_info()
            account["claim_time_remaining"] = pick.claim_time_remaining
            if pick.claim_time_remaining <= 0:
                _log(crane, f"⏳ Claiming {config['coin']} — {account['email']}...")
                ok, msg = pick.claim()
                if ok:
                    account["balance"] = float(pick.balance)
                    crane["claims"] = crane.get("claims", 0) + 1
                    _log(crane, f"✅ {account['email']}: {config['coin']} olindi")
                else:
                    _log(crane, f"❌ {account['email']}: {msg}")
                pick.claim_time_remaining = 3600
                account["next_claim_at"] = datetime.now(timezone.utc) + timedelta(minutes=60)
            time.sleep(1)
        except Exception as e:
            _log(crane, f"⚠️ {account['email']}: {e}")
            time.sleep(10)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_crane(name: str) -> dict | None:
    return next((c for c in CRANES if c["name"] == name), None)

def _log(crane: dict, text: str):
    crane.setdefault("logs", []).append({"time": datetime.now().strftime("%H:%M:%S"), "text": text})
    crane["logs"] = crane["logs"][-20:]

def fmt_timer(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"

def get_countdown(acc: dict) -> str:
    nca = acc.get("next_claim_at")
    if not nca:
        return "--:--"
    rem = (nca - datetime.now(timezone.utc)).total_seconds()
    if rem <= 0:
        return "Ready"
    return fmt_timer(rem)

# ─── KEYBOARDS ───────────────────────────────────────────────────────────────
def cancel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_add", style=ButtonStyle.DANGER)]
    ])

def settings_cancel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_settings", style=ButtonStyle.DANGER)]
    ])

def build_language_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"lang_{code}")]
        for code, name in LANGUAGES.items()
    ])

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
        InlineKeyboardButton(text=t(chat_id, "btn_start_all"), callback_data="start_all", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text=t(chat_id, "btn_stop_all"),  callback_data="stop_all",  style=ButtonStyle.DANGER),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_settings"), callback_data="settings", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text=t(chat_id, "btn_refresh"),  callback_data="refresh",  style=ButtonStyle.SUCCESS),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_support"), url="https://t.me/alphadevlab", style=ButtonStyle.DANGER),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_crane_keyboard(chat_id: int, crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_add_account"), callback_data=f"add_account_{crane_name}", style=ButtonStyle.DANGER)],
        [
            InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=t(chat_id, "btn_back"),    callback_data="back_main",             style=ButtonStyle.SUCCESS),
        ],
    ])

def build_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    s = get_user_settings(chat_id)
    api_style = ButtonStyle.SUCCESS if s.get("api_key") else ButtonStyle.DANGER
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_api_key"),  callback_data="settings_api_key",  style=api_style)],
        [InlineKeyboardButton(text=t(chat_id, "btn_language"), callback_data="settings_language", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_back"),     callback_data="back_main",         style=ButtonStyle.SUCCESS)],
    ])

# ─── RICH MESSAGE BUILDERS ────────────────────────────────────────────────────
def _cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
    return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)


def build_main_rich_message(chat_id: int) -> InputRichMessage:
    # ── Sarlavha (ALPHA) ──
    title_table = InputRichBlockTable(
        cells=[[_cell(t(chat_id, "app_name"), header=True, align="center")]],
        is_bordered=True, is_striped=True,
    )

    # ── PICK NETWORK + rangli jadval ──
    network_table = InputRichBlockTable(
        cells=[
            [
                _cell(t(chat_id, "guide_h1"), header=True, align="center"),
                _cell(t(chat_id, "guide_h2"), header=True, align="center"),
                _cell(t(chat_id, "guide_h3"), header=True, align="center"),
            ],
            [
                _cell(t(chat_id, "guide_p1"), align="center"),
                _cell(t(chat_id, "guide_p2"), align="center"),
                _cell(t(chat_id, "guide_p3"), align="center"),
            ],
        ],
        is_bordered=True, is_striped=True,
    )

    # ── Kranlar umumiy statistika jadvali ──
    # Sarlavha qatori
    stats_rows = [[
        _cell(t(chat_id, "col_crane"),    header=True, align="center"),
        _cell(t(chat_id, "col_accounts"), header=True, align="center"),
        _cell(t(chat_id, "col_balance"),  header=True, align="right"),
    ]]
    total_accs   = 0
    total_bal    = 0.0
    for c in CRANES:
        accs = c.get("accounts", [])
        bal  = sum(a.get("balance", 0.0) for a in accs)
        active = sum(1 for a in accs if a.get("active", False))
        total_accs += len(accs)
        total_bal  += bal
        status = "🟢" if c["active"] else "🔴"
        stats_rows.append([
            _cell(f"{c['emoji']} {c['name']} {status}", align="center"),
            _cell(f"{active}/{len(accs)}",              align="center"),
            _cell(f"{bal:.6f}",                         align="right"),
        ])
    # Jami qatori
    stats_rows.append([
        _cell(t(chat_id, "total_label"), header=True, align="center"),
        _cell(str(total_accs),           header=True, align="center"),
        _cell(f"{total_bal:.6f}",        header=True, align="right"),
    ])

    stats_table = InputRichBlockTable(
        cells=stats_rows,
        is_bordered=True, is_striped=True,
    )

    return InputRichMessage(blocks=[title_table, network_table, stats_table])


def build_crane_rich_message(chat_id: int, crane: dict) -> InputRichMessage:
    config   = crane.get("config", {})
    accounts = crane.get("accounts", [])
    coin     = config.get("coin", "")
    active_c = sum(1 for a in accounts if a.get("active", False))
    claims   = crane.get("claims", 0)

    # ── Sarlavha ──
    title_table = InputRichBlockTable(
        cells=[[_cell(f"{crane['emoji']} {crane['name']} ({coin})", header=True, align="center")]],
        is_bordered=True, is_striped=True,
    )

    # ── Mini statistika ──
    mini_table = InputRichBlockTable(
        cells=[
            [
                _cell("Akkauntlar", header=True, align="center"),
                _cell("Faol",       header=True, align="center"),
                _cell("Claim",      header=True, align="center"),
            ],
            [
                _cell(str(len(accounts)), align="center"),
                _cell(str(active_c),      align="center"),
                _cell(str(claims),        align="center"),
            ],
        ],
        is_bordered=True, is_striped=True,
    )

    blocks = [title_table, mini_table]

    # ── Akkauntlar jadvali ──
    if accounts:
        rows = [[
            _cell(t(chat_id, "col_email"), header=True, align="left"),
            _cell(t(chat_id, "col_timer"), header=True, align="center"),
            _cell(t(chat_id, "col_bal"),   header=True, align="right"),
        ]]
        for acc in accounts:
            email   = acc.get("email", "")[:16]
            balance = acc.get("balance", 0.0)
            cd      = get_countdown(acc)
            status  = t(chat_id, "status_online") if acc.get("active") else t(chat_id, "status_offline")
            rows.append([
                _cell(f"{status} {email}", align="left"),
                _cell(cd,                  align="center"),
                _cell(f"{balance:.6f}",    align="right"),
            ])
        blocks.append(InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True))
    else:
        blocks.append(InputRichBlockPreformatted(text=t(chat_id, "crane_no_accounts")))

    # ── Loglar ──
    logs = crane.get("logs", [])
    log_text = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-6:]) if logs else t(chat_id, "no_logs")
    blocks.append(InputRichBlockPreformatted(text=log_text))

    return InputRichMessage(blocks=blocks)


def build_settings_rich_message(chat_id: int) -> InputRichMessage:
    s       = get_user_settings(chat_id)
    raw_key = s.get("api_key")
    api_val = (raw_key[:10] if raw_key else "----------")
    lang_full = LANGUAGES.get(s.get("language", "uz_latin"), "")
    lang_val  = (lang_full.split(" ", 1)[1] if " " in lang_full else lang_full)[:10]
    short_id  = str(chat_id % 10_000_000_000).zfill(10)

    title_table = InputRichBlockTable(
        cells=[[_cell(t(chat_id, "settings_title"), header=True, align="center")]],
        is_bordered=True, is_striped=True,
    )
    info_table = InputRichBlockTable(
        cells=[
            [
                _cell(t(chat_id, "settings_api_label"),  header=True, align="center"),
                _cell(t(chat_id, "settings_lang_label"), header=True, align="center"),
                _cell(t(chat_id, "settings_id_label"),   header=True, align="center"),
            ],
            [
                _cell(api_val,  align="center"),
                _cell(lang_val, align="center"),
                _cell(short_id, align="center"),
            ],
        ],
        is_bordered=True, is_striped=True,
    )
    return InputRichMessage(blocks=[title_table, info_table])

# ─── BOT VA DISPATCHER ────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

active_messages: dict[int, int]  = {}
active_screen:   dict[int, str]  = {}


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
            active_messages.pop(chat_id, None)
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
            active_messages.pop(chat_id, None)
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    active_messages[chat_id] = msg.message_id


async def delete_silently(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


async def require_text(message: Message) -> str | None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return None
    return message.text.strip()

# ─── AUTO REFRESH ─────────────────────────────────────────────────────────────
async def auto_refresh():
    while True:
        await asyncio.sleep(3)
        for chat_id, msg_id in list(active_messages.items()):
            screen = active_screen.get(chat_id, "")
            try:
                if screen == "dashboard":
                    await bot.edit_message_text(
                        chat_id=chat_id, message_id=msg_id,
                        rich_message=build_main_rich_message(chat_id),
                        reply_markup=build_keyboard(chat_id),
                    )
                elif screen.startswith("crane:"):
                    crane_name = screen.split(":", 1)[1]
                    crane = get_crane(crane_name)
                    if crane:
                        await bot.edit_message_text(
                            chat_id=chat_id, message_id=msg_id,
                            rich_message=build_crane_rich_message(chat_id, crane),
                            reply_markup=build_crane_keyboard(chat_id, crane_name),
                        )
            except Exception:
                pass

# ─── HANDLERS ─────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
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


@dp.callback_query(F.data == "start_all")
async def cb_start_all(call: CallbackQuery):
    chat_id = call.message.chat.id
    api_key = get_user_settings(chat_id).get("api_key")
    if not api_key:
        await call.answer(t(chat_id, "no_api_key"), show_alert=True)
        return
    started = 0
    for crane in CRANES:
        for idx, acc in enumerate(crane.get("accounts", [])):
            key = f"{crane['name']}_{idx}"
            if key not in STOP_EVENTS or STOP_EVENTS[key].is_set():
                ev = threading.Event()
                STOP_EVENTS[key] = ev
                Thread(target=pick_bot_worker, args=(crane["name"], idx, ev, chat_id), daemon=True).start()
                started += 1
                crane["active"] = True
                acc["active"] = True
                _log(crane, f"🚀 Ishga tushirildi: {acc['email']}")
    await call.answer(t(chat_id, "started", count=started))
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.callback_query(F.data == "stop_all")
async def cb_stop_all(call: CallbackQuery):
    chat_id = call.message.chat.id
    stopped = 0
    for key in list(STOP_EVENTS):
        STOP_EVENTS[key].set()
        del STOP_EVENTS[key]
        stopped += 1
    for crane in CRANES:
        crane["active"] = False
        for acc in crane.get("accounts", []):
            acc["active"] = False
        _log(crane, "⏹️ Barcha akkauntlar to'xtatildi")
    await call.answer(t(chat_id, "stopped", count=stopped))
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("add_account_", "")
    crane = get_crane(crane_name)
    chat_id = call.message.chat.id
    if not crane:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return
    acc_num = len(crane["accounts"]) + 1
    label   = str(acc_num)
    await state.set_state(AddAccount.email)
    await state.update_data(crane_name=crane_name, label=label)
    active_screen[chat_id] = "add_account"
    text = (
        f"{t(chat_id, 'add_account_title', crane=crane_name)}\n\n"
        f"{t(chat_id, 'field_label', label=label)}\n\n"
        f"{t(chat_id, 'send_email')}\n\n"
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
    await state.update_data(password=password)
    await delete_silently(message)
    await _finish_add_account(message, state)


async def _finish_add_account(message: Message, state: FSMContext):
    data       = await state.get_data()
    crane_name = data["crane_name"]
    label      = data["label"]
    email      = data["email"]
    password   = data["password"]
    crane = get_crane(crane_name)
    if not crane:
        await state.clear()
        return
    new_acc = {
        "label":      label,
        "email":      email,
        "password":   password,
        "active":     False,
        "balance":    0.0,
        "next_claim_at": datetime.now(timezone.utc) + timedelta(minutes=60),
        "claim_time_remaining": 3600,
    }
    crane["accounts"].append(new_acc)
    _log(crane, f"📝 Qo'shildi: {email}")
    chat_id = message.chat.id
    summary = (
        f"{t(chat_id, 'account_added')}\n\n"
        f"{crane['emoji']} {crane_name} #{label}\n"
        f"{t(chat_id, 'email_line', email=email)}\n"
        f"{t(chat_id, 'password_ok')}\n\n"
        f"{t(chat_id, 'start_hint')}"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_back_to_crane", crane=crane_name), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_main_menu"), callback_data="back_main")],
    ])
    await state.clear()
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
    await show_text(chat_id, f"{t(chat_id, 'send_api_key')}\n\n{t(chat_id, 'cancel_hint')}", settings_cancel_keyboard(chat_id))
    await call.answer()


@dp.message(SettingsFSM.api_key)
async def fsm_settings_api_key(message: Message, state: FSMContext):
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
    code    = call.data.replace("lang_", "")
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

# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def main():
    asyncio.create_task(auto_refresh())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
