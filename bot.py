import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ===================== TOKEN & ID =====================
BOT_TOKEN = "8930805461:AAGd7e2qPGqu7lJjOLO-Pv1Ha9DkbbniyxM"
ADMIN_IDS = [8758410535]  # BU YERGA O'Z TELEGRAM ID INGIZNI YOZING (Son shaklida)
# ======================================================

logging.basicConfig(level=logging.INFO)

CRYPTO_DATA = {
    "BTC": {"name": "Bitcoin", "emoji_id": "5215346446429103945"},
    "ETH": {"name": "Ethereum", "emoji_id": "5215357136602698456"},
    "BNB": {"name": "BNB", "emoji_id": "5215553828924995476"},
    "SOL": {"name": "Solana", "emoji_id": "5215299923343353183"},
    "LTC": {"name": "Litecoin", "emoji_id": "5215555130300080404"},
    "TON": {"name": "Toncoin", "emoji_id": "5215261504860891404"},
    "TRX": {"name": "TRON", "emoji_id": "5215509887114584038"},
    "DOGE": {"name": "Dogecoin", "emoji_id": "5215634149108392152"}
}

crypto_addresses = {k: "" for k in CRYPTO_DATA.keys()}

WAITING_ADDRESS = 1
admin_edit_target = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def build_keyboard():
    """
    Foydalanuvchiga barcha kripto tugmalari Moviy (primary) rangda ko'rinadi.
    """
    keyboard = []
    for code, info in CRYPTO_DATA.items():
        keyboard.append([InlineKeyboardButton(
            text=f" {info['name']} ({code})",
            callback_data=f"crypto_{code}",
            icon_custom_emoji_id=info['emoji_id'],
            style="primary"  # 🔵 TUGMA KO'K (PRIMARY) RANGDA BO'LADI
        )])
    return InlineKeyboardMarkup(keyboard)

# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = build_keyboard()
    await update.message.reply_text(
        "💰 **Crypto To'lov Tizimi**\n\nQaysi kriptovalyuta orqali to'lov qilmoqchisiz? Tanlang 👇",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ==================== Crypto tanlash ====================
async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    address = crypto_addresses.get(crypto, "")

    # Orqaga qaytish tugmasi neytral (oddiy) ko'rinishda qoladi
    back_keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="back_start")]]

    if not address:
        await query.edit_message_text(
            f"⚠️ **{crypto}** adresi hali kiritilmagan.\n\nAdmin tez orada manzilni qo'shadi!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
        )
        return

    await query.edit_message_text(
        f"💳 **{crypto} Adresi:**\n\n`{address}`\n\nYuqoridagi manzilga to'lovingizni yuboring. ✅\n\n_(Nusxalash uchun adres ustiga bosing)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(back_keyboard),
    )

# ==================== Orqaga ====================
async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = build_keyboard()
    await query.edit_message_text(
        "💰 **Crypto To'lov Tizimi**\n\nQaysi kriptovalyuta orqali to'lov qilmoqchisiz? Tanlang 👇",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )

# ==================== /admin ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    keyboard = []
    for crypto in CRYPTO_DATA.keys():
        addr = crypto_addresses[crypto]
        
        # Manzil bor bo'lsa yashil tugma, yo'q bo'lsa qizil tugma chiqadi
        if addr:
            btn_text = f"✅ {crypto} manzilini yangilash"
            btn_style = "success"  # 🟢 TUGMA YASHIL RANGDA BO'LADI
        else:
            btn_text = f"❌ {crypto} manzilini kiritish"
            btn_style = "danger"   # 🔴 TUGMA QIZIL RANGDA BO'LADI

        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"admin_edit_{crypto}",
            style=btn_style
        )])

    await update.message.reply_text(
        "⚙️ **Admin Panel**\n\n🟩 Yashil tugmalar = Adres kiritilgan\n🟥 Qizil tugmalar = Adres kiritilmagan\n\nO'zgartirish uchun tangani tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ==================== Admin edit ====================
async def admin_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Ruxsat berilmagan!", show_alert=True)
        return

    await query.answer()
    crypto = query.data.replace("admin_edit_", "")
    admin_edit_target[user_id] = crypto

    current = crypto_addresses[crypto]
    current_text = f"\nHozirgi manzil: `{current}`" if current else "\nHozirgi manzil: kiritilmagan"

    # Bekor qilish tugmasi qizil (danger) dizaynda bo'ladi
    cancel_keyboard = [[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_action", style="danger")]]

    await query.edit_message_text(
        f"✏️ **{crypto}** uchun yangi hamyon manzilini (adres) yuboring:{current_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(cancel_keyboard)
    )
    return WAITING_ADDRESS

# ==================== Adres qabul qilish ====================
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
        f"✅ **{crypto}** hamyon manzili muvaffaqiyatli o'zgartirildi!\n\nYangi manzil: `{new_address}`\n\n/admin — Panelga qaytish\n/start — Botni ko'rish",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ==================== Cancel Callback & Command ====================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # CallbackQuery yoki oddiy xabar orqali kelganini tekshirish
    target_user = update.effective_user.id
    if target_user in admin_edit_target:
        del admin_edit_target[target_user]

    msg_text = "❌ Jarayon bekor qilindi."
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text)
    else:
        await update.message.reply_text(msg_text)
        
    return ConversationHandler.END

# ==================== MAIN START ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_edit_callback, pattern="^admin_edit_")],
        states={
            WAITING_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_address)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(cancel, pattern="^cancel_action$")
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(crypto_callback, pattern="^crypto_"))
    app.add_handler(CallbackQueryHandler(back_start, pattern="^back_start$"))

    print("🤖 Rangli tugmalarga ega bot muvaffaqiyatli ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
