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

# ==================== PREMIUM EMOJI IDLAR ====================
CRYPTO_DATA = {
    "BTC": {"name": "Bitcoin", "emoji_id": "5215346446429103945", "color": "danger"},
    "ETH": {"name": "Ethereum", "emoji_id": "5215357136602698456", "color": "primary"},
    "BNB": {"name": "BNB", "emoji_id": "5215553828924995476", "color": "success"},
    "SOL": {"name": "Solana", "emoji_id": "5215299923343353183", "color": "primary"},
    "LTC": {"name": "Litecoin", "emoji_id": "5215555130300080404", "color": "success"},
    "TON": {"name": "Toncoin", "emoji_id": "5215261504860891404", "color": "primary"},
    "TRX": {"name": "TRON", "emoji_id": "5215509887114584038", "color": "danger"},
    "DOGE": {"name": "Dogecoin", "emoji_id": "5215634149108392152", "color": "success"}
}

# ==================== MA'LUMOTLARNI FAYLGA SAQLASH ====================
DATA_FILE = "addresses.json"

def load_addresses():
    """Fayldan ma'lumotlarni yuklash"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {k: "" for k in CRYPTO_DATA.keys()}
    return {k: "" for k in CRYPTO_DATA.keys()}

def save_addresses(addresses):
    """Ma'lumotlarni faylga saqlash"""
    with open(DATA_FILE, 'w') as f:
        json.dump(addresses, f, indent=2)

# Ma'lumotlarni yuklash
crypto_addresses = load_addresses()

WAITING_ADDRESS = 1
admin_edit_target = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ==================== TUGMA YARATISH ====================
def create_premium_button(code: str, info: dict):
    text = f"{info['name']} ({code})"
    
    return InlineKeyboardButton(
        text=text,
        callback_data=f"crypto_{code}",
        style=info.get('color', 'primary'),
        icon_custom_emoji_id=info['emoji_id']
    )

# ==================== PROGRESS BAR ====================
def create_progress(percent: int):
    filled = int(percent / 100 * 20)
    empty = 20 - filled
    progress_bar = "▓" * filled + "░" * empty
    percent_text = f"{percent:>4}%"
    return f"{progress_bar}{percent_text}"

# ==================== TUGMALARNI BIRMA-BIR QO'SHISH ====================
async def show_crypto_one_by_one(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳", parse_mode="Markdown")
    
    crypto_list = list(CRYPTO_DATA.items())
    keyboard = []
    
    for i, (code, info) in enumerate(crypto_list):
        await asyncio.sleep(0.4)
        button = create_premium_button(code, info)
        keyboard.append([button])
        percent = int((i + 1) / len(crypto_list) * 100)
        progress = create_progress(percent)
        await msg.edit_text(
            f"```\n{progress}\n```",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    await asyncio.sleep(0.3)
    keyboard.append([
        InlineKeyboardButton("📊 Kurslar", callback_data="prices", style="primary"),
        InlineKeyboardButton("❓ Yordam", callback_data="help", style="primary")
    ])
    
    progress = create_progress(100)
    await msg.edit_text(
        f"```\n{progress}\n```",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_crypto_one_by_one(update, context)

# ==================== QOLGAN FUNKSIYALAR ====================
async def show_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    prices = {
        "BTC": "$67,500",
        "ETH": "$3,200", 
        "BNB": "$550",
        "SOL": "$145",
        "LTC": "$85",
        "TON": "$6.50",
        "TRX": "$0.12",
        "DOGE": "$0.15"
    }
    
    text = "📊 **Kurslar**\n\n"
    for code, price in prices.items():
        info = CRYPTO_DATA[code]
        text += f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji> <b>{code}</b>: {price}\n'
    
    keyboard = [[
        InlineKeyboardButton("🔄 Yangilash", callback_data="prices", style="primary"),
        InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")
    ]]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "❓ <b>Yordam</b>\n\n"
        "1️⃣ Kriptovalyutani tanlang\n"
        "2️⃣ Manzilni nusxalang\n"
        "3️⃣ To'lovni yuboring"
    )
    
    keyboard = [[
        InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")
    ]]
    
    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== CRYPTO CALLBACK - HTML FORMAT ====================
async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    address = crypto_addresses.get(crypto, "")
    info = CRYPTO_DATA.get(crypto, {})

    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'

    if address:
        keyboard = [[
            InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")
        ]]
        
        await query.edit_message_text(
            f"{emoji} <code>{address}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [[
            InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")
        ]]
        
        await query.edit_message_text(
            f"{emoji} Manzil yo'q",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    crypto_list = list(CRYPTO_DATA.items())
    keyboard = []
    
    for code, info in crypto_list:
        button = create_premium_button(code, info)
        keyboard.append([button])
    
    keyboard.append([
        InlineKeyboardButton("📊 Kurslar", callback_data="prices", style="primary"),
        InlineKeyboardButton("❓ Yordam", callback_data="help", style="primary")
    ])
    
    progress = create_progress(100)
    await query.edit_message_text(
        f"```\n{progress}\n```",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== ADMIN ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin emassiz!")
        return

    keyboard = []
    for crypto, info in CRYPTO_DATA.items():
        addr = crypto_addresses.get(crypto, "")
        
        if addr:
            btn_text = f"{crypto} - yangilash"
            btn_style = "success"
        else:
            btn_text = f"{crypto} - kiritish"
            btn_style = "danger"

        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"admin_edit_{crypto}",
            style=btn_style,
            icon_custom_emoji_id=info['emoji_id']
        )])

    await update.message.reply_text(
        "⚙️ <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def admin_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ Ruxsat yo'q!", show_alert=True)
        return

    await query.answer()
    crypto = query.data.replace("admin_edit_", "")
    admin_edit_target[user_id] = crypto

    current = crypto_addresses.get(crypto, "")
    info = CRYPTO_DATA.get(crypto, {})
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'
    
    current_text = f"\n{emoji} Hozirgi: <code>{current}</code>" if current else f"\n{emoji} Hozirgi: yo'q"

    cancel_keyboard = [[
        InlineKeyboardButton("❌ Bekor", callback_data="cancel_action", style="danger")
    ]]

    await query.edit_message_text(
        f"{emoji} ✏️ <b>{crypto}</b> manzilini yuboring:{current_text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(cancel_keyboard)
    )
    return WAITING_ADDRESS

async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin emassiz!")
        return ConversationHandler.END
    
    crypto = admin_edit_target.get(user_id)
    if not crypto:
        await update.message.reply_text("❌ Xatolik!")
        return ConversationHandler.END

    new_address = update.message.text.strip()
    crypto_addresses[crypto] = new_address
    
    # Ma'lumotlarni faylga saqlash
    save_addresses(crypto_addresses)
    
    info = CRYPTO_DATA.get(crypto, {})
    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'
    del admin_edit_target[user_id]
    
    await update.message.reply_text(
        f"{emoji} ✅ <b>{crypto}</b> manzili o'zgartirildi!\n\n"
        f"{emoji} <code>{new_address}</code>",
        parse_mode="HTML"
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user = update.effective_user.id
    if target_user in admin_edit_target:
        del admin_edit_target[target_user]

    msg_text = "❌ Bekor qilindi"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg_text)
    else:
        await update.message.reply_text(msg_text)
        
    return ConversationHandler.END

# ==================== MAIN ====================
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
    app.add_handler(CallbackQueryHandler(show_prices, pattern="^prices$"))
    app.add_handler(CallbackQueryHandler(show_help, pattern="^help$"))

    print("🤖 Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
