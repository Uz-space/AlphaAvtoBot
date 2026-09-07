import asyncio
import logging
import base64
import random
import re
import string
import time
import threading
from datetime import datetime, timezone
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

import requests as req_lib

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"

# ─── Kran konfiguratsiyasi (per-user) ───────────────────────────────────────
# CRANES faqat nom/emoji — ma'lumotlar USER_DATA ichida saqlanadi
CRANE_DEFS = [
    {"name": "TronPick", "domain": "tronpick.io"},
    {"name": "LitePick", "domain": "litepick.io"},
    {"name": "DogePick", "domain": "dogepick.io"},
]

# ─── Per-user ma'lumotlar ────────────────────────────────────────────────────
# USER_DATA[chat_id] = {
#   "settings": {"api_key": str|None, "language": str},
#   "cranes": {
#     "TronPick": {"accounts": [account_dict, ...], "logs": [...]},
#     ...
#   }
# }
USER_DATA: dict[int, dict] = {}

# ─── Ishlaydigan botlar (threading) ─────────────────────────────────────────
# RUNNING_BOTS[chat_id][crane_name][email] = {"bot": TronPickBot, "thread": Thread, "stop": Event}
RUNNING_BOTS: dict[int, dict] = {}

# ─── FSM States ──────────────────────────────────────────────────────────────
class AddAccount(StatesGroup):
    email    = State()
    password = State()

class SettingsFSM(StatesGroup):
    api_key = State()

# ─── LANGUAGES ───────────────────────────────────────────────────────────────
LANGUAGES = {
    "uz_latin":   "🇺🇿 O'zbekcha (lotin)",
    "uz_cyrillic": "🇺🇿 Ўзбекча (кирилл)",
}

# ─── User data helpers ────────────────────────────────────────────────────────
def get_user_data(chat_id: int) -> dict:
    if chat_id not in USER_DATA:
        USER_DATA[chat_id] = {
            "settings": {"api_key": None, "language": "uz_latin"},
            "cranes": {d["name"]: {"accounts": [], "logs": []} for d in CRANE_DEFS},
        }
    return USER_DATA[chat_id]

def get_user_settings(chat_id: int) -> dict:
    return get_user_data(chat_id)["settings"]

def get_user_crane(chat_id: int, crane_name: str) -> dict:
    return get_user_data(chat_id)["cranes"][crane_name]

def get_crane_domain(crane_name: str) -> str:
    for d in CRANE_DEFS:
        if d["name"] == crane_name:
            return d["domain"]
    return "tronpick.io"

# ─── TARJIMALAR ──────────────────────────────────────────────────────────────
TEXTS = {
    "uz_latin": {
        "dashboard_title": "ALPHA",
        "guide_header1": "1",
        "guide_header_mid": "•",
        "guide_header2": "2",
        "guide_part1": "🔵🔵🔵🔵🔵",
        "guide_part_mid": "⚪⚪⚪⚪⚪",
        "guide_part2": "🔴🔴🔴🔴🔴",
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
        "crane_control_panel": "{name} - Boshqaruv paneli",
        "crane_claims_balance": "📊 {claims} ta olish | 💰 {balance}",
        "crane_active_accounts": "Faol akkauntlar ({active}/{total})",
        "crane_no_accounts": "Faol akkaunt yo'q - qo'shish uchun + bosing",
        "crane_trx_stats_heading": "📊 TRX Statistikasi",
        "crane_live_logs_heading": "📡 Jonli loglar",
        "crane_no_claims_yet": "⏳ Hali olishlar yo'q...",
        "stats_col_account": "Akkaunt",
        "stats_col_next_claim": "Keyingi olish",
        "stats_col_balance": "Balans",
        "add_account_title": "Akkaunt qo'shish - {crane}",
        "field_label": "Belgi: {label}",
        "add_account_send_email": "Akkaunt emailini yuboring:",
        "email_line": "Email: {email}",
        "send_password": "Endi parolni yuboring:",
        "password_line": "Parol: ✅",
        "cancel_hint": "/cancel — bekor qilish uchun.",
        "account_added": "Akkaunt qo'shildi!",
        "no_api_key": "⚠️ Avval API kalitni sozlamalarda kiriting!",
        "settings_title": "⚙️ Sozlamalar",
        "settings_api_key_line": "🔑 API Kalit: {status}",
        "settings_language_line": "🌐 Til: {lang}",
        "api_key_set": "✅ O'rnatilgan",
        "api_key_not_set": "❌ O'rnatilmagan",
        "send_api_key": "🔑 API kalitingizni yuboring:",
        "choose_language": "🌐 Tilni tanlang:",
        "login_started": "🔄 Login jarayoni boshlandi...",
        "login_success": "✅ Login muvaffaqiyatli!",
        "login_failed": "❌ Login muvaffaqiyatsiz: {msg}",
    },
    "uz_cyrillic": {
        "dashboard_title": "ALPHA",
        "guide_header1": "1",
        "guide_header_mid": "•",
        "guide_header2": "2",
        "guide_part1": "🔵🔵🔵🔵🔵",
        "guide_part_mid": "⚪⚪⚪⚪⚪",
        "guide_part2": "🔴🔴🔴🔴🔴",
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
        "crane_control_panel": "{name} - Бошқарув панели",
        "crane_claims_balance": "📊 {claims} та олиш | 💰 {balance}",
        "crane_active_accounts": "Фаол аккаунтлар ({active}/{total})",
        "crane_no_accounts": "Фаол аккаунт йўқ - қўшиш учун + босинг",
        "crane_trx_stats_heading": "📊 TRX Статистикаси",
        "crane_live_logs_heading": "📡 Жонли логлар",
        "crane_no_claims_yet": "⏳ Ҳали олишлар йўқ...",
        "stats_col_account": "Аккаунт",
        "stats_col_next_claim": "Кейинги олиш",
        "stats_col_balance": "Баланс",
        "add_account_title": "Аккаунт қўшиш - {crane}",
        "field_label": "Белги: {label}",
        "add_account_send_email": "Аккаунт email'ини юборинг:",
        "email_line": "Email: {email}",
        "send_password": "Энди паролни юборинг:",
        "password_line": "Парол: ✅",
        "cancel_hint": "/cancel — бекор қилиш учун.",
        "account_added": "Аккаунт қўшилди!",
        "no_api_key": "⚠️ Аввал API калитни созламаларда киритинг!",
        "settings_title": "⚙️ Созламалар",
        "settings_api_key_line": "🔑 API Калит: {status}",
        "settings_language_line": "🌐 Тил: {lang}",
        "api_key_set": "✅ Ўрнатилган",
        "api_key_not_set": "❌ Ўрнатилмаган",
        "send_api_key": "🔑 API калитингизни юборинг:",
        "choose_language": "🌐 Тилни танланг:",
        "login_started": "🔄 Login жараёни бошланди...",
        "login_success": "✅ Login муваффақиятли!",
        "login_failed": "❌ Login муваффақиятсиз: {msg}",
    },
}


def t(chat_id: int, key: str, **kwargs) -> str:
    lang = get_user_settings(chat_id).get("language", "uz_latin")
    table = TEXTS.get(lang, TEXTS["uz_latin"])
    template = table.get(key, TEXTS["uz_latin"].get(key, key))
    return template.format(**kwargs) if kwargs else template


# ─── TronPick Bot logikasi ────────────────────────────────────────────────────
def generate_fp(length: int = 16) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


class TronPickBot:
    def __init__(self, email: str, password: str, api_key: str, domain: str, crane_data: dict, chat_id: int):
        self.session = req_lib.Session()
        self.email = email
        self.password = password
        self.api_key = api_key
        self.domain = domain
        self.crane_data = crane_data  # reference to user's crane dict
        self.chat_id = chat_id
        self.fp = generate_fp()
        self.is_logged_in = False
        self.balance = "0.000000"
        self.level = "Stone"
        self.claim_time_remaining = 0
        self.ua = "Mozilla/5.0 (Linux; Android 12; V2029 Build/SP1A.210812.003) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.164 Mobile Safari/537.36"
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": f"https://{self.domain}",
            "Referer": f"https://{self.domain}/login.php",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def _add_log(self, text: str):
        self.crane_data.setdefault("logs", []).append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": f"[{self.email.split('@')[0]}] {text}",
        })
        self.crane_data["logs"] = self.crane_data["logs"][-20:]
        # Akkauntga ham yoz
        for acc in self.crane_data.get("accounts", []):
            if acc.get("email") == self.email:
                acc["last_log"] = text
                break

    def solve_captcha(self) -> str | None:
        try:
            self._add_log("Captcha yuborilmoqda...")
            payload = {
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": "0x4AAAAAAAW74HiAaujGhyeV",
                "pageurl": f"https://{self.domain}/faucet.php",
                "json": 1,
            }
            res = req_lib.post("https://api.sctg.xyz/in.php", data=payload, timeout=30).json()
            if res.get("status") != 1:
                self._add_log(f"Captcha xato: {res.get('request')}")
                return None

            rid = res.get("request")
            for _ in range(40):
                time.sleep(3)
                g = req_lib.get(
                    f"https://api.sctg.xyz/res.php?key={self.api_key}&action=get&id={rid}&json=1",
                    timeout=30,
                ).json()
                if g.get("status") == 1:
                    self._add_log("Captcha hal qilindi!")
                    return g.get("request")
                if g.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    self._add_log("Captcha hal qilib bo'lmadi")
                    break
            return None
        except Exception as e:
            self._add_log(f"Captcha xatosi: {e}")
            return None

    def login(self) -> tuple[bool, str]:
        try:
            self._add_log(f"{self.domain} serveriga ulanmoqda...")
            self.session.cookies.set("fp", self.fp, domain=self.domain)
            try:
                self.session.get(f"https://{self.domain}/login.php", headers={"User-Agent": self.ua}, timeout=20)
            except Exception:
                self.session.get(f"https://{self.domain}/login.php", headers={"User-Agent": self.ua}, timeout=30)

            csrf = self.session.cookies.get("csrf_cookie_name")
            if not csrf:
                self._add_log("CSRF topilmadi")
                return False, "CSRF Missing"

            token = self.solve_captcha()
            if not token:
                return False, "Captcha Failed"

            payload = {
                "action": "login",
                "email": self.email,
                "password": self.password,
                "captcha_type": "3",
                "c_captcha_response": token,
                "csrf_test_name": csrf,
                "twofa": "",
                "g-recaptcha-response": "",
                "_iconcaptcha-token": "",
                "ic-rq": "", "ic-wid": "", "ic-cid": "", "ic-hp": "",
                "h-captcha-response": "", "pcaptcha_token": "",
            }
            res = self.session.post(
                f"https://{self.domain}/process.php",
                data=payload, headers=self.headers, timeout=30
            ).json()

            if res.get("ret") == 1:
                self.is_logged_in = True
                self._add_log("Login muvaffaqiyatli!")
                self._update_account_status()
                return True, "Success"

            msg = res.get("mes", "Unknown error")
            self._add_log(f"Login xato: {msg}")
            return False, msg
        except Exception as e:
            self._add_log(f"Login xatosi: {e}")
            return False, str(e)

    def update_info(self):
        try:
            res = self.session.get(f"https://{self.domain}/faucet.php", headers={"User-Agent": self.ua}, timeout=20)
            bal = re.search(r'user_balance">([\d.]+)', res.text)
            if bal:
                self.balance = bal.group(1)
            lvl = re.search(r'Your level is\s*<b>(.*?)</b>', res.text)
            if lvl:
                self.level = lvl.group(1)
            tmr = re.search(r'show_countdown_clock\((\d+)\)', res.text)
            if tmr:
                self.claim_time_remaining = int(tmr.group(1))
            else:
                self.claim_time_remaining = 0
            self._update_account_status()
        except Exception:
            pass

    def _update_account_status(self):
        """Akkaunt ma'lumotlarini USER_DATA ga sinxron qiladi"""
        for acc in self.crane_data.get("accounts", []):
            if acc.get("email") == self.email:
                acc["balance"] = float(self.balance) if self.balance else 0.0
                acc["claim_time_remaining"] = self.claim_time_remaining
                acc["is_logged_in"] = self.is_logged_in
                acc["level"] = self.level
                break

    def claim(self):
        try:
            self._add_log("Claim boshlandi...")
            token = self.solve_captcha()
            if not token:
                return

            csrf = self.session.cookies.get("csrf_cookie_name")
            ts = int(time.time())
            data_str = f"{random.randint(100,200)}:{random.randint(10,50)}:{ts}"
            xor_key = "0542f6c18bc7906d742a8401d0b5ef7f50ee304bff4f032348a4ceb3fd2d6bb1"
            hashed = base64.b64encode(
                "".join(chr(ord(c) ^ ord(xor_key[i % len(xor_key)])) for i, c in enumerate(data_str)).encode()
            ).decode()

            payload = {
                "action": "claim_hourly_faucet",
                "hash": hashed,
                "captcha_type": "3",
                "c_captcha_response": token,
                "csrf_test_name": csrf,
            }
            res = self.session.post(
                f"https://{self.domain}/process.php",
                data=payload, headers=self.headers, timeout=30
            ).json()

            if res.get("ret") == 1:
                self._add_log(f"✅ Claim: {res.get('mes')}")
                if "balance" in res:
                    self.balance = str(float(res["balance"]) / 100000000)
                # crane darajasidagi claims sonini oshiramiz
                self.crane_data["claims"] = self.crane_data.get("claims", 0) + 1
            else:
                self._add_log(f"❌ Claim xato: {res.get('mes')}")

            self.update_info()
        except Exception as e:
            self._add_log(f"Claim xatosi: {e}")


def account_worker(tron_bot: TronPickBot, stop_event: threading.Event):
    """Har bir akkaunt uchun alohida thread"""
    while not stop_event.is_set():
        try:
            if tron_bot.claim_time_remaining > 0:
                tron_bot.claim_time_remaining -= 1
                tron_bot._update_account_status()

            if tron_bot.claim_time_remaining <= 0:
                tron_bot.update_info()
                if tron_bot.claim_time_remaining <= 0:
                    tron_bot.claim()
                    tron_bot.update_info()

            time.sleep(1)
        except Exception as e:
            tron_bot._add_log(f"Worker xatosi: {e}")
            time.sleep(5)


def start_account_worker(chat_id: int, crane_name: str, email: str):
    """Akkaunt uchun TronPickBot va thread ishga tushiradi"""
    user_data = get_user_data(chat_id)
    api_key = user_data["settings"].get("api_key")
    if not api_key:
        return

    crane_data = user_data["cranes"][crane_name]
    domain = get_crane_domain(crane_name)

    # Akkaunt ma'lumotlarini topamiz
    acc = next((a for a in crane_data["accounts"] if a["email"] == email), None)
    if not acc:
        return

    tron_bot = TronPickBot(
        email=email,
        password=acc["password"],
        api_key=api_key,
        domain=domain,
        crane_data=crane_data,
        chat_id=chat_id,
    )

    stop_event = threading.Event()

    def run():
        success, msg = tron_bot.login()
        if not success:
            crane_data.setdefault("logs", []).append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "text": f"[{email.split('@')[0]}] ❌ Login xato: {msg}",
            })
            return
        tron_bot.update_info()
        account_worker(tron_bot, stop_event)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    RUNNING_BOTS.setdefault(chat_id, {}).setdefault(crane_name, {})[email] = {
        "bot": tron_bot,
        "thread": thread,
        "stop": stop_event,
    }


def stop_account_worker(chat_id: int, crane_name: str, email: str):
    try:
        RUNNING_BOTS[chat_id][crane_name][email]["stop"].set()
    except KeyError:
        pass


# ─── Helpers ─────────────────────────────────────────────────────────────────
def format_countdown(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def get_account_countdown(acc: dict) -> str:
    remaining = acc.get("claim_time_remaining", 0)
    if remaining <= 0:
        return "Ready"
    return format_countdown(remaining)


def cancel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_add")]
    ])


def settings_cancel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_settings")]
    ])


# ─── Rich message builders ────────────────────────────────────────────────────
def build_main_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left", colspan: int | None = None) -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header, colspan=colspan)

    alpha_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "dashboard_title"), header=True, align="center")]],
        is_bordered=True, is_striped=True,
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
        is_bordered=True, is_striped=True,
    )

    return InputRichMessage(blocks=[alpha_table, guide_table])


def build_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for c in CRANE_DEFS:
        btn = InlineKeyboardButton(
            text=c["name"],
            callback_data=f"crane_{c['name']}",
            style=ButtonStyle.PRIMARY,
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(
        text=t(chat_id, "btn_support"), url="https://t.me/alphadevlab", style=ButtonStyle.DANGER,
    )])
    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_settings"), callback_data="settings", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data="refresh", style=ButtonStyle.SUCCESS),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_crane_rich_message(chat_id: int, crane_name: str) -> InputRichMessage:
    crane_data = get_user_crane(chat_id, crane_name)
    accounts = crane_data.get("accounts", [])
    acc_count = len(accounts)
    active_count = sum(1 for a in accounts if a.get("is_logged_in", False))
    claims = crane_data.get("claims", 0)

    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    blocks = [
        InputRichBlockParagraph(text=[RichTextBold(text=f"{crane_name} - Boshqaruv paneli")]),
        InputRichBlockParagraph(text=f"📊 {claims} ta olish"),
        InputRichBlockSectionHeading(text=t(chat_id, "crane_active_accounts", active=active_count, total=acc_count), size=4),
    ]

    if accounts:
        # Akkauntlar jadvali
        header_row = [
            cell(t(chat_id, "stats_col_account"), header=True),
            cell(t(chat_id, "stats_col_next_claim"), header=True, align="center"),
            cell(t(chat_id, "stats_col_balance"), header=True, align="right"),
        ]
        data_rows = []
        for acc in accounts:
            email_short = acc.get("email", "")[:15]
            balance = acc.get("balance", 0.0)
            countdown = get_account_countdown(acc)
            status = "🟢" if acc.get("is_logged_in") else "🔴"
            data_rows.append([
                cell(f"{status} {email_short}"),
                cell(countdown, align="center"),
                cell(f"{balance:.6f}", align="right"),
            ])

        accs_table = InputRichBlockTable(
            cells=[header_row, *data_rows],
            is_bordered=True, is_striped=True,
        )
        blocks.append(accs_table)
    else:
        blocks.append(InputRichBlockParagraph(text=t(chat_id, "crane_no_accounts")))

    blocks.append(InputRichBlockSectionHeading(text=t(chat_id, "crane_live_logs_heading"), size=4))

    logs = crane_data.get("logs", [])
    log_body = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-8:]) if logs else t(chat_id, "crane_no_claims_yet")
    blocks.append(InputRichBlockPreformatted(text=log_body))

    return InputRichMessage(blocks=blocks)


def build_crane_keyboard(chat_id: int, crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_add_account"), callback_data=f"add_account_{crane_name}", style=ButtonStyle.DANGER)],
        [
            InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=t(chat_id, "btn_back"), callback_data="back_main", style=ButtonStyle.SUCCESS),
        ],
    ])


def build_settings_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    s = get_user_settings(chat_id)
    raw_api_key = s.get("api_key")
    api_val = raw_api_key[:10] if raw_api_key else "----------"

    lang_full = LANGUAGES.get(s.get("language", "uz_latin"), "")
    lang_val = (lang_full.split(" ", 1)[1] if " " in lang_full else lang_full)[:10]
    short_id = str(chat_id % 10000000000).zfill(10)

    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "settings_title"), header=True, align="center")]],
        is_bordered=True, is_striped=True,
    )
    info_table = InputRichBlockTable(
        cells=[
            [
                cell(t(chat_id, "settings_api_label"), header=True, align="center"),
                cell(t(chat_id, "btn_language"), header=True, align="center"),
                cell(t(chat_id, "settings_id_label"), header=True, align="center"),
            ],
            [
                cell(api_val, align="center"),
                cell(lang_val, align="center"),
                cell(short_id, align="center"),
            ],
        ],
        is_bordered=True, is_striped=True,
    )
    return InputRichMessage(blocks=[title_table, info_table])


def build_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    api_style = ButtonStyle.SUCCESS if get_user_settings(chat_id).get("api_key") else ButtonStyle.DANGER
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_api_key"), callback_data="settings_api_key", style=api_style)],
        [InlineKeyboardButton(text=t(chat_id, "btn_language"), callback_data="settings_language", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_back"), callback_data="back_main", style=ButtonStyle.SUCCESS)],
    ])


def build_language_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"lang_{code}")]
        for code, name in LANGUAGES.items()
    ])


# ─── Bot va Dispatcher ───────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

active_messages: dict[int, int] = {}
active_screen: dict[int, str] = {}


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


async def require_text(message: Message) -> str | None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return None
    return message.text.strip()


# ─── Auto refresh ─────────────────────────────────────────────────────────────
async def auto_refresh():
    while True:
        await asyncio.sleep(1)
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
                    await bot.edit_message_text(
                        chat_id=chat_id, message_id=message_id,
                        rich_message=build_crane_rich_message(chat_id, crane_name),
                        reply_markup=build_crane_keyboard(chat_id, crane_name),
                    )
            except Exception:
                pass


# ─── /start ───────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    get_user_data(chat_id)  # init
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


# ─── /cancel ──────────────────────────────────────────────────────────────────
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
    elif crane_name:
        active_screen[chat_id] = f"crane:{crane_name}"
        await show_rich(chat_id, build_crane_rich_message(chat_id, crane_name), build_crane_keyboard(chat_id, crane_name))
    else:
        active_screen[chat_id] = "dashboard"
        await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


# ─── Refresh ──────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "refresh")
async def cb_refresh(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer(t(chat_id, "updated"))


# ─── Back to main ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer()


# ─── Crane panel ──────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("crane_"))
async def cb_crane(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("crane_", "")
    chat_id = call.message.chat.id
    if not any(d["name"] == crane_name for d in CRANE_DEFS):
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return
    active_screen[chat_id] = f"crane:{crane_name}"
    await show_rich(chat_id, build_crane_rich_message(chat_id, crane_name), build_crane_keyboard(chat_id, crane_name))
    await call.answer()


# ─── Add Account ──────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("add_account_", "")
    chat_id = call.message.chat.id

    api_key = get_user_settings(chat_id).get("api_key")
    if not api_key:
        await call.answer(t(chat_id, "no_api_key"), show_alert=True)
        return

    crane_data = get_user_crane(chat_id, crane_name)
    acc_num = len(crane_data["accounts"]) + 1
    label = f"Account {acc_num}"

    await state.set_state(AddAccount.email)
    await state.update_data(crane_name=crane_name, label=label)
    active_screen[chat_id] = "add_account"

    text = (
        f"{t(chat_id, 'add_account_title', crane=crane_name)}\n\n"
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
    await state.update_data(password=password)
    await delete_silently(message)
    await _finish_add_account(message, state)


async def _finish_add_account(message: Message, state: FSMContext):
    data = await state.get_data()
    crane_name = data["crane_name"]
    label = data["label"]
    email = data["email"]
    password = data["password"]
    chat_id = message.chat.id

    crane_data = get_user_crane(chat_id, crane_name)

    new_acc = {
        "label": label,
        "email": email,
        "password": password,
        "is_logged_in": False,
        "balance": 0.0,
        "claim_time_remaining": 0,
        "level": "Stone",
        "last_log": "Ulanmoqda...",
    }
    crane_data["accounts"].append(new_acc)
    crane_data.setdefault("logs", []).append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "text": f"[{email.split('@')[0]}] Akkaunt qo'shildi, login boshlandi...",
    })

    await state.clear()
    active_screen[chat_id] = f"crane:{crane_name}"

    summary = (
        f"{t(chat_id, 'account_added')}\n\n"
        f"{crane_name} #{len(crane_data['accounts'])}\n"
        f"{t(chat_id, 'field_label', label=label)}\n"
        f"{t(chat_id, 'email_line', email=email)}\n"
        f"{t(chat_id, 'password_line')}\n\n"
        f"🔄 Login jarayoni orqa fonda boshlandi..."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_back_to_crane", crane=crane_name), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_main_menu"), callback_data="back_main")],
    ])
    await show_text(chat_id, summary, keyboard)

    # Login va claim worker'ni orqa fonda ishga tushiramiz
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, start_account_worker, chat_id, crane_name, email)


# ─── Cancel add ───────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "cancel_add")
async def cb_cancel_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()
    chat_id = call.message.chat.id

    if crane_name:
        active_screen[chat_id] = f"crane:{crane_name}"
        await show_rich(chat_id, build_crane_rich_message(chat_id, crane_name), build_crane_keyboard(chat_id, crane_name))
    else:
        active_screen[chat_id] = "dashboard"
        await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer(t(chat_id, "cancelled"))


# ─── Settings ─────────────────────────────────────────────────────────────────
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


# ─── Startup ──────────────────────────────────────────────────────────────────
async def main():
    asyncio.create_task(auto_refresh())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
