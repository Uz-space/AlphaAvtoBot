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
    RichBlockTableCell, RichTextBold,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"

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

CRANES = []
for _name, _config in PICK_CONFIGS.items():
    _emoji = "💎" if "Tron" in _name else "🔵" if "Lite" in _name else "🐕"
    CRANES.append({
        "name": _name,
        "emoji": _emoji,
        "active": False,
        "claims": 0,
        "accounts": [],
        "logs": [],
        "config": _config
    })


class AddAccount(StatesGroup):
    email = State()
    password = State()


class SettingsFSM(StatesGroup):
    api_key = State()


USER_SETTINGS: dict[int, dict] = {}

LANGUAGES = {
    "uz_latin": "🇺🇿 O'zbekcha (lotin)",
    "uz_cyrillic": "🇺🇿 Ўзбекча (кирилл)"
}

TEXTS = {
    "uz_latin": {
        "dashboard_title": "🚀 PICK MULTI-BOT",
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
        "stats_col_account": "Akkaunt",
        "stats_col_next_claim": "Keyingi olish",
        "stats_col_balance": "Balans",
        "stats_col_status": "Holat",
        "add_account_title": "{emoji} Akkaunt qo'shish - {crane}",
        "add_account_send_email": "📧 Akkaunt emailini yuboring:",
        "email_line": "📧 Email: {email}",
        "send_password": "🔑 Parolni yuboring:",
        "cancel_hint": "/cancel — bekor qilish",
        "account_added": "✅ Akkaunt qo'shildi!",
        "next_claim_in": "Keyingi olish: 60:00",
        "settings_title": "⚙️ Sozlamalar",
        "api_key_not_set": "❌ O'rnatilmagan",
        "send_api_key": "🔑 XEVIL API kalitingizni yuboring:",
        "api_key_saved": "✅ API Kalit saqlandi!",
        "choose_language": "🌐 Tilni tanlang:",
        "no_api_key": "⚠️ Avval Sozlamalar -> API Kalit orqali XEVIL API kalitini o'rnating!",
        "started": "🚀 {count} ta akkaunt ishga tushirildi!",
        "stopped": "⏹️ {count} ta akkaunt to'xtatildi!",
        "col_crane": "Kran",
        "col_accounts": "Akkauntlar",
        "col_status": "Holat",
        "col_balance": "Balans",
    },
    "uz_cyrillic": {
        "dashboard_title": "🚀 PICK MULTI-BOT",
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
        "stats_col_account": "Аккаунт",
        "stats_col_next_claim": "Кейинги олиш",
        "stats_col_balance": "Баланс",
        "stats_col_status": "Ҳолат",
        "add_account_title": "{emoji} Аккаунт қўшиш - {crane}",
        "add_account_send_email": "📧 Аккаунт email'ини юборинг:",
        "email_line": "📧 Email: {email}",
        "send_password": "🔑 Паролни юборинг:",
        "cancel_hint": "/cancel — бекор қилиш",
        "account_added": "✅ Аккаунт қўшилди!",
        "next_claim_in": "Кейинги олиш: 60:00",
        "settings_title": "⚙️ Созламалар",
        "api_key_not_set": "❌ Ўрнатилмаган",
        "send_api_key": "🔑 XEVIL API калитингизни юборинг:",
        "api_key_saved": "✅ API Калит сақланди!",
        "choose_language": "🌐 Тилни танланг:",
        "no_api_key": "⚠️ Аввал Созламалар -> API Калит орқали XEVIL API калитини ўрнатинг!",
        "started": "🚀 {count} та аккаунт ишга туширилди!",
        "stopped": "⏹️ {count} та аккаунт тўхтатилди!",
        "col_crane": "Кран",
        "col_accounts": "Аккаунтлар",
        "col_status": "Ҳолат",
        "col_balance": "Баланс",
    }
}


def get_user_settings(chat_id: int) -> dict:
    if chat_id not in USER_SETTINGS:
        USER_SETTINGS[chat_id] = {"api_key": None, "language": "uz_latin"}
    return USER_SETTINGS[chat_id]


def t(chat_id: int, key: str, **kwargs) -> str:
    lang = get_user_settings(chat_id).get("language", "uz_latin")
    table = TEXTS.get(lang, TEXTS["uz_latin"])
    template = table.get(key, TEXTS["uz_latin"].get(key, key))
    return template.format(**kwargs) if kwargs else template


def rt(text: str) -> RichTextBold:
    """str -> RichTextBold (RichTextPlain mavjud emas bu versiyada)."""
    return RichTextBold(text=text)


def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
    return RichBlockTableCell(
        align=align,
        valign="middle",
        text=rt(text),
        is_header=True if header else None,
    )


# ─── PICK BOT ────────────────────────────────────────────────────────────────
class PickBot:
    def __init__(self, email: str, password: str, api_key: str, config: dict):
        self.session = requests.Session()
        self.email = email
        self.password = password
        self.api_key = api_key
        self.config = config
        self.domain = config['domain']
        self.balance = "0.00000000"
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

    def solve_captcha(self) -> str | None:
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
            for _ in range(40):
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
        except Exception:
            return None

    def login(self) -> tuple[bool, str]:
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
                data=payload, headers=self.headers, timeout=30
            )
            res = response.json()
            if res.get('ret') == 1:
                self.is_logged_in = True
                return True, "Success"
            return False, res.get('mes', 'Unknown error')
        except Exception as e:
            return False, str(e)

    def update_info(self) -> None:
        try:
            res = self.session.get(
                f"https://{self.domain}/faucet.php",
                headers={'User-Agent': self.ua}, timeout=20
            )
            bal = re.search(r'user_balance">([\d.]+)', res.text)
            if bal:
                self.balance = bal.group(1)
            tmr = re.search(r'show_countdown_clock\((\d+)\)', res.text)
            self.claim_time_remaining = int(tmr.group(1)) if tmr else 0
        except Exception:
            pass

    def claim(self) -> tuple[bool, str]:
        try:
            token = self.solve_captcha()
            if not token:
                return False, "Captcha failed"
            csrf = self.session.cookies.get('csrf_cookie_name')
            if not csrf:
                return False, "No CSRF"
            ts = int(time.time())
            data_str = f"{random.randint(100, 200)}:{random.randint(10, 50)}:{ts}"
            xor_key = self.config['xor_key']
            hashed = base64.b64encode(
                "".join(
                    chr(ord(c) ^ ord(xor_key[i % len(xor_key)]))
                    for i, c in enumerate(data_str)
                ).encode()
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
                data=payload, headers=self.headers, timeout=30
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


# ─── WORKER ──────────────────────────────────────────────────────────────────
STOP_EVENTS: dict[str, threading.Event] = {}


def pick_bot_worker(crane_name: str, account_index: int, stop_event: threading.Event, chat_id: int) -> None:
    crane = next((c for c in CRANES if c["name"] == crane_name), None)
    if not crane:
        return
    account = crane['accounts'][account_index]
    api_key = get_user_settings(chat_id).get('api_key')
    if not api_key:
        add_log(crane, f"❌ No API key for {account['email']}")
        return

    bot_instance = PickBot(account['email'], account['password'], api_key, crane['config'])
    ok, msg = bot_instance.login()
    if ok:
        add_log(crane, f"✅ {account['email']} logged in")
        account['active'] = True
    else:
        add_log(crane, f"❌ {account['email']} login failed: {msg}")
        account['active'] = False
        return

    while not stop_event.is_set():
        try:
            bot_instance.update_info()
            if bot_instance.claim_time_remaining <= 0:
                add_log(crane, f"⏳ Claiming for {account['email']}...")
                ok, claim_msg = bot_instance.claim()
                if ok:
                    account['balance'] = float(bot_instance.balance)
                    crane['claims'] += 1
                    add_log(crane, f"✅ {account['email']} claimed: {claim_msg}")
                else:
                    add_log(crane, f"❌ {account['email']} failed: {claim_msg}")
                bot_instance.claim_time_remaining = 3600
                account['next_claim_at'] = datetime.now(timezone.utc) + timedelta(minutes=60)
            time.sleep(1)
        except Exception as e:
            add_log(crane, f"⚠️ {account['email']}: {str(e)}")
            time.sleep(10)


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def get_crane(name: str) -> dict | None:
    return next((c for c in CRANES if c["name"] == name), None)


def add_log(crane: dict, text: str) -> None:
    crane.setdefault("logs", []).append({"time": datetime.now().strftime("%H:%M:%S"), "text": text})
    crane["logs"] = crane["logs"][-20:]


def get_account_countdown(next_claim_at) -> str:
    if not next_claim_at:
        return "--:--"
    remaining = (next_claim_at - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        return "Ready"
    m, s = divmod(int(remaining), 60)
    return f"{m:02d}:{s:02d}"


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


# ─── RICH MESSAGE BUILDERS ───────────────────────────────────────────────────
def build_main_rich_message(chat_id: int) -> InputRichMessage:
    total_accounts = sum(len(c.get("accounts", [])) for c in CRANES)
    total_claims = sum(c.get("claims", 0) for c in CRANES)

    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "dashboard_title"), header=True, align="center")]],
        is_bordered=True,
    )

    rows = [[
        cell(t(chat_id, "col_crane"), header=True, align="left"),
        cell(t(chat_id, "col_accounts"), header=True, align="center"),
        cell(t(chat_id, "col_status"), header=True, align="center"),
        cell(t(chat_id, "col_balance"), header=True, align="right"),
    ]]
    for crane in CRANES:
        balance = sum(a.get("balance", 0.0) for a in crane.get("accounts", []))
        rows.append([
            cell(f"{crane['emoji']} {crane['name']}", align="left"),
            cell(str(len(crane["accounts"])), align="center"),
            cell("🟢 ON" if crane["active"] else "🔴 OFF", align="center"),
            cell(f"{balance:.6f}", align="right"),
        ])
    rows.append([
        cell("TOTAL", header=True, align="left"),
        cell(str(total_accounts), header=True, align="center"),
        cell(f"Claims: {total_claims}", header=True, align="center"),
        cell("", header=True, align="right"),
    ])

    stats_table = InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True)
    return InputRichMessage(blocks=[title_table, stats_table])


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
        InlineKeyboardButton(text=t(chat_id, "start_all"), callback_data="start_all", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text=t(chat_id, "stop_all"), callback_data="stop_all", style=ButtonStyle.DANGER),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_settings"), callback_data="settings", style=ButtonStyle.SUCCESS),
        InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data="refresh", style=ButtonStyle.SUCCESS),
    ])
    buttons.append([
        InlineKeyboardButton(text=t(chat_id, "btn_support"), url="https://t.me/alphadevlab"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_crane_rich_message(chat_id: int, crane: dict) -> InputRichMessage:
    blocks = []
    blocks.append(InputRichBlockTable(
        cells=[[cell(f"{crane['emoji']} {crane['name']}", header=True, align="center")]],
        is_bordered=True,
    ))

    accounts = crane.get("accounts", [])
    if accounts:
        rows = [[
            cell(t(chat_id, "stats_col_account"), header=True, align="left"),
            cell(t(chat_id, "stats_col_next_claim"), header=True, align="center"),
            cell(t(chat_id, "stats_col_balance"), header=True, align="right"),
            cell(t(chat_id, "stats_col_status"), header=True, align="center"),
        ]]
        for acc in accounts:
            rows.append([
                cell(acc.get("email", "")[:18], align="left"),
                cell(get_account_countdown(acc.get("next_claim_at")), align="center"),
                cell(f"{acc.get('balance', 0.0):.8f}", align="right"),
                cell("🟢" if acc.get("active") else "🔴", align="center"),
            ])
        blocks.append(InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True))
    else:
        blocks.append(InputRichBlockPreformatted(text=rt(t(chat_id, "crane_no_accounts"))))

    logs = crane.get("logs", [])
    if logs:
        log_text = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-8:])
        blocks.append(InputRichBlockPreformatted(text=rt(log_text)))

    return InputRichMessage(blocks=blocks)


def build_crane_keyboard(chat_id: int, crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(chat_id, "btn_add_account"),
            callback_data=f"add_account_{crane_name}",
            style=ButtonStyle.DANGER,
        )],
        [
            InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=t(chat_id, "btn_back"), callback_data="back_main", style=ButtonStyle.SUCCESS),
        ],
    ])


def build_settings_rich_message(chat_id: int) -> InputRichMessage:
    s = get_user_settings(chat_id)
    api_key = s.get("api_key")
    api_status = (api_key[:10] + "...") if api_key else t(chat_id, "api_key_not_set")
    lang_name = LANGUAGES.get(s.get("language", "uz_latin"), "UZ")

    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "settings_title"), header=True, align="center")]],
        is_bordered=True,
    )
    info_table = InputRichBlockTable(
        cells=[
            [
                cell("API Kalit", header=True, align="center"),
                cell("Til", header=True, align="center"),
                cell("ID", header=True, align="center"),
            ],
            [
                cell(api_status, align="center"),
                cell(lang_name, align="center"),
                cell(str(chat_id), align="center"),
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

active_messages: dict[int, int] = {}
active_screen: dict[int, str] = {}


async def show_rich(chat_id: int, rich_message: InputRichMessage, reply_markup: InlineKeyboardMarkup | None = None) -> None:
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


async def show_text(chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
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


async def delete_silently(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


async def auto_refresh() -> None:
    while True:
        await asyncio.sleep(5)
        for chat_id, msg_id in list(active_messages.items()):
            if active_screen.get(chat_id) == "dashboard":
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id, message_id=msg_id,
                        rich_message=build_main_rich_message(chat_id),
                        reply_markup=build_keyboard(chat_id),
                    )
                except Exception:
                    pass


# ─── HANDLERS ────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.callback_query(F.data == "refresh")
async def cb_refresh(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer(t(chat_id, "updated"))


@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))
    await call.answer()


@dp.callback_query(F.data.startswith("crane_"))
async def cb_crane(call: CallbackQuery) -> None:
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
async def cb_start_all(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
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
                Thread(
                    target=pick_bot_worker,
                    args=(crane['name'], idx, STOP_EVENTS[key], chat_id),
                    daemon=True,
                ).start()
                started += 1
                crane["active"] = True
                acc["active"] = True
                add_log(crane, f"🚀 Started: {acc['email']}")
    await call.answer(t(chat_id, "started", count=started))
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.callback_query(F.data == "stop_all")
async def cb_stop_all(call: CallbackQuery) -> None:
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
    active_screen[chat_id] = "dashboard"
    await show_rich(chat_id, build_main_rich_message(chat_id), build_keyboard(chat_id))


@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext) -> None:
    crane_name = call.data.replace("add_account_", "")
    crane = get_crane(crane_name)
    chat_id = call.message.chat.id
    if not crane:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return
    await state.set_state(AddAccount.email)
    await state.update_data(crane_name=crane_name)
    active_screen[chat_id] = "add_account"
    text = (
        f"{t(chat_id, 'add_account_title', emoji=crane['emoji'], crane=crane_name)}\n\n"
        f"{t(chat_id, 'add_account_send_email')}\n\n"
        f"{t(chat_id, 'cancel_hint')}"
    )
    await show_text(chat_id, text, cancel_keyboard(chat_id))
    await call.answer()


@dp.message(AddAccount.email)
async def fsm_email(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return
    await state.update_data(email=message.text.strip())
    await state.set_state(AddAccount.password)
    chat_id = message.chat.id
    await delete_silently(message)
    text = (
        f"{t(chat_id, 'email_line', email=message.text.strip())}\n\n"
        f"{t(chat_id, 'send_password')}\n\n"
        f"{t(chat_id, 'cancel_hint')}"
    )
    await show_text(chat_id, text, cancel_keyboard(chat_id))


@dp.message(AddAccount.password)
async def fsm_password(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return
    data = await state.get_data()
    crane_name = data["crane_name"]
    email = data["email"]
    password = message.text.strip()
    await delete_silently(message)

    crane = get_crane(crane_name)
    if not crane:
        await state.clear()
        return

    crane["accounts"].append({
        "label": f"Account {len(crane['accounts']) + 1}",
        "email": email,
        "password": password,
        "active": False,
        "balance": 0.0,
        "next_claim_at": datetime.now(timezone.utc) + timedelta(minutes=60),
    })
    add_log(crane, f"📝 Added: {email}")
    await state.clear()

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
    active_screen[chat_id] = "account_added"
    await show_text(chat_id, summary, keyboard)


@dp.callback_query(F.data == "cancel_add")
async def cb_cancel_add(call: CallbackQuery, state: FSMContext) -> None:
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
async def cb_settings(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await call.answer()


@dp.callback_query(F.data == "settings_api_key")
async def cb_settings_api_key(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsFSM.api_key)
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings_api_key"
    text = f"{t(chat_id, 'send_api_key')}\n\n{t(chat_id, 'cancel_hint')}"
    await show_text(chat_id, text, settings_cancel_keyboard(chat_id))
    await call.answer()


@dp.message(SettingsFSM.api_key)
async def fsm_settings_api_key(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return
    get_user_settings(message.chat.id)["api_key"] = message.text.strip()
    await state.clear()
    chat_id = message.chat.id
    await delete_silently(message)
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await message.answer(t(chat_id, "api_key_saved"))


@dp.callback_query(F.data == "settings_language")
async def cb_settings_language(call: CallbackQuery) -> None:
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings_language"
    await show_text(chat_id, t(chat_id, "choose_language"), build_language_keyboard(chat_id))
    await call.answer()


@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang_select(call: CallbackQuery) -> None:
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
async def cb_cancel_settings(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    chat_id = call.message.chat.id
    active_screen[chat_id] = "settings"
    await show_rich(chat_id, build_settings_rich_message(chat_id), build_settings_keyboard(chat_id))
    await call.answer(t(chat_id, "cancelled"))


# ─── MAIN ────────────────────────────────────────────────────────────────────
async def main() -> None:
    asyncio.create_task(auto_refresh())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
