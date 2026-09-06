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
    InputRichMessage, InputRichBlockTable, InputRichBlockPreformatted
)
from aiogram.types.rich_block_table_cell import RichBlockTableCell
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"

# ─── PICK NETWORK KONFIGURATSIYASI ───────────────────────────────────────────
PICK_CONFIGS = {
    "TronPick": {
        "domain": "tronpick.io",
        "sitekey": "0x4AAAAAAAW74HiAaujGhyeV",
        "xor_key": "0542f6c18bc7906d742a8401d0b5ef7f50ee304bff4f032348a4ceb3fd2d6bb1",
        "coin": "TRX"
    },
    "LitePick": {
        "domain": "litepick.io",
        "sitekey": "0x4AAAAAAA0-UWDHOKP0OrgS",
        "xor_key": "bd98ddb15b2b9e248ff50123976abe8600e27d3b5c08be9f864267d35e07930b",
        "coin": "LTC"
    },
    "DogePick": {
        "domain": "dogepick.io",
        "sitekey": "0x4AAAAAABbyeJO9QkW9czUo",
        "xor_key": "6d60cca458034d0ccf0e9a81408a5704ac3e4ee33cd267545afe79f3a25a09c1",
        "coin": "DOGE"
    }
}

# ─── KRANLAR ──────────────────────────────────────────────────────────────────
CRANES = []
for name, config in PICK_CONFIGS.items():
    emoji = "💎" if "Tron" in name else "💎" if "Lite" in name else "🐕"
    CRANES.append({
        "name": name,
        "emoji": emoji,
        "active": False,
        "claims": 0,
        "balance": 0,
        "accounts": [],
        "logs": [],
        "config": config
    })

# ─── FSM STATES ──────────────────────────────────────────────────────────────
class AddAccount(StatesGroup):
    crane_name = State()
    label = State()
    email = State()
    password = State()

class SettingsFSM(StatesGroup):
    api_key = State()

# ─── SETTINGS ─────────────────────────────────────────────────────────────────
USER_SETTINGS = {}  # chat_id -> {"api_key": str, "language": str}

LANGUAGES = {
    "uz_latin": "🇺🇿 O'zbekcha (lotin)",
    "uz_cyrillic": "🇺🇿 Ўзбекча (кирилл)"
}

def get_user_settings(chat_id: int) -> dict:
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {"api_key": None, "language": "uz_latin"}
    return USER_SETTINGS[chat_id]

# ─── TARJIMALAR ──────────────────────────────────────────────────────────────
TEXTS = {
    "uz_latin": {
        "dashboard_title": "🚀 PICK MULTI-BOT",
        "statistics_title": "📊 Statistika",
        "col_account": "Akkauntlar",
        "col_next_claim": "Keyingi olish",
        "col_balance": "Balans",
        "btn_settings": "⚙️ Sozlamalar",
        "btn_refresh": "🔄 Yangilash",
        "btn_add_account": "➕ Akkaunt qo'shish",
        "btn_back": "◀️ Orqaga",
        "btn_cancel": "❌ Bekor qilish",
        "btn_api_key": "🔑 API Kalit",
        "btn_language": "🌐 Til",
        "btn_support": "🆘 Yordam",
        "btn_main_menu": "🏠 Bosh menyu",
        "btn_back_to_crane": "◀️ {crane}ga qaytish",
        "start_all": "▶️ Hammani ishga tushirish",
        "stop_all": "⏹️ Hammani to'xtatish",
        "not_found": "Topilmadi!",
        "updated": "♻️ Yangilandi!",
        "cancelled": "❌ Bekor qilindi.",
        "plain_text_warning": "⚠️ Iltimos, oddiy matn yuboring.",
        "crane_no_accounts": "⚠️ Faol akkaunt yo'q",
        "stats_col_account": "🏷️ Akkaunt",
        "stats_col_next_claim": "⏱️ Keyingi olish",
        "stats_col_balance": "💰 Balans",
        "stats_col_status": "📡 Holat",
        "add_account_title": "{emoji} Akkaunt qo'shish - {crane}",
        "field_label": "Belgi: {label}",
        "add_account_send_email": "📧 Akkaunt emailini yuboring:",
        "email_line": "📧 Email: {email}",
        "send_password": "🔑 Parolni yuboring:",
        "password_line": "🔑 Parol: ✅",
        "cancel_hint": "/cancel — bekor qilish",
        "account_added": "✅ Akkaunt qo'shildi!",
        "next_claim_in": "⏱️ Keyingi olish: 60:00",
        "settings_title": "⚙️ Sozlamalar",
        "settings_api_key_line": "🔑 API Kalit: {status}",
        "settings_language_line": "🌐 Til: {lang}",
        "api_key_set": "✅ O'rnatilgan",
        "api_key_not_set": "❌ O'rnatilmagan",
        "send_api_key": "🔑 XEVIL API kalitingizni yuboring:",
        "api_key_saved": "✅ API Kalit saqlandi!",
        "choose_language": "🌐 Tilni tanlang:",
        "no_api_key": "⚠️ Avval Sozlamalar -> API Kalit orqali XEVIL API kalitini o'rnating!",
        "started": "🚀 {count} ta akkaunt ishga tushirildi!",
        "stopped": "⏹️ {count} ta akkaunt to'xtatildi!",
        "guide_header1": "1",
        "guide_header2": "2",
        "guide_part1": "🔵🔵🔵🔵",
        "guide_part2": "🔴🔴🔴🔴",
        "guide_header_mid": "",
        "guide_part_mid": "",
    },
    "uz_cyrillic": {
        "dashboard_title": "🚀 PICK MULTI-BOT",
        "statistics_title": "📊 Статистика",
        "col_account": "Аккаунтлар",
        "col_next_claim": "Кейинги олиш",
        "col_balance": "Баланс",
        "btn_settings": "⚙️ Созламалар",
        "btn_refresh": "🔄 Янгилаш",
        "btn_add_account": "➕ Аккаунт қўшиш",
        "btn_back": "◀️ Орқага",
        "btn_cancel": "❌ Бекор қилиш",
        "btn_api_key": "🔑 API Калит",
        "btn_language": "🌐 Тил",
        "btn_support": "🆘 Ёрдам",
        "btn_main_menu": "🏠 Бош меню",
        "btn_back_to_crane": "◀️ {crane}га қайтиш",
        "start_all": "▶️ Ҳаммани ишга тушириш",
        "stop_all": "⏹️ Ҳаммани тўхтатиш",
        "not_found": "Топилмади!",
        "updated": "♻️ Янгиланди!",
        "cancelled": "❌ Бекор қилинди.",
        "plain_text_warning": "⚠️ Илтимос, оддий матн юборинг.",
        "crane_no_accounts": "⚠️ Фаол аккаунт йўқ",
        "stats_col_account": "🏷️ Аккаунт",
        "stats_col_next_claim": "⏱️ Кейинги олиш",
        "stats_col_balance": "💰 Баланс",
        "stats_col_status": "📡 Ҳолат",
        "add_account_title": "{emoji} Аккаунт қўшиш - {crane}",
        "field_label": "Белги: {label}",
        "add_account_send_email": "📧 Аккаунт email'ини юборинг:",
        "email_line": "📧 Email: {email}",
        "send_password": "🔑 Паролни юборинг:",
        "password_line": "🔑 Парол: ✅",
        "cancel_hint": "/cancel — бекор қилиш",
        "account_added": "✅ Аккаунт қўшилди!",
        "next_claim_in": "⏱️ Кейинги олиш: 60:00",
        "settings_title": "⚙️ Созламалар",
        "settings_api_key_line": "🔑 API Калит: {status}",
        "settings_language_line": "🌐 Тил: {lang}",
        "api_key_set": "✅ Ўрнатилган",
        "api_key_not_set": "❌ Ўрнатилмаган",
        "send_api_key": "🔑 XEVIL API калитингизни юборинг:",
        "api_key_saved": "✅ API Калит сақланди!",
        "choose_language": "🌐 Тилни танланг:",
        "no_api_key": "⚠️ Аввал Созламалар -> API Калит орқали XEVIL API калитини ўрнатинг!",
        "started": "🚀 {count} та аккаунт ишга туширилди!",
        "stopped": "⏹️ {count} та аккаунт тўхтатилди!",
        "guide_header1": "1",
        "guide_header2": "2",
        "guide_part1": "🔵🔵🔵🔵",
        "guide_part2": "🔴🔴🔴🔴",
        "guide_header_mid": "",
        "guide_part_mid": "",
    }
}

def t(chat_id: int, key: str, **kwargs) -> str:
    lang = get_user_settings(chat_id).get("language", "uz_latin")
    table = TEXTS.get(lang, TEXTS["uz_latin"])
    template = table.get(key, TEXTS["uz_latin"].get(key, key))
    return template.format(**kwargs) if kwargs else template

# ─── PICK BOT CLASS ──────────────────────────────────────────────────────────
class PickBot:
    def __init__(self, email, password, api_key, config):
        self.session = requests.Session()
        self.email = email
        self.password = password
        self.api_key = api_key
        self.config = config
        self.domain = config['domain']
        self.balance = "0.00000000"
        self.next_claim = 0
        self.claim_time_remaining = 0
        self.is_logged_in = False
        self.fp = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        self.ua = "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36"
        self.headers = {
            'User-Agent': self.ua,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f'https://{self.domain}',
            'Referer': f'https://{self.domain}/login.php',
        }

    def solve_captcha(self):
        try:
            payload = {
                'key': self.api_key,
                'method': 'turnstile',
                'sitekey': self.config['sitekey'],
                'pageurl': f'https://{self.domain}/faucet.php',
                'json': 1
            }
            res = requests.post("https://api.sctg.xyz/in.php", data=payload, timeout=30)
            res_json = res.json()
            if res_json.get('status') != 1:
                return None
            rid = res_json.get('request')
            for i in range(40):
                time.sleep(3)
                g = requests.get(
                    f"https://api.sctg.xyz/res.php?key={self.api_key}&action=get&id={rid}&json=1",
                    timeout=30
                )
                g_json = g.json()
                if g_json.get('status') == 1:
                    return g_json.get('request')
                if g_json.get('request') == 'ERROR_CAPTCHA_UNSOLVABLE':
                    break
            return None
        except:
            return None

    def login(self):
        try:
            self.session.cookies.set('fp', self.fp, domain=self.domain)
            self.session.get(f"https://{self.domain}/login.php", headers={'User-Agent': self.ua}, timeout=20)
            
            csrf = self.session.cookies.get('csrf_cookie_name')
            if not csrf:
                return False, "CSRF Missing"

            token = self.solve_captcha()
            if not token:
                return False, "Captcha Failed"

            payload = {
                'action': "login",
                'email': self.email,
                'password': self.password,
                'captcha_type': "3",
                'c_captcha_response': token,
                'csrf_test_name': csrf,
                'twofa': '',
                'g-recaptcha-response': '',
                '_iconcaptcha-token': '',
                'ic-rq': '', 'ic-wid': '', 'ic-cid': '', 'ic-hp': '',
                'h-captcha-response': '', 'pcaptcha_token': ''
            }

            response = self.session.post(
                f"https://{self.domain}/process.php",
                data=payload,
                headers=self.headers,
                timeout=30
            )
            res = response.json()
            if res.get('ret') == 1:
                self.is_logged_in = True
                return True, "Success"
            return False, res.get('mes', 'Unknown error')
        except Exception as e:
            return False, str(e)

    def update_info(self):
        try:
            res = self.session.get(
                f"https://{self.domain}/faucet.php",
                headers={'User-Agent': self.ua},
                timeout=20
            )
            bal = re.search(r'user_balance">([\d.]+)', res.text)
            if bal:
                self.balance = bal.group(1)
            tmr = re.search(r'show_countdown_clock\((\d+)\)', res.text)
            if tmr:
                self.next_claim = int(tmr.group(1))
                self.claim_time_remaining = self.next_claim
            else:
                self.next_claim = 0
                self.claim_time_remaining = 0
        except:
            pass

    def claim(self):
        try:
            token = self.solve_captcha()
            if not token:
                return False, "Captcha failed"

            csrf = self.session.cookies.get('csrf_cookie_name')
            if not csrf:
                return False, "No CSRF"

            ts = int(time.time())
            data_str = f"{random.randint(100,200)}:{random.randint(10,50)}:{ts}"
            xor_key = self.config['xor_key']
            hashed = base64.b64encode(
                "".join(chr(ord(c) ^ ord(xor_key[i % len(xor_key)]))
                for i, c in enumerate(data_str)).encode()
            ).decode()

            payload = {
                'action': 'claim_hourly_faucet',
                'hash': hashed,
                'captcha_type': '3',
                'c_captcha_response': token,
                'csrf_test_name': csrf
            }

            res = self.session.post(
                f"https://{self.domain}/process.php",
                data=payload,
                headers=self.headers,
                timeout=30
            )
            res_json = res.json()
            if res_json.get('ret') == 1:
                if 'balance' in res_json:
                    self.balance = str(float(res_json['balance']) / 100000000)
                self.update_info()
                return True, res_json.get('mes', 'Success')
            return False, res_json.get('mes', 'Failed')
        except Exception as e:
            return False, str(e)

# ─── WORKER THREAD ──────────────────────────────────────────────────────────
STOP_EVENTS = {}

def pick_bot_worker(crane_name: str, account_index: int, stop_event: threading.Event, chat_id: int):
    crane = next((c for c in CRANES if c["name"] == crane_name), None)
    if not crane:
        return
    
    account = crane['accounts'][account_index]
    config = crane['config']
    api_key = get_user_settings(chat_id).get('api_key')
    
    if not api_key:
        add_log(crane, f"❌ No API key for {account['email']}")
        return
    
    bot = PickBot(account['email'], account['password'], api_key, config)
    
    success, msg = bot.login()
    if success:
        add_log(crane, f"✅ {account['email']} logged in")
        account['active'] = True
    else:
        add_log(crane, f"❌ {account['email']} login failed: {msg}")
        account['active'] = False
        return
    
    while not stop_event.is_set():
        try:
            bot.update_info()
            
            if bot.claim_time_remaining <= 0:
                add_log(crane, f"⏳ Claiming {config['coin']} for {account['email']}...")
                success, msg = bot.claim()
                if success:
                    account['balance'] = float(bot.balance)
                    add_log(crane, f"✅ {account['email']} claimed {config['coin']}: {msg}")
                else:
                    add_log(crane, f"❌ {account['email']} claim failed: {msg}")
                
                bot.claim_time_remaining = 3600
                account['next_claim_at'] = datetime.now(timezone.utc) + timedelta(minutes=60)
            
            time.sleep(1)
            
        except Exception as e:
            add_log(crane, f"⚠️ {account['email']} error: {str(e)}")
            time.sleep(10)

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_crane(name: str):
    return next((c for c in CRANES if c["name"] == name), None)

def add_log(crane: dict, text: str):
    crane.setdefault("logs", []).append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "text": text,
    })
    crane["logs"] = crane["logs"][-20:]

def format_countdown(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"

def get_account_countdown(next_claim_at) -> str:
    if not next_claim_at:
        return "--:--"
    remaining = (next_claim_at - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        return "🟢 Ready"
    return format_countdown(remaining)

def cancel_keyboard(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_add", style=ButtonStyle.DANGER)]
    ])

def settings_cancel_keyboard(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_settings", style=ButtonStyle.DANGER)]
    ])

def build_language_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"lang_{code}")] for code, name in LANGUAGES.items()]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ─── RICH MESSAGES ──────────────────────────────────────────────────────────
def build_main_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    # Sarlavha
    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "dashboard_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )

    # Qo'llanma
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

    # Kranlar statistikasi
    total_accounts = sum(len(c.get("accounts", [])) for c in CRANES)
    total_claims = sum(c.get("claims", 0) for c in CRANES)
    
    stats_rows = [
        [cell("📊 Statistika", header=True, align="center")],
        [cell(f"👥 Akkauntlar: {total_accounts} | 📈 Yig'ishlar: {total_claims}", align="center")]
    ]
    
    for crane in CRANES:
        balance = sum(a.get("balance", 0) for a in crane.get("accounts", []))
        status = "🟢" if crane["active"] else "🔴"
        stats_rows.append([
            cell(f"{crane['emoji']} {crane['name']}: {len(crane['accounts'])} akkaunt | 💰 {balance:.8f} {status}", align="center")
        ])
    
    stats_table = InputRichBlockTable(
        cells=stats_rows,
        is_bordered=True,
        is_striped=True,
    )

    return InputRichMessage(blocks=[title_table, guide_table, stats_table])

def build_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    
    for c in CRANES:
        btn = InlineKeyboardButton(
            text=f"{c['emoji']} {c['name']}",
            callback_data=f"crane_{c['name']}",
            style=ButtonStyle.PRIMARY,
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text=t(chat_id, "start_all"),
            callback_data="start_all",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text=t(chat_id, "stop_all"),
            callback_data="stop_all",
            style=ButtonStyle.DANGER,
        ),
    ])

    buttons.append([
        InlineKeyboardButton(
            text=t(chat_id, "btn_settings"),
            callback_data="settings",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text=t(chat_id, "btn_refresh"),
            callback_data="refresh",
            style=ButtonStyle.SUCCESS,
        ),
    ])

    buttons.append([
        InlineKeyboardButton(
            text=t(chat_id, "btn_support"),
            url="https://t.me/alphadevlab",
            style=ButtonStyle.DANGER,
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_crane_rich_message(chat_id: int, crane: dict) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    blocks = []
    
    # Sarlavha
    title_table = InputRichBlockTable(
        cells=[[cell(f"{crane['emoji']} {crane['name']}", header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )
    blocks.append(title_table)

    # Akkauntlar jadvali
    accounts = crane.get("accounts", [])
    
    if accounts:
        rows = [[
            cell(t(chat_id, "stats_col_account"), header=True, align="left"),
            cell(t(chat_id, "stats_col_next_claim"), header=True, align="center"),
            cell(t(chat_id, "stats_col_balance"), header=True, align="right"),
            cell(t(chat_id, "stats_col_status"), header=True, align="center"),
        ]]
        
        for acc in accounts:
            email = acc.get("email", "Unknown")[:15]
            balance = acc.get("balance", 0.0)
            countdown = get_account_countdown(acc.get("next_claim_at"))
            status = "🟢 Faol" if acc.get("active", False) else "🔴 O'chiq"
            rows.append([
                cell(email, align="left"),
                cell(countdown, align="center"),
                cell(f"{balance:.8f}", align="right"),
                cell(status, align="center"),
            ])
        
        acc_table = InputRichBlockTable(
            cells=rows,
            is_bordered=True,
            is_striped=True,
        )
        blocks.append(acc_table)
    else:
        blocks.append(InputRichBlockPreformatted(text=t(chat_id, "crane_no_accounts")))

    # Loglar
    logs = crane.get("logs", [])
    if logs:
        log_text = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-8:])
        blocks.append(InputRichBlockPreformatted(text=log_text))

    return InputRichMessage(blocks=blocks)

def build_crane_keyboard(chat_id: int, crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(chat_id, "btn_add_account"),
            callback_data=f"add_account_{crane_name}",
            style=ButtonStyle.DANGER
        )],
        [
            InlineKeyboardButton(
                text=t(chat_id, "btn_refresh"),
                callback_data=f"crane_{crane_name}",
                style=ButtonStyle.SUCCESS
            ),
            InlineKeyboardButton(
                text=t(chat_id, "btn_back"),
                callback_data="back_main",
                style=ButtonStyle.SUCCESS
            ),
        ],
    ])

def build_settings_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    s = get_user_settings(chat_id)
    api_key = s.get("api_key")
    api_status = api_key[:10] + "..." if api_key else "❌ O'rnatilmagan"
    lang_name = LANGUAGES.get(s.get("language", "uz_latin"), "UZ")

    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "settings_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )

    info_table = InputRichBlockTable(
        cells=[
            [
                cell("🔑 API Kalit", header=True, align="center"),
                cell("🌐 Til", header=True, align="center"),
                cell("🆔 ID", header=True, align="center"),
            ],
            [
                cell(api_status, align="center"),
                cell(lang_name, align="center"),
                cell(str(chat_id)[-10:], align="center"),
            ],
        ],
        is_bordered=True,
        is_striped=True,
    )

    return InputRichMessage(blocks=[title_table, info_table])

def build_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_api_key"), callback_data="settings_api_key", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_language"), callback_data="settings_language", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_back"), callback_data="back_main", style=ButtonStyle.SUCCESS)],
    ])

# ─── BOT ─────────────────────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

active_messages = {}
active_screen = {}

async def show_rich(chat_id: int, rich_message: InputRichMessage, reply_markup: InlineKeyboardMarkup | None = None):
    msg_id = active_messages.get(chat_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                rich_message=rich_message,
                reply_markup=reply_markup,
            )
            return
        except:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except:
                pass
    msg = await bot.send_rich_message(chat_id=chat_id, rich_message=rich_message, reply_markup=reply_markup)
    active_messages[chat_id] = msg.message_id

async def show_text(chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None):
    msg_id = active_messages.get(chat_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except:
                pass
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    active_messages[chat_id] = msg.message_id

async def delete_silently(message: Message):
    try:
        await message.delete()
    except:
        pass

# ─── AUTO REFRESH ──────────────────────────────────────────────────────────
async def auto_refresh():
    while True:
        await asyncio.sleep(3)
        try:
            for chat_id, msg_id in list(active_messages.items()):
                if active_screen.get(chat_id) == "dashboard":
                    try:
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=msg_id,
                            rich_message=build_main_rich_message(chat_id),
                            reply_markup=build_keyboard(chat_id)
                        )
                    except:
                        pass
        except:
            pass

# ─── COMMANDS ──────────────────────────────────────────────────────────────
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

# ─── CALLBACKS ─────────────────────────────────────────────────────────────
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

# ─── START ALL ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "start_all")
async def cb_start_all(call: CallbackQuery):
    chat_id = call.message.chat.id
    
    # API key borligini tekshirish
    api_key = get_user_settings(chat_id).get('api_key')
    if not api_key:
        await call.answer(t(chat_id, "no_api_key"), show_alert=True)
        return
    
    started = 0
    for crane in CRANES:
        for idx, acc in enumerate(crane.get("accounts", [])):
            key = f"{crane['name']}_{idx}"
            if key not in STOP_EVENTS or STOP_EVENTS[key].is_set():
                STOP_EVENTS[key] = threading.Event()
                thread = Thread(
                    target=pick_bot_worker,
                    args=(crane['name'], idx, STOP_EVENTS[key], chat_id)
                )
                thread.daemon = True
                thread.start()
                started += 1
                crane["active"] = True
                acc["active"] = True
                add_log(crane, f"🚀 Started: {acc['email']}")
    
    await call.answer(t(chat_id, "started", count=started))
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))

# ─── STOP ALL ──────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "stop_all")
async def cb_stop_all(call: CallbackQuery):
    chat_id = call.message.chat.id
    stopped = 0
    
    for key in list(STOP_EVENTS.keys()):
        STOP_EVENTS[key].set()
        del STOP_EVENTS[key]
        stopped += 1
    
    for crane in CRANES:
        crane["active"] = False
        for acc in crane.get("accounts", []):
            acc["active"] = False
            add_log(crane, f"⏹️ Stopped: {acc['email']}")
    
    await call.answer(t(chat_id, "stopped", count=stopped))
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))

# ─── ADD ACCOUNT ────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("add_account_", "")
    crane = get_crane(crane_name)
    chat_id = call.message.chat.id
    
    if not crane:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return

    acc_num = len(crane["accounts"]) + 1
    label = f"Account {acc_num}"

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
    
    await state.update_data(password=password)
    await delete_silently(message)
    await _finish_add_account(message, state)

async def _finish_add_account(message: Message, state: FSMContext):
    data = await state.get_data()
    crane_name = data["crane_name"]
    label = data["label"]
    email = data["email"]
    password = data["password"]

    crane = get_crane(crane_name)
    if not crane:
        await state.clear()
        return

    next_claim_time = datetime.now(timezone.utc) + timedelta(minutes=60)

    new_acc = {
        "label": label,
        "email": email,
        "password": password,
        "active": False,
        "balance": 0.0,
        "next_claim_at": next_claim_time,
    }
    crane["accounts"].append(new_acc)
    crane["active"] = True

    add_log(crane, f"📝 Account added: {email}")

    chat_id = message.chat.id
    summary = (
        f"{t(chat_id, 'account_added')}\n\n"
        f"{crane['emoji']} {crane_name}\n"
        f"📧 {email}\n"
        f"🔑 Parol: ✅\n\n"
        f"⏱️ {t(chat_id, 'next_claim_in')}\n\n"
        f"▶️ Akkauntni ishga tushirish uchun 'Hammani ishga tushirish' tugmasini bosing!"
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

async def require_text(message: Message) -> str | None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return None
    return message.text.strip()

# ─── SETTINGS ──────────────────────────────────────────────────────────────
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
async def fsm_settings_api_key(message: Message, state: FSMContext):
    api_key = await require_text(message)
    if api_key is None:
        return
    
    settings = get_user_settings(message.chat.id)
    settings["api_key"] = api_key
    await state.clear()
    
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await message.answer(t(chat_id, "api_key_saved"))

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
    
    settings = get_user_settings(chat_id)
    settings["language"] = code
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

# ─── MAIN ──────────────────────────────────────────────────────────────────
async def main():
    asyncio.create_task(auto_refresh())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
