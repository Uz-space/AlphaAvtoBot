import logging
import asyncio
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ===================== TOKEN & ID =====================
BOT_TOKEN = "8930805461:AAGd7e2qPGqu7lJjOLO-Pv1Ha9DkbbniyxM"
ADMIN_IDS = [8758410535]
# ======================================================

logging.basicConfig(level=logging.INFO)

CRYPTO_DATA = {
    "BTC":  {"name": "Bitcoin",  "emoji_id": "5215346446429103945", "color": "danger"},
    "ETH":  {"name": "Ethereum", "emoji_id": "5215357136602698456", "color": "primary"},
    "BNB":  {"name": "BNB",      "emoji_id": "5215553828924995476", "color": "success"},
    "SOL":  {"name": "Solana",   "emoji_id": "5215299923343353183", "color": "primary"},
    "LTC":  {"name": "Litecoin", "emoji_id": "5215555130300080404", "color": "success"},
    "TON":  {"name": "Toncoin",  "emoji_id": "5215261504860891404", "color": "primary"},
    "TRX":  {"name": "TRON",     "emoji_id": "5215509887114584038", "color": "danger"},
    "DOGE": {"name": "Dogecoin", "emoji_id": "5215634149108392152", "color": "success"},
}

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "addresses.json")

def load_addresses():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k in CRYPTO_DATA:
                data.setdefault(k, "")
            return data
        except Exception as e:
            logging.error(f"load_addresses xato: {e}")
    return {k: "" for k in CRYPTO_DATA}

def save_addresses(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"save_addresses xato: {e}")

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS

# ── progress bar ──────────────────────────────────────
def progress_text(pct: int) -> str:
    filled = int(pct / 100 * 20)
    bar    = "▓" * filled + "░" * (20 - filled)
    return f"```\n{bar}{pct:>4}%\n```"

# ── klaviaturalar ─────────────────────────────────────
def main_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for code, info in CRYPTO_DATA.items():
        rows.append([InlineKeyboardButton(
            text=f"{info['name']} ({code})",
            callback_data=f"c_{code}",
            style=info["color"],
            icon_custom_emoji_id=info["emoji_id"],
        )])
    return InlineKeyboardMarkup(rows)

def admin_keyboard() -> InlineKeyboardMarkup:
    addrs = load_addresses()
    rows  = []
    for code, info in CRYPTO_DATA.items():
        has = bool(addrs.get(code, ""))
        rows.append([InlineKeyboardButton(
            text=f"{'✅' if has else '➕'} {code} — {'yangilash' if has else 'kiritish'}",
            callback_data=f"ae_{code}",
            style="success" if has else "danger",
            icon_custom_emoji_id=info["emoji_id"],
        )])
    return InlineKeyboardMarkup(rows)

# ═══════════════════════════════════════════════════════
#  /start
# ═══════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # conversation state ni tozalash
    context.user_data.clear()

    items = list(CRYPTO_DATA.items())
    msg   = await update.message.reply_text(progress_text(0), parse_mode="Markdown")
    rows  = []

    for i, (code, info) in enumerate(items):
        await asyncio.sleep(0.35)
        rows.append([InlineKeyboardButton(
            text=f"{info['name']} ({code})",
            callback_data=f"c_{code}",
            style=info["color"],
            icon_custom_emoji_id=info["emoji_id"],
        )])
        pct = int((i + 1) / len(items) * 100)
        try:
            await msg.edit_text(
                progress_text(pct),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(rows),
            )
        except Exception:
            pass

# ═══════════════════════════════════════════════════════
#  Crypto tugma → manzilni ko'rsatish
# ═══════════════════════════════════════════════════════
async def on_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    code = q.data[2:]          # "c_BTC" → "BTC"
    info = CRYPTO_DATA.get(code)
    if not info:
        return

    addr  = load_addresses().get(code, "")
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'
    text  = (
        f"{emoji} <b>{info['name']} ({code})</b>\n\n<code>{addr}</code>"
        if addr else
        f"{emoji} <b>{info['name']} ({code})</b>\n\n❌ Manzil hali kiritilmagan"
    )
    back = InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Bosh sahifa", callback_data="home", style="primary")
    ]])
    try:
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=back)
    except Exception:
        pass

# ═══════════════════════════════════════════════════════
#  Bosh sahifa tugmasi
# ═══════════════════════════════════════════════════════
async def on_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        await q.edit_message_text(
            progress_text(100),
            parse_mode="Markdown",
            reply_markup=main_keyboard(),
        )
    except Exception:
        pass

# ═══════════════════════════════════════════════════════
#  /admin
# ═══════════════════════════════════════════════════════
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin emassiz!")
        return
    context.user_data.clear()   # avvalgi kutish holatini tozalash
    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\nQaysi cryptoni tahrirlash?",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )

# ═══════════════════════════════════════════════════════
#  Admin: tahrirlash tugmasi bosildi  →  manzil so'rash
# ═══════════════════════════════════════════════════════
async def on_admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("❌ Ruxsat yo'q!", show_alert=True)
        return
    await q.answer()

    code = q.data[3:]           # "ae_BTC" → "BTC"
    info = CRYPTO_DATA.get(code, {})
    cur  = load_addresses().get(code, "")
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'
    cur_line = f"\n\nHozirgi: <code>{cur}</code>" if cur else "\n\nHozirgi: <i>yo'q</i>"

    # Kutish holatini saqlash
    context.user_data["waiting"] = code

    cancel_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Bekor", callback_data="cancel", style="danger")
    ]])
    try:
        await q.edit_message_text(
            f"{emoji} <b>{code}</b> uchun yangi manzilni yuboring:{cur_line}",
            parse_mode="HTML",
            reply_markup=cancel_btn,
        )
    except Exception:
        pass

# ═══════════════════════════════════════════════════════
#  Admin: bekor qilish
# ═══════════════════════════════════════════════════════
async def on_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    try:
        await q.edit_message_text(
            "⚙️ <b>Admin Panel</b>\n\nQaysi cryptoni tahrirlash?",
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )
    except Exception:
        pass

# ═══════════════════════════════════════════════════════
#  Matn xabari keldi  →  faqat admin + waiting holat
# ═══════════════════════════════════════════════════════
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    code = context.user_data.get("waiting")

    # Admin emas yoki kutish holati yo'q → e'tiborsiz
    if not is_admin(uid) or not code:
        return

    new_addr = update.message.text.strip()
    if not new_addr:
        await update.message.reply_text("❌ Bo'sh manzil. Qaytadan yuboring:")
        return

    # Saqlash
    addrs       = load_addresses()
    addrs[code] = new_addr
    save_addresses(addrs)

    # Kutish holatini tozalash
    context.user_data.clear()

    info  = CRYPTO_DATA.get(code, {})
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'

    await update.message.reply_text(
        f"{emoji} ✅ <b>{code}</b> manzili saqlandi!\n\n<code>{new_addr}</code>",
        parse_mode="HTML",
    )

    # Yangilangan admin panelni ko'rsat
    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\nQaysi cryptoni tahrirlash?",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )

# ═══════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))

    app.add_handler(CallbackQueryHandler(on_crypto,     pattern=r"^c_"))
    app.add_handler(CallbackQueryHandler(on_home,       pattern=r"^home$"))
    app.add_handler(CallbackQueryHandler(on_admin_edit, pattern=r"^ae_"))
    app.add_handler(CallbackQueryHandler(on_cancel,     pattern=r"^cancel$"))

    # Barcha matn xabarlari — ConversationHandler YO'Q
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    print("🤖 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
