import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ===================== TOKEN =====================
BOT_TOKEN = ""
ADMIN_IDS = [8758410535]  # BU YERGA O'Z TELEGRAM ID INGIZNI YOZING
# =================================================

logging.basicConfig(level=logging.INFO)

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

WAITING_ADDRESS = 1
admin_edit_target = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def build_keyboard():
    """
    Har bir button uchun icon_custom_emoji_id ishlatiladi.
    Bot API 9.4+ va bot egasida Telegram Premium bo'lishi kerak.
    """
    keyboard = []
    for crypto in CRYPTOS:
        keyboard.append([InlineKeyboardButton(
            text=f"{crypto}",
            callback_data=f"crypto_{crypto}",
            icon_custom_emoji_id=CRYPTO_EMOJIS[crypto]
        )])
    return InlineKeyboardMarkup(keyboard)


# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = build_keyboard()
    await update.message.reply_text(
        "💰 Crypto To'lov Tizimi\n\nQaysi crypto orqali to'lov qilmoqchisiz? Tanlang 👇",
        reply_markup=keyboard,
    )


# ==================== Crypto tanlash ====================
async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    address = crypto_addresses.get(crypto, "")

    back_keyboard = [[InlineKeyboardButton(
        "Orqaga",
        callback_data="back_start",
    )]]

    if not address:
        await query.edit_message_text(
            f"{crypto} adresi hali sozlanmagan.\n\nAdmin tez orada qo'shadi!",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
        )
        return

    await query.edit_message_text(
        f"{crypto} Adresi:\n\n{address}\n\nYuqoridagi adresga to'lovingizni yuboring. ✅",
        reply_markup=InlineKeyboardMarkup(back_keyboard),
    )


# ==================== Orqaga ====================
async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = build_keyboard()
    await query.edit_message_text(
        "💰 Crypto To'lov Tizimi\n\nQaysi crypto orqali to'lov qilmoqchisiz? Tanlang 👇",
        reply_markup=keyboard,
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
        keyboard.append([InlineKeyboardButton(
            f"{status} {crypto} adresini o'zgartir",
            callback_data=f"admin_edit_{crypto}"
        )])

    await update.message.reply_text(
        "⚙️ Admin Panel\n\n✅ = adres kiritilgan\n❌ = adres kiritilmagan\n\nO'zgartirmoqchi bo'lgan cryptoni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ==================== Admin edit ====================
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
    current_text = f"\nHozirgi adres: {current}" if current else "\nHozirgi adres: kiritilmagan"

    await query.edit_message_text(
        f"✏️ {crypto} uchun yangi adresni yuboring:{current_text}\n\nBekor qilish: /cancel"
    )

    return WAITING_ADDRESS


# ==================== Adres qabul ====================
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
        f"✅ {crypto} adresi yangilandi!\n\nYangi adres: {new_address}\n\n/admin — panel\n/start — bosh sahifa"
    )

    return ConversationHandler.END


# ==================== /cancel ====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in admin_edit_target:
        del admin_edit_target[user_id]
    await update.message.reply_text("❌ Bekor qilindi.")
    return ConversationHandler.END


# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

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
