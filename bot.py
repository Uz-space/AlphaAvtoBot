#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tron.py uchun Telegram bot interface.
Terminal chiqishi (Display.Cetak, Display.Error, Display.Sukses, Tmr)
va input() so'rovlari Telegram'da aynan ko'rinadi.

Ishlatish:
  pip install pyTelegramBotAPI --break-system-packages
  pip install requests --break-system-packages
  python tron_bot.py

tron.py shu fayl bilan bir papkada bo'lishi kerak.
"""

import os
import sys
import time
import threading
import logging

import telebot
from telebot import types

# tron.py ni import qilamiz — Bot() chaqirmaymiz, faqat classlardan foydalanamiz
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# tron.py ichidagi Bot() __main__ da ishga tushadi — buni to'xtatamiz
import importlib, types as _types

# tron.py ni modul sifatida yuklaymiz (if __name__ == "__main__" bloki chaqirilmaydi)
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "tron",
    os.path.join(os.path.dirname(__file__), "tron.py")
)
tron = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tron)

# ============================================================
#                      SOZLAMALAR
# ============================================================
BOT_TOKEN = "8863932002:AAE7AaYQFBCycRzv-M1zfAIa-ye5HniJj2Q"   # @BotFather dan olgan token
ALLOWED_USERS: set[int] = set()  # Bo'sh = hamma foydalanuvchiga ruxsat
#  Faqat o'zingga ruxsat bermoqchi bo'lsang:  ALLOWED_USERS = {123456789}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("tron_tg")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ============================================================
#             Foydalanuvchi sessiyalari (xotirada)
# ============================================================
# session[chat_id] = {
#   "state": "idle" | "waiting_input" | "running",
#   "input_key": str,          # setConfig uchun so'ralayotgan kalit
#   "input_event": Event,      # bot_input() ni kutish uchun
#   "input_value": str,        # foydalanuvchi kiritgani
#   "tron_bot": TronBot,       # har bir chat uchun alohida TronBot instance
#   "timer_msg_id": int | None # countdown xabari id
# }
sessions: dict[int, dict] = {}
sessions_lock = threading.Lock()


def get_session(chat_id: int) -> dict:
    with sessions_lock:
        if chat_id not in sessions:
            sessions[chat_id] = {
                "state": "idle",
                "input_key": None,
                "input_event": threading.Event(),
                "input_value": None,
                "tron_bot": None,
                "timer_msg_id": None,
            }
        return sessions[chat_id]


def guard(func):
    """Ruxsatsiz foydalanuvchilarni bloklaydi."""
    def wrapper(message):
        if ALLOWED_USERS and message.from_user.id not in ALLOWED_USERS:
            bot.send_message(message.chat.id, "⛔ Ruxsat yo'q.")
            return
        func(message)
    return wrapper


# ============================================================
#              TronBot — tron.py Bot klassini wraplash
# ============================================================
class TronBot:
    """
    tron.py Bot() klassining barcha terminal I/O operatsiyalarini
    Telegram'ga yo'naltiruvchi adapter.
    """

    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self._session = get_session(chat_id)

        # tron classlarini yaratamiz (asl mantiq o'zgarmaydi)
        self.cf       = tron.Cloudflare()
        self.scrap    = tron.HtmlScrap()
        self.captcha  = None   # login paytida yaratilamiz
        self.iewil    = None
        self.cookie   = None
        self.uagent   = None

    # ----------------------------------------------------------
    #  Chiqish — terminal → Telegram
    # ----------------------------------------------------------
    def _send(self, text: str):
        """HTML formatida xabar yuboradi. ANSI kodlarini olib tashlaydi."""
        import re
        clean = re.sub(r'\033\[[0-9;]*m', '', text).strip()
        if not clean:
            return
        try:
            bot.send_message(self.chat_id, clean)
        except Exception as e:
            log.error("send error: %s", e)

    def _send_ok(self, text: str):
        self._send(f"✅ {text}")

    def _send_err(self, text: str):
        self._send(f"❌ {text}")

    def _cetak(self, label: str, value: str = "[No Content]"):
        """Display.Cetak ekvivalenti."""
        self._send(f"<b>{label}:</b> {value}")

    def _line(self):
        self._send("─" * 30)

    # ----------------------------------------------------------
    #  Kirish — input() → Telegram xabar kutish
    # ----------------------------------------------------------
    def _ask_input(self, prompt: str) -> str:
        """
        Foydalanuvchidan ma'lumot so'raydi.
        Javob kelgunicha bu thread bloklanadi.
        """
        sess = self._session
        sess["state"] = "waiting_input"
        sess["input_key"] = prompt
        sess["input_event"].clear()
        sess["input_value"] = None

        self._send(f"⌨️ <b>{prompt}:</b>")

        # 5 daqiqa kutamiz
        if not sess["input_event"].wait(timeout=300):
            self._send_err("Vaqt tugadi (5 daqiqa). /start bilan qayta boshlang.")
            raise TimeoutError("input timeout")

        sess["state"] = "running"
        return sess["input_value"]

    # ----------------------------------------------------------
    #  Countdown — Functions.Tmr ekvivalenti
    # ----------------------------------------------------------
    def _tmr(self, seconds: int):
        """Countdown timerni Telegram xabarini edit qilib ko'rsatadi."""
        sess = self._session
        try:
            msg = bot.send_message(self.chat_id, "⏳ 01:00:00")
            sess["timer_msg_id"] = msg.message_id
        except Exception:
            return

        end_time = time.time() + seconds
        while True:
            remaining = end_time - time.time()
            if remaining < 1:
                break
            t = time.gmtime(int(remaining))
            countdown_text = (
                f"⏳ Keyingi claim: "
                f"{time.strftime('%H:%M:%S', t)}"
            )
            try:
                bot.edit_message_text(
                    countdown_text,
                    chat_id=self.chat_id,
                    message_id=sess["timer_msg_id"]
                )
            except Exception:
                pass
            time.sleep(30)  # har 30 sekundda yangilanadi (flood limit)

        try:
            bot.edit_message_text(
                "✅ Vaqt tugadi! Claim boshlayapti...",
                chat_id=self.chat_id,
                message_id=sess["timer_msg_id"]
            )
        except Exception:
            pass

    # ----------------------------------------------------------
    #  tron.py mantiqini ishga tushirish
    # ----------------------------------------------------------
    def headers(self):
        from urllib.parse import urlparse
        return [
            "Host: " + urlparse(tron.host).hostname,
            "cookie: " + self.cookie,
            "X-Requested-With: XMLHttpRequest",
            "user-agent: " + self.uagent,
        ]

    def _load_config_value(self, key: str) -> str | None:
        return tron.Functions.getConfig(key)

    def _set_or_ask(self, key: str) -> str:
        """Config'dan o'qiydi, yo'q bo'lsa Telegram orqali so'raydi."""
        val = tron.Functions.getConfig(key)
        if val:
            return val
        val = self._ask_input(key)
        tron.Functions._save_config(
            {**tron.Functions._load_config(), key: val}
        )
        return val

    def start(self):
        """Bot() __init__ + _enter_cookie_flow ekvivalenti."""
        self._session["state"] = "running"
        self._send("🚀 <b>TRONPICK BOT</b> ishga tushdi.")
        self._line()

        # Cookie va user_agent olish
        self.cookie = self._set_or_ask("cookie")
        self.uagent = self._set_or_ask("user_agent")

        # Captcha setup
        self._setup_captcha()

        # Dashboard tekshirish
        ok = self._dashboard_flow()
        if not ok:
            tron.Functions.removeConfig("cookie")
            tron.Functions.removeConfig("user_agent")
            self.cookie = None
            self.uagent = None
            return self.start()

        self._menu()

    def _setup_captcha(self):
        """Captcha provider ni Telegram orqali tanlaydi."""
        if not tron.Functions.getConfig("type"):
            self._send(
                "🔑 <b>Captcha API tanlang:</b>\n"
                "/cap1 — Multibot\n"
                "/cap2 — Xevil"
            )
            # type tanlanishini kutamiz (handler pastda)
            sess = self._session
            sess["state"] = "waiting_input"
            sess["input_key"] = "type"
            sess["input_event"].clear()
            sess["input_event"].wait(timeout=300)
            sess["state"] = "running"

        self.captcha = tron.Captcha()

    def _dashboard_flow(self) -> bool:
        """
        True  = login muvaffaqiyatli
        False = cookie expired yoki cloudflare
        """
        retry = 0
        while True:
            r = tron.Requests.get(tron.host, self.headers())
            data = {}
            import re
            data["cloudflare"] = 1 if re.search(r"Just a moment\.\.\.", r[1]) else 0
            data["Login"]      = "" if re.search(r"login_button", r[1]) else 1

            try:
                data["Username"] = r[1].split("&username=")[1].split("&")[0].strip()
            except IndexError:
                data["Username"] = None

            try:
                data["Balance"] = r[1].split(
                    'class="drop_down_header_text user_balance">'
                )[1].split("<")[0]
            except IndexError:
                data["Balance"] = None

            if data.get("cloudflare"):
                self._send_err(f"Cloudflare aniqlandi. Bypass qilinmoqda... ({retry})")
                cf = self.cf.BypassCf(tron.host)
                self.cookie = cf["cookie"]
                self.uagent = cf["user-agent"]
                retry += 1
                if retry > 3:
                    self._send_err("Cloudflare bypass muvaffaqiyatsiz. Cookie qayta kiriting.")
                    return False
                continue

            if not data.get("Login"):
                self._send_err("Cookie muddati tugagan. Qayta kiriting.")
                return False

            self._cetak("Username", data["Username"])
            self._cetak("Balance",  data["Balance"])
            self._cetak("Bal_Api",  str(self.captcha.getBalance()))
            self._line()
            return True

    def _menu(self):
        """Inline keyboard menu."""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🎁 Claim Bonus",          callback_data="menu_1"),
            types.InlineKeyboardButton("⏰ Hourly Bonus (24/7)",  callback_data="menu_2"),
        )
        markup.add(
            types.InlineKeyboardButton("📊 Dashboard",            callback_data="menu_dash"),
            types.InlineKeyboardButton("🔄 Cookie yangilash",     callback_data="menu_cookie"),
        )
        bot.send_message(self.chat_id, "📋 <b>Menyu:</b>", reply_markup=markup)

    # ----------------------------------------------------------
    #  HourlyFaucet — tron.py mantiqini qayta ishlatadi
    # ----------------------------------------------------------
    def run_hourly(self):
        self._send("⏰ Hourly Faucet boshlandi (cheksiz loop)...")
        retry = 0
        import re as _re

        while True:
            r = tron.Requests.get(tron.host + "faucet.php", self.headers())
            cek = self.scrap.Result(r[1])

            if cek.get("cloudflare"):
                self._send_err(f"Cloudflare. Bypass {retry}...")
                cf = self.cf.BypassCf(tron.host)
                self.cookie = cf["cookie"]
                self.uagent = cf["user-agent"]
                retry += 1
                if retry > 3:
                    self._send_err("Cloudflare bypass muvaffaqiyatsiz. Cookie yangilang: /cookie")
                    return
                continue

            retry = 0
            try:
                tmr = r[1].split("select_hourly_faucet|")[1].split("|")[0]
            except IndexError:
                tmr = None

            set_cookie_matches = _re.findall(
                r"^Set-Cookie:\s*([^;]*)", r[0], flags=_re.MULTILINE | _re.IGNORECASE
            )
            cookies = {}
            for item in set_cookie_matches:
                if "=" in item:
                    k_, v_ = item.split("=", 1)
                    cookies[k_] = v_

            # Captcha hal qilish
            recaptcha_ = tron.recaptcha
            turnstile_  = tron.turnstile

            cap = None
            if recaptcha_ and _re.search(recaptcha_, r[1]):
                self._send("🔐 RecaptchaV2 hal qilinmoqda...")
                cap = self.captcha.RecaptchaV2(recaptcha_, tron.host + "faucet.php")
                if not cap:
                    continue
                data = (
                    "action=claim_hourly_faucet&g-recaptcha-response="
                    + cap
                    + "&h-captcha-response=null&captcha=&ft=&csrf_test_name="
                    + cookies.get("csrf_cookie_name", "")
                )
            elif turnstile_ and _re.search(turnstile_, r[1]):
                self._send("🔐 Turnstile hal qilinmoqda...")
                cap = (
                    self.iewil.Turnstile(turnstile_, tron.host + "faucet.php")
                    if self.iewil
                    else self.captcha.Turnstile(turnstile_, tron.host + "faucet.php")
                )
                if not cap:
                    continue
                data = (
                    "action=claim_hourly_faucet&clbt=1&g-recaptcha-response=null"
                    "&captcha=&h-captcha-response=null&c_captcha_response="
                    + cap
                    + "&csrf_test_name="
                    + cookies.get("csrf_cookie_name", "")
                )
            else:
                self._send_err("Sitekey topilmadi.")
                continue

            r2 = tron.safe_json_loads(
                tron.Requests.post(tron.host + "process.php", self.headers(), data)[1],
                "hourly_faucet"
            )
            if r2 is None:
                self._send_err("Server JSON qaytarmadi. Qayta urinilmoqda...")
                time.sleep(3)
                continue

            if r2.get("ret"):
                self._cetak("Number",  str(r2.get("num", "")))
                self._send_ok(r2.get("mes", ""))
                # Dashboard yangilash
                dash = self._quick_balance()
                self._cetak("Balance", dash)
                self._cetak("Bal_Api", str(self.captcha.getBalance()))
                self._line()
            else:
                if r2.get("mes"):
                    self._send_err(r2["mes"])
                else:
                    self._send(str(r2))
                self._line()

            # 1 soat countdown
            self._tmr(3600)

    def run_bonus(self):
        """ClaimBonus ekvivalenti."""
        import re as _re
        while True:
            r = tron.Requests.get(tron.host + "faucet.php", self.headers())
            try:
                bonus = r[1].split('<span id="free_spins">')[1].split("</span>")[0]
            except IndexError:
                bonus = None

            if not bonus:
                self._send_err("Bonus topilmadi.")
                break

            self._send(f"🎁 Bonus topildi: <b>{bonus}</b>. Claim qilinmoqda...")

            set_cookie_matches = _re.findall(
                r"^Set-Cookie:\s*([^;]*)", r[0], flags=_re.MULTILINE | _re.IGNORECASE
            )
            cookies = {}
            for item in set_cookie_matches:
                if "=" in item:
                    k_, v_ = item.split("=", 1)
                    cookies[k_] = v_

            data = "action=claim_bonus_faucet&csrf_test_name=" + cookies.get("csrf_cookie_name", "")
            r2 = tron.safe_json_loads(
                tron.Requests.post(tron.host + "process.php", self.headers(), data)[1],
                "claim_bonus"
            )
            if r2 is None:
                self._send_err("Server JSON qaytarmadi.")
                break
            if r2.get("ret"):
                self._cetak("Number",  str(r2.get("num", "")))
                self._send_ok(r2.get("mes", ""))
                bal = self._quick_balance()
                self._cetak("Balance", bal)
                self._line()

    def _quick_balance(self) -> str:
        try:
            r = tron.Requests.get(tron.host, self.headers())[1]
            return r.split(
                'class="drop_down_header_text user_balance">'
            )[1].split("<")[0]
        except Exception:
            return "—"


# ============================================================
#                     Telegram Handlerlar
# ============================================================

@bot.message_handler(commands=["start"])
@guard
def cmd_start(message):
    chat_id = message.chat.id
    sess = get_session(chat_id)

    if sess["state"] == "running":
        bot.send_message(chat_id, "⚙️ Bot allaqachon ishlayapti.")
        return

    tb = TronBot(chat_id)
    sess["tron_bot"] = tb

    # Alohida threadda ishlatamiz (blocking loop)
    t = threading.Thread(target=tb.start, daemon=True)
    t.start()


@bot.message_handler(commands=["stop"])
@guard
def cmd_stop(message):
    chat_id = message.chat.id
    sess = get_session(chat_id)
    sess["state"] = "idle"
    sess["tron_bot"] = None
    bot.send_message(chat_id, "🛑 Bot to'xtatildi. /start bilan qayta boshlang.")


@bot.message_handler(commands=["dashboard"])
@guard
def cmd_dashboard(message):
    chat_id = message.chat.id
    sess = get_session(chat_id)
    tb: TronBot = sess.get("tron_bot")
    if not tb or not tb.cookie:
        bot.send_message(chat_id, "⚠️ Avval /start qiling.")
        return
    bal = tb._quick_balance()
    tb._cetak("Balance", bal)
    tb._cetak("Bal_Api", str(tb.captcha.getBalance()) if tb.captcha else "—")


@bot.message_handler(commands=["cookie"])
@guard
def cmd_cookie(message):
    chat_id = message.chat.id
    sess = get_session(chat_id)
    tron.Functions.removeConfig("cookie")
    tron.Functions.removeConfig("user_agent")
    if sess.get("tron_bot"):
        sess["tron_bot"].cookie  = None
        sess["tron_bot"].uagent  = None
    bot.send_message(chat_id, "🔄 Cookie o'chirildi. /start bilan qayta kiriting.")
    sess["state"] = "idle"


@bot.message_handler(commands=["cap1"])
@guard
def cmd_cap1(message):
    chat_id = message.chat.id
    sess = get_session(chat_id)
    tron.Functions._save_config({**tron.Functions._load_config(), "type": "1"})
    _resume_input(sess, "1")
    bot.send_message(chat_id, "✅ Multibot tanlandi.")


@bot.message_handler(commands=["cap2"])
@guard
def cmd_cap2(message):
    chat_id = message.chat.id
    sess = get_session(chat_id)
    tron.Functions._save_config({**tron.Functions._load_config(), "type": "2"})
    _resume_input(sess, "2")
    bot.send_message(chat_id, "✅ Xevil tanlandi.")


@bot.message_handler(func=lambda m: True)
@guard
def handle_text(message):
    """
    Foydalanuvchi matn yozganda:
    - agar bot input kutayotgan bo'lsa → javobni uzatadi
    - aks holda → menyu ko'rsatadi
    """
    chat_id = message.chat.id
    sess = get_session(chat_id)
    text = message.text.strip()

    if sess["state"] == "waiting_input":
        _resume_input(sess, text)
        return

    tb: TronBot = sess.get("tron_bot")
    if tb:
        tb._menu()
    else:
        bot.send_message(chat_id, "ℹ️ /start buyrug'ini yuboring.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu(call):
    chat_id = call.message.chat.id
    sess = get_session(chat_id)
    tb: TronBot = sess.get("tron_bot")

    if not tb:
        bot.answer_callback_query(call.id, "Avval /start qiling.")
        return

    action = call.data

    if action == "menu_1":
        bot.answer_callback_query(call.id, "Bonus claim boshlandi...")
        t = threading.Thread(target=tb.run_bonus, daemon=True)
        t.start()

    elif action == "menu_2":
        bot.answer_callback_query(call.id, "Hourly loop boshlandi...")
        t = threading.Thread(target=tb.run_hourly, daemon=True)
        t.start()

    elif action == "menu_dash":
        bot.answer_callback_query(call.id)
        bal = tb._quick_balance()
        tb._cetak("Balance", bal)
        tb._cetak("Bal_Api", str(tb.captcha.getBalance()) if tb.captcha else "—")

    elif action == "menu_cookie":
        bot.answer_callback_query(call.id)
        tron.Functions.removeConfig("cookie")
        tron.Functions.removeConfig("user_agent")
        tb.cookie  = None
        tb.uagent  = None
        sess["state"] = "idle"
        bot.send_message(chat_id, "🔄 Cookie o'chirildi. /start yuboring.")


# ============================================================
#                        Yordamchi
# ============================================================

def _resume_input(sess: dict, value: str):
    """Input kutayotgan thread'ni uyg'otadi."""
    sess["input_value"] = value
    sess["input_event"].set()


# ============================================================
#                          Main
# ============================================================
if __name__ == "__main__":
    log.info("Tronpick Telegram Bot ishga tushdi.")
    log.info("Bot token: %s", BOT_TOKEN[:10] + "...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
