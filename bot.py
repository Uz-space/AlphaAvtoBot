import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ===================== TOKEN =====================
BOT_TOKEN = "8768572368:AAF20AL0KGW8AziA9WsPx4XHZDAJjB6zZys"
ADMIN_IDS = [8758410535]  # BU YERGA O'Z TELEGRAM ID INGIZNI YOZING
# =================================================

logging.basicConfig(level=logging.INFO)

# Crypto ma'lumotlari
CRYPTOS = ["BTC", "ETH", "BNB", "SOL", "LTC", "TON", "TRX", "DOGE"]

CRYPTO_EMOJIS = {
    "BTC":  "5215346446429103945",
    "ETH":  "5215357136602698456",
    "BNB":  "5215553828924995476",
    "SOL":  "5215299923343353183",
    "LTC":  "5215555130300080404",
    "TON":  "5215261504860891404",
    "TRX":  "5215509887114584038",
    "DOGE": "5215634149108392152",
}

# Adreslar (admin panel orqali o'zgartiriladi)
crypto_addresses = {
    "BTC":  "",
    "ETH":  "",
    "BNB":  "",
    "SOL":  "",
    "LTC":  "",
    "TON":  "",
    "TRX":  "",
    "DOGE": "",
}

# ConversationHandler states
WAITING_ADDRESS = 1
admin_edit_target = {}  # user_id -> crypto nomi


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def custom_emoji(crypto: str) -> str:
    eid = CRYPTO_EMOJIS[crypto]
    return f'<tg-emoji emoji-id="{eid}">🪙</tg-emoji>'


# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for crypto in CRYPTOS:
        btn = InlineKeyboardButton(
            text=f"{crypto}",
            callback_data=f"crypto_{crypto}",
            icon_custom_emoji_id=CRYPTO_EMOJIS[crypto]
        )
        keyboard.append([btn])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💰 <b>Crypto To'lov Tizimi</b>\n\n"
        "Qaysi crypto orqali to'lov qilmoqchisiz?\n"
        "Tanlang 👇",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


# ==================== Crypto tanlash ====================
async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    address = crypto_addresses.get(crypto, "")

    emoji_tag = custom_emoji(crypto)

    if not address:
        await query.edit_message_text(
            f"{emoji_tag} <b>{crypto}</b> adresi hali sozlanmagan.\n\n"
            "Admin tez orada qo'shadi!",
            parse_mode="HTML"
        )
        return

    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_start")]]
    await query.edit_message_text(
        f"{emoji_tag} <b>{crypto} Adres:</b>\n\n"
        f"<code>{address}</code>\n\n"
        "Yuqoridagi adresga to'lovingizni yuboring. ✅",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ==================== Orqaga qaytish ====================
async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for crypto in CRYPTOS:
        btn = InlineKeyboardButton(
            text=f"{crypto}",
            callback_data=f"crypto_{crypto}",
            icon_custom_emoji_id=CRYPTO_EMOJIS[crypto]
        )
        keyboard.append([btn])

    await query.edit_message_text(
        "💰 <b>Crypto To'lov Tizimi</b>\n\n"
        "Qaysi crypto orqali to'lov qilmoqchisiz?\n"
        "Tanlang 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ==================== /admin ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    keyboard = []
    for crypto in CRYPTOS:
        addr = crypto_addresses[crypto]
        status = "✅" if addr else "❌"
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {crypto} adresini o'zgartir",
                callback_data=f"admin_edit_{crypto}"
            )
        ])

    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>\n\n"
        "✅ = adres kiritilgan\n"
        "❌ = adres kiritilmagan\n\n"
        "O'zgartirmoqchi bo'lgan cryptoni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# ==================== Admin edit tanlash ====================
async def admin_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await query.answer()
    crypto = query.data.replace("admin_edit_", "")
    admin_edit_target[user_id] = crypto

    current = crypto_addresses[crypto]
    current_text = f"\nHozirgi adres: <code>{current}</code>" if current else "\nHozirgi adres: <i>kiritilmagan</i>"

    await query.edit_message_text(
        f"✏️ <b>{crypto}</b> uchun yangi adresni yuboring:{current_text}\n\n"
        "Bekor qilish uchun /cancel yozing.",
        parse_mode="HTML"
    )

    return WAITING_ADDRESS


# ==================== Yangi adres qabul qilish ====================
async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        return

    crypto = admin_edit_target.get(user_id)
    if not crypto:
        return

    new_address = update.message.text.strip()
    crypto_addresses[crypto] = new_address
    del admin_edit_target[user_id]

    await update.message.reply_text(
        f"✅ <b>{crypto}</b> adresi muvaffaqiyatli yangilandi!\n\n"
        f"Yangi adres: <code>{new_address}</code>\n\n"
        "Admin panelga qaytish: /admin",
        parse_mode="HTML"
    )

    return ConversationHandler.END


# ==================== /cancel ====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in admin_edit_target:
        del admin_edit_target[user_id]
    await update.message.reply_text("❌ Bekor qilindi. /admin — panel, /start — bosh sahifa.")
    return ConversationHandler.END


# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Admin conversation
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_callback, pattern="^admin_edit_")],
        states={
            WAITING_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(crypto_callback, pattern="^crypto_"))
    app.add_handler(CallbackQueryHandler(back_start, pattern="^back_start$"))

    print("✅ Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
