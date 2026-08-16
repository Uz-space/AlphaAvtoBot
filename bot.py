#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tron.py uchun Telegram Bot Wrapper
Barcha input() chaqiruvlarini Telegram xabarlari bilan almashtiradi.
pip install python-telegram-bot --break-system-packages
"""

import os
import sys
import json
import time
import logging
import threading
from enum import Enum, auto
from typing import Optional

from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# tron.py bir xil papkada bo'lishi kerak
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tron as T

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────
BOT_TOKEN   = os.environ.get("TG_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_IDS = set()  # Bo'sh = hamma foydalana oladi. To'ldirish: {123456789, 987654321}

CONFIG_FILE = "tronpick_config.json"

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────
# STATE MACHINE
# ──────────────────────────────────────────
class S(Enum):
    WAIT_COOKIE       = auto()
    WAIT_USER_AGENT   = auto()
    WAIT_CAPTCHA_TYPE = auto()
    WAIT_API_KEY      = auto()
    MENU              = auto()
    RUNNING           = auto()


# ──────────────────────────────────────────
# GUARDS
# ──────────────────────────────────────────
def _allowed(update: Update) -> bool:
    if not ALLOWED_IDS:
        return True
    return update.effective_user.id in ALLOWED_IDS


async def _deny(update: Update) -> None:
    await update.message.reply_text("❌ Ruxsat yo'q.")


# ──────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────
def _load_cfg() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cfg(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=4)


def _set_cfg(key: str, value: str) -> None:
    cfg = _load_cfg()
    cfg[key] = value
    _save_cfg(cfg)


def _get_cfg(key: str) -> Optional[str]:
    return _load_cfg().get(key)


def _del_cfg(key: str) -> None:
    cfg = _load_cfg()
    cfg.pop(key, None)
    _save_cfg(cfg)


def _strip_ansi(text: str) -> str:
    """ANSI rang kodlarini olib tashlaydi."""
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


def _build_bot_instance(context: ContextTypes.DEFAULT_TYPE) -> T.Bot.__class__:
    """Bot classini to'g'ridan-to'g'ri emas, classlarini alohida yaratadi."""
    cookie   = _get_cfg("cookie") or ""
    uagent   = _get_cfg("user_agent") or ""
    cap_type = _get_cfg("type") or "1"

    class BotCore:
        def __init__(self):
            self.cookie  = cookie
            self.uagent  = uagent
            self.scrap   = T.HtmlScrap()
            self.cf      = T.Cloudflare()
            self.captcha = _make_captcha(cap_type)
            self.iewil   = None

        def headers(self):
            from urllib.parse import urlparse
            return [
                "Host: " + urlparse(T.host).hostname,
                "cookie: " + self.cookie,
                "X-Requested-With: XMLHttpRequest",
                "user-agent: " + self.uagent,
            ]

        def Dashboard(self):
            r = T.Requests.get(T.host, self.headers())[1]
            data = {}
            import re
            data["cloudflare"] = 1 if re.search(r"Just a moment\.\.\.", r) else 0
            data["Login"]      = "" if re.search(r"login_button", r) else 1
            try:
                data["Username"] = r.split("&username=")[1].split("&")[0].strip()
            except IndexError:
                data["Username"] = "N/A"
            try:
                data["Balance"] = r.split('class="drop_down_header_text user_balance">')[1].split("<")[0]
            except IndexError:
                data["Balance"] = "N/A"
            return data

    return BotCore()


def _make_captcha(cap_type: str) -> T.Captcha:
    """Captcha objectini config dan yaratadi (input() chaqirmaydi)."""
    obj = object.__new__(T.Captcha)
    if cap_type == "1":
        obj.url      = "http://api.multibot.in/"
        obj.key      = _get_cfg("multibot_apikey") or ""
        obj.provider = "Multibot"
    else:
        obj.url      = "https://sctg.xyz/"
        obj.key      = (_get_cfg("xevil_apikey") or "") + "|SOFTID1204538927"
        obj.provider = "Xevil"
    return obj


# ──────────────────────────────────────────
# /start
# ──────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        await _deny(update)
        return ConversationHandler.END

    cookie = _get_cfg("cookie")
    if cookie:
        await update.message.reply_text(
            f"✅ Cookie mavjud. /menu buyrug'ini yuboring.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return S.MENU

    await update.message.reply_text(
        "🍪 *Cookie kiriting:*\n\n"
        "Brauzer → tronpick.io → F12 → Network → Request Headers → `cookie:` qiymatini nusxalang.",
        parse_mode="Markdown",
    )
    return S.WAIT_COOKIE


# ──────────────────────────────────────────
# SETUP FLOW: cookie → user_agent → captcha_type → api_key
# ──────────────────────────────────────────
async def recv_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return ConversationHandler.END

    cookie = update.message.text.strip()
    if len(cookie) < 20:
        await update.message.reply_text("❌ Cookie juda qisqa. Qayta yuboring:")
        return S.WAIT_COOKIE

    _set_cfg("cookie", cookie)
    await update.message.reply_text("✅ Cookie saqlandi.\n\n🖥 *User-Agent* kiriting:")
    return S.WAIT_USER_AGENT


async def recv_user_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return ConversationHandler.END

    ua = update.message.text.strip()
    if len(ua) < 20:
        await update.message.reply_text("❌ User-agent noto'g'ri ko'rinadi. Qayta yuboring:")
        return S.WAIT_USER_AGENT

    _set_cfg("user_agent", ua)

    kb = [["1 - Multibot", "2 - Xevil"]]
    await update.message.reply_text(
        "🔐 *Captcha API turini tanlang:*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
    )
    return S.WAIT_CAPTCHA_TYPE


async def recv_captcha_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return ConversationHandler.END

    txt = update.message.text.strip()[0]  # "1" yoki "2"
    if txt not in ("1", "2"):
        await update.message.reply_text("1 yoki 2 yuboring:")
        return S.WAIT_CAPTCHA_TYPE

    _set_cfg("type", txt)
    context.user_data["cap_type"] = txt

    if txt == "1":
        await update.message.reply_text(
            "🔑 *Multibot API key* kiriting:\nRo'yxatdan o'tish: http://api.multibot.in",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            "🔑 *Xevil API key* kiriting:\nt.me/Xevil_check_bot",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )
    return S.WAIT_API_KEY


async def recv_api_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return ConversationHandler.END

    key     = update.message.text.strip()
    cap_type = context.user_data.get("cap_type", _get_cfg("type") or "1")

    if cap_type == "1":
        _set_cfg("multibot_apikey", key)
    else:
        _set_cfg("xevil_apikey", key)

    await update.message.reply_text("✅ Sozlash tugadi!\n\n/menu buyrug'ini yuboring.")
    return S.MENU


# ──────────────────────────────────────────
# /menu
# ──────────────────────────────────────────
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return ConversationHandler.END

    # Cookie tekshirish
    if not _get_cfg("cookie"):
        await update.message.reply_text("❌ Avval /start bilan sozlang.")
        return ConversationHandler.END

    # Dashboard ma'lumoti
    try:
        core = _build_bot_instance(context)
        dash = core.Dashboard()
    except Exception as e:
        await update.message.reply_text(f"❌ Dashboard xatosi: {e}")
        return ConversationHandler.END

    if dash.get("cloudflare"):
        await update.message.reply_text("⚠️ Cloudflare aniqlandi. Cookie yangilang: /reset")
        return ConversationHandler.END

    if not dash.get("Login"):
        _del_cfg("cookie")
        _del_cfg("user_agent")
        await update.message.reply_text("❌ Cookie muddati tugagan. /start bilan qaytadan kiring.")
        return ConversationHandler.END

    cap_type = _get_cfg("type") or "1"
    cap_obj  = _make_captcha(cap_type)
    try:
        bal_api = cap_obj.getBalance()
    except Exception:
        bal_api = "N/A"

    kb = [["1️⃣ Claim Bonus", "2️⃣ Hourly Faucet"]]
    await update.message.reply_text(
        f"👤 *{dash.get('Username','?')}*\n"
        f"💰 Balans: `{dash.get('Balance','?')}`\n"
        f"🔑 API balans: `{bal_api}`\n\n"
        f"Nima qilasiz?",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
    )
    context.user_data["waiting_menu"] = True
    return ConversationHandler.END


async def recv_menu_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return
    if not context.user_data.get("waiting_menu"):
        return  # Bu handler faqat /menu dan keyin ishlaydi

    txt = update.message.text.strip()
    if "1" in txt:
        action = "bonus"
    elif "2" in txt:
        action = "hourly"
    else:
        await update.message.reply_text("1 yoki 2 tanlang:")
        return

    context.user_data["action"] = action
    await update.message.reply_text(
        "⚙️ Ishga tushirildi... Natija keladi.",
        reply_markup=ReplyKeyboardRemove(),
    )

    # Threading: bot bloklanmasin
    thread = threading.Thread(
        target=_run_action,
        args=(update, context, action),
        daemon=True,
    )
    context.user_data["waiting_menu"] = False
    thread.start()


def _run_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """Bloklayuvchi tron.py funksiyalarini alohida threadda ishlatadi."""
    import asyncio

    async def _send(msg: str):
        clean = _strip_ansi(msg)[:4000]
        if clean.strip():
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=clean,
            )

    loop = asyncio.new_event_loop()

    try:
        core = _build_bot_instance(context)

        if action == "bonus":
            loop.run_until_complete(_send("🎰 Bonus claim boshlanmoqda..."))
            _run_claim_bonus(core, loop, update, context)

        elif action == "hourly":
            loop.run_until_complete(_send("⏰ Hourly faucet boshlanmoqda..."))
            _run_hourly(core, loop, update, context)

    except Exception as e:
        loop.run_until_complete(_send(f"❌ Xato: {e}"))
    finally:
        loop.close()


def _run_claim_bonus(core, loop, update, context):
    """ClaimBonus logikasi — terminal output ni Telegram ga yo'naltiradi."""
    import asyncio, re as _re

    async def send(msg):
        clean = _strip_ansi(str(msg))[:4000]
        if clean.strip():
            await context.bot.send_message(chat_id=update.effective_chat.id, text=clean)

    T_Requests = T.Requests

    while True:
        r = T_Requests.get(T.host + "faucet.php", core.headers())
        try:
            bonus = r[1].split('<span id="free_spins">')[1].split("</span>")[0]
        except IndexError:
            bonus = None

        if not bonus:
            loop.run_until_complete(send("ℹ️ Bonus yo'q."))
            break

        set_cookie_matches = _re.findall(
            r"^Set-Cookie:\s*([^;]*)", r[0], flags=_re.MULTILINE | _re.IGNORECASE
        )
        cookies = {}
        for item in set_cookie_matches:
            if "=" in item:
                k_, v_ = item.split("=", 1)
                cookies[k_] = v_

        data = "action=claim_bonus_faucet&csrf_test_name=" + cookies.get("csrf_cookie_name", "")
        r2 = T.safe_json_loads(
            T_Requests.post(T.host + "process.php", core.headers(), data)[1], "claim_bonus"
        )

        if r2 is None:
            loop.run_until_complete(send("❌ Server JSON qaytarmadi. Qayta urinilmoqda..."))
            time.sleep(3)
            continue

        if r2.get("ret"):
            msg = (
                f"✅ {r2.get('mes','')}\n"
                f"🎯 Raqam: {r2.get('num','')}\n"
                f"💰 Balans: {core.Dashboard().get('Balance','?')}"
            )
            loop.run_until_complete(send(msg))
        else:
            loop.run_until_complete(send(f"⚠️ {r2.get('mes', str(r2))}"))
        break


def _run_hourly(core, loop, update, context):
    """HourlyFaucet logikasi — cheksiz loop, har soat bir marta claim."""
    import asyncio, re as _re

    async def send(msg):
        clean = _strip_ansi(str(msg))[:4000]
        if clean.strip():
            await context.bot.send_message(chat_id=update.effective_chat.id, text=clean)

    T_Requests = T.Requests
    retry = 0

    while True:
        r = T_Requests.get(T.host + "faucet.php", core.headers())
        cek = core.scrap.Result(r[1])

        if cek.get("cloudflare"):
            loop.run_until_complete(send(f"⚠️ Cloudflare aniqlandi ({retry}). Cookie yangilang."))
            retry += 1
            if retry > 3:
                loop.run_until_complete(send("❌ Cloudflare bypass muvaffaqiyatsiz. /reset yuboring."))
                return
            time.sleep(30)
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
        recaptcha_ = T.recaptcha
        cap = None
        if recaptcha_ and _re.search(recaptcha_, r[1]):
            loop.run_until_complete(send("🤖 RecaptchaV2 hal qilinmoqda..."))
            cap = core.captcha.RecaptchaV2(recaptcha_, T.host + "faucet.php")
            if not cap:
                loop.run_until_complete(send("❌ Captcha hal qilinmadi. Qayta urinilmoqda..."))
                time.sleep(10)
                continue
            data = (
                "action=claim_hourly_faucet&g-recaptcha-response="
                + cap
                + "&h-captcha-response=null&captcha=&ft=&csrf_test_name="
                + cookies.get("csrf_cookie_name", "")
            )
        elif T.turnstile and _re.search(T.turnstile, r[1]):
            loop.run_until_complete(send("🤖 Turnstile hal qilinmoqda..."))
            cap = core.captcha.Turnstile(T.turnstile, T.host + "faucet.php")
            if not cap:
                time.sleep(10)
                continue
            data = (
                "action=claim_hourly_faucet&clbt=1&g-recaptcha-response=null&captcha=&h-captcha-response=null&c_captcha_response="
                + cap
                + "&csrf_test_name="
                + cookies.get("csrf_cookie_name", "")
            )
        else:
            loop.run_until_complete(send("❌ Captcha sitekey topilmadi."))
            time.sleep(30)
            continue

        r2 = T.safe_json_loads(
            T_Requests.post(T.host + "process.php", core.headers(), data)[1], "hourly_faucet"
        )

        if r2 is None:
            loop.run_until_complete(send("❌ Server JSON qaytarmadi. Qayta urinilmoqda..."))
            time.sleep(10)
            continue

        if r2.get("ret"):
            try:
                bal_api = core.captcha.getBalance()
            except Exception:
                bal_api = "N/A"
            msg = (
                f"✅ {r2.get('mes','')}\n"
                f"🎯 Raqam: {r2.get('num','')}\n"
                f"💰 Balans: {core.Dashboard().get('Balance','?')}\n"
                f"🔑 API balans: {bal_api}\n\n"
                f"⏳ 1 soatdan keyin qayta claim qilinadi..."
            )
            loop.run_until_complete(send(msg))
        else:
            msg = r2.get("mes", str(r2))
            loop.run_until_complete(send(f"⚠️ {msg}"))

        # 3600 soniya kutish — har 60 soniyada bir xabar
        total = 3600
        for remaining in range(total, 0, -60):
            h_left = remaining // 3600
            m_left = (remaining % 3600) // 60
            s_left = remaining % 60
            if remaining % 300 == 0:  # har 5 daqiqada xabar
                loop.run_until_complete(
                    send(f"⏳ Keyingi claim: {h_left:02d}:{m_left:02d}:{s_left:02d}")
                )
            time.sleep(60)


# ──────────────────────────────────────────
# /status
# ──────────────────────────────────────────
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _allowed(update):
        return

    cookie = _get_cfg("cookie")
    if not cookie:
        await update.message.reply_text("❌ Cookie yo'q. /start yuboring.")
        return

    try:
        core = _build_bot_instance(context)
        dash = core.Dashboard()
        cap_obj = _make_captcha(_get_cfg("type") or "1")
        bal_api = cap_obj.getBalance()
    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")
        return

    await update.message.reply_text(
        f"📊 *Status*\n"
        f"👤 Username: `{dash.get('Username','?')}`\n"
        f"💰 Balans: `{dash.get('Balance','?')}`\n"
        f"🔑 API balans: `{bal_api}`\n"
        f"☁️ Cloudflare: `{'Ha' if dash.get('cloudflare') else 'Yoq'}`",
        parse_mode="Markdown",
    )


# ──────────────────────────────────────────
# /reset — cookie va user_agent ni o'chiradi
# ──────────────────────────────────────────
async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _allowed(update):
        return ConversationHandler.END

    _del_cfg("cookie")
    _del_cfg("user_agent")
    await update.message.reply_text(
        "🔄 Cookie va User-Agent o'chirildi.\n/start bilan qaytadan kiring.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ──────────────────────────────────────────
# /cancel
# ──────────────────────────────────────────
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ──────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("TG_BOT_TOKEN muhit o'zgaruvchisini o'rnating!")
        print("Misol: export TG_BOT_TOKEN='123456:ABC-DEF...'")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # Setup flow faqat: /start → cookie → ua → captcha type → api key
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
        ],
        states={
            S.WAIT_COOKIE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_cookie)],
            S.WAIT_USER_AGENT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_user_agent)],
            S.WAIT_CAPTCHA_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_captcha_type)],
            S.WAIT_API_KEY:      [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_api_key)],
            S.MENU:              [MessageHandler(filters.TEXT & ~filters.COMMAND, recv_menu_choice)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            CommandHandler("reset",  cmd_reset),
        ],
        per_message=False,
        allow_reentry=True,
    )

    # /menu, /status, /reset — conversation dan tashqarida, har doim ishlaydi
    app.add_handler(conv)
    app.add_handler(CommandHandler("menu",   cmd_menu))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("reset",  cmd_reset))
    # Keyboard javobini ushlaydi (faqat waiting_menu=True bo'lsa)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recv_menu_choice))

    log.info("Bot ishga tushdi. /start yuboring.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
