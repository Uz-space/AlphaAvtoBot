import logging
import asyncio
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ===================== TOKEN & ID =====================
BOT_TOKEN = "8930805461:AAGd7e2qPGqu7lJjOLO-Pv1Ha9DkbbniyxM"
ADMIN_IDS = [8758410535]
# ======================================================

logging.basicConfig(level=logging.INFO)

# ==================== CRYPTO MA'LUMOTLARI ====================
CRYPTO_DATA = {
    "BTC": {"name": "Bitcoin",  "emoji_id": "5215346446429103945", "color": "danger"},
    "ETH": {"name": "Ethereum", "emoji_id": "5215357136602698456", "color": "primary"},
    "BNB": {"name": "BNB",      "emoji_id": "5215553828924995476", "color": "success"},
    "SOL": {"name": "Solana",   "emoji_id": "5215299923343353183", "color": "primary"},
    "LTC": {"name": "Litecoin", "emoji_id": "5215555130300080404", "color": "success"},
    "TON": {"name": "Toncoin",  "emoji_id": "5215261504860891404", "color": "primary"},
    "TRX": {"name": "TRON",     "emoji_id": "5215509887114584038", "color": "danger"},
    "DOGE": {"name": "Dogecoin","emoji_id": "5215634149108392152", "color": "success"},
}

# ==================== FAYL BILAN ISHLASH ====================
# Har doim bot.py turgan papkada saqlanadi
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "addresses.json")

def load_addresses():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for k in CRYPTO_DATA:
                    if k not in data:
                        data[k] = ""
                return data
        except Exception as e:
            logging.error(f"addresses.json o'qishda xato: {e}")
    return {k: "" for k in CRYPTO_DATA}

def save_addresses(addresses):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(addresses, f, indent=2, ensure_ascii=False)
        logging.info(f"Saqlandi: {DATA_FILE}")
    except Exception as e:
        logging.error(f"Saqlashda xato: {e}")

crypto_addresses = load_addresses()

# ==================== CONVERSATION STATE ====================
WAITING_ADDRESS = 1

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ==================== YORDAMCHI FUNKSIYALAR ====================
def build_main_keyboard() -> InlineKeyboardMarkup:
    """Asosiy crypto tugmalar klaviaturasini yaratish"""
    keyboard = []
    for code, info in CRYPTO_DATA.items():
        keyboard.append([InlineKeyboardButton(
            text=f"{info['name']} ({code})",
            callback_data=f"crypto_{code}",
            style=info.get("color", "primary"),
            icon_custom_emoji_id=info["emoji_id"],
        )])
    return InlineKeyboardMarkup(keyboard)

def create_progress(percent: int):
    filled = int(percent / 100 * 20)
    empty = 20 - filled
    progress_bar = "▓" * filled + "░" * empty
    percent_text = f"{percent:>4}%"
    return f"{progress_bar}{percent_text}"

# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tugmalarni birma-bir chiqarish"""
    msg = await update.message.reply_text(
        f"```\n{create_progress(0)}\n```",
        parse_mode="Markdown"
    )

    crypto_list = list(CRYPTO_DATA.items())
    keyboard = []

    for i, (code, info) in enumerate(crypto_list):
        await asyncio.sleep(0.35)
        keyboard.append([InlineKeyboardButton(
            text=f"{info['name']} ({code})",
            callback_data=f"crypto_{code}",
            style=info.get("color", "primary"),
            icon_custom_emoji_id=info["emoji_id"],
        )])
        percent = int((i + 1) / len(crypto_list) * 100)
        try:
            await msg.edit_text(
                f"```\n{create_progress(percent)}\n```",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception:
            pass  # MessageNotModified xatoligini e'tiborsiz qoldirish

# ==================== CRYPTO TUGMA BOSILGANDA ====================
async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    info = CRYPTO_DATA.get(crypto)
    if not info:
        return

    # Har safar fayldan o'qish
    addresses = load_addresses()
    address = addresses.get(crypto, "")
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'

    back_btn = [[InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")]]

    text = (
        f"{emoji} <b>{info['name']} ({crypto})</b>\n\n"
        f"<code>{address}</code>"
        if address else
        f"{emoji} <b>{info['name']} ({crypto})</b>\n\n"
        f"❌ Manzil hali kiritilmagan"
    )

    # Agar xabar allaqachon shu matnda bo'lsa xatolik chiqmasligi uchun try/except
    try:
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(back_btn),
        )
    except Exception:
        pass

# ==================== BOSH SAHIFAGA QAYTISH ====================
async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        await query.edit_message_text(
            f"```\n{create_progress(100)}\n```",
            parse_mode="Markdown",
            reply_markup=build_main_keyboard(),
        )
    except Exception:
        pass

# ==================== ADMIN PANEL ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin emassiz!")
        return

    # Har safar fayldan o'qish
    addresses = load_addresses()

    keyboard = []
    for crypto, info in CRYPTO_DATA.items():
        addr = addresses.get(crypto, "")
        btn_text = f"✅ {crypto} — yangilash" if addr else f"➕ {crypto} — kiritish"
        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"admin_edit_{crypto}",
            style="success" if addr else "danger",
            icon_custom_emoji_id=info["emoji_id"],
        )])

    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\nQaysi cryptoni tahrirlash?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ConversationHandler.END

# ==================== ADMIN: TAHRIRLASH BOSHLASH ====================
async def admin_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not is_admin(query.from_user.id):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    crypto = query.data.replace("admin_edit_", "")

    # State ni context.user_data ga saqlash (xavfsiz usul)
    context.user_data["edit_crypto"] = crypto

    info = CRYPTO_DATA.get(crypto, {})
    current = load_addresses().get(crypto, "")
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'
    current_text = f"\n\nHozirgi: <code>{current}</code>" if current else "\n\nHozirgi: <i>yo'q</i>"

    try:
        await query.edit_message_text(
            f"{emoji} <b>{crypto}</b> uchun yangi manzilni yuboring:{current_text}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="cancel_action", style="danger")
            ]]),
        )
    except Exception:
        pass

    return WAITING_ADDRESS

# ==================== ADMIN: MANZILNI QABUL QILISH ====================
async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    crypto = context.user_data.get("edit_crypto")
    if not crypto:
        await update.message.reply_text("❌ Xatolik: qaysi crypto belgilanmagan.")
        return ConversationHandler.END

    new_address = update.message.text.strip()
    if not new_address:
        await update.message.reply_text("❌ Bo'sh manzil qabul qilinmadi.")
        return WAITING_ADDRESS

    # Fayldan o'qib, yangilab, qayta saqlash
    addresses = load_addresses()
    addresses[crypto] = new_address
    save_addresses(addresses)

    context.user_data.pop("edit_crypto", None)

    info = CRYPTO_DATA.get(crypto, {})
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'

    # Tasdiqlash
    await update.message.reply_text(
        f"{emoji} ✅ <b>{crypto}</b> manzili saqlandi!\n\n"
        f"<code>{new_address}</code>",
        parse_mode="HTML",
    )

    # Yangilangan holatda admin panelni ko'rsatish
    fresh = load_addresses()

    keyboard = []
    for c, inf in CRYPTO_DATA.items():
        addr = fresh.get(c, "")
        btn_text = f"✅ {c} — yangilash" if addr else f"➕ {c} — kiritish"
        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"admin_edit_{c}",
            style="success" if addr else "danger",
            icon_custom_emoji_id=inf["emoji_id"],
        )])

    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\nQaysi cryptoni tahrirlash?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return ConversationHandler.END

# ==================== BEKOR QILISH ====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("edit_crypto", None)

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text("❌ Bekor qilindi.")
        except Exception:
            pass
    elif update.message:
        await update.message.reply_text("❌ Bekor qilindi.")

    return ConversationHandler.END

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler — admin tahrirlash uchun
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("admin", admin_panel),
            CallbackQueryHandler(admin_edit_callback, pattern=r"^admin_edit_"),
        ],
        states={
            WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address),
                CallbackQueryHandler(cancel, pattern=r"^cancel_action$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CallbackQueryHandler(cancel, pattern=r"^cancel_action$"),
        ],
        per_message=False,
        per_chat=True,
        per_user=True,
        allow_reentry=True,
    )

    # Handler tartib muhim: ConversationHandler birinchi!
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(crypto_callback, pattern=r"^crypto_"))
    app.add_handler(CallbackQueryHandler(back_start, pattern=r"^back_start$"))

    print("🤖 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
