import logging
import asyncio
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

crypto_addresses = {k: "" for k in CRYPTO_DATA.keys()}

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

# ==================== PROGRESS BAR (DOIM BIR XIL UZUNLIKDA) ====================
def create_progress(percent: int):
    """Progress bar doim 24 belgi - 20 belgi progress + 4 belgi foiz"""
    filled = int(percent / 100 * 20)
    empty = 20 - filled
    progress_bar = "▓" * filled + "░" * empty
    
    # Foizni doim 4 ta belgi qilib formatlash (chapga tekislab)
    # "   0%", "  10%", "  50%", " 100%"
    percent_text = f"{percent:>4}%"
    
    # Progress bar + foiz (doim 24 belgi)
    return f"{progress_bar}{percent_text}"

# ==================== TUGMALARNI BIRMA-BIR QO'SHISH ====================
async def show_crypto_one_by_one(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "⏳",
        parse_mode="Markdown"
    )
    
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

# ==================== 1-2-3-2 FORMAT ====================
async def show_crypto_fancy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "⏳",
        parse_mode="Markdown"
    )
    
    crypto_list = list(CRYPTO_DATA.items())
    layout = [1, 2, 3, 2]
    keyboard = []
    index = 0
    
    for row_count in layout:
        await asyncio.sleep(0.5)
        
        row = []
        for _ in range(row_count):
            if index < len(crypto_list):
                code, info = crypto_list[index]
                button = create_premium_button(code, info)
                row.append(button)
                index += 1
        
        if row:
            keyboard.append(row)
            
            percent = int(index / len(crypto_list) * 100)
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

# ==================== 2 TADAN ====================
async def show_crypto_two_by_two(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "⏳",
        parse_mode="Markdown"
    )
    
    crypto_list = list(CRYPTO_DATA.items())
    keyboard = []
    row = []
    
    for i, (code, info) in enumerate(crypto_list):
        await asyncio.sleep(0.3)
        
        button = create_premium_button(code, info)
        row.append(button)
        
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
            
            percent = int((i + 1) / len(crypto_list) * 100)
            progress = create_progress(percent)
            
            await msg.edit_text(
                f"```\n{progress}\n```",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    if row:
        keyboard.append(row)
    
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
        text += f"[{code}](tg://emoji?id={info['emoji_id']}) **{code}:** {price}\n"
    
    keyboard = [[
        InlineKeyboardButton("🔄 Yangilash", callback_data="prices", style="primary"),
        InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")
    ]]
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = (
        "❓ **Yordam**\n\n"
        "1️⃣ Kriptovalyutani tanlang\n"
        "2️⃣ Manzilni nusxalang\n"
        "3️⃣ To'lovni yuboring"
    )
    
    keyboard = [[
        InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary")
    ]]
    
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    address = crypto_addresses.get(crypto, "")
    info = CRYPTO_DATA.get(crypto, {})

    back_keyboard = [[
        InlineKeyboardButton("🏠 Bosh sahifa", callback_data="back_start", style="primary"),
        InlineKeyboardButton("📊 Kurslar", callback_data="prices", style="primary")
    ]]

    if not address:
        await query.edit_message_text(
            f"⚠️ [{crypto}](tg://emoji?id={info['emoji_id']}) **{crypto}** manzili yo'q\n⏳ Admin qo'shadi",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
        )
        return

    await query.edit_message_text(
        f"💳 [{crypto}](tg://emoji?id={info['emoji_id']}) **{crypto}**\n\n"
        f"```\n{address}\n```\n\n"
        f"📤 Yuqoridagi manzilga to'lov yuboring",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(back_keyboard),
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
        addr = crypto_addresses[crypto]
        
        if addr:
            btn_text = f"✅ {crypto} - yangilash"
            btn_style = "success"
        else:
            btn_text = f"❌ {crypto} - kiritish"
            btn_style = "danger"

        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"admin_edit_{crypto}",
            style=btn_style,
            icon_custom_emoji_id=info['emoji_id']
        )])

    await update.message.reply_text(
        "⚙️ **Admin Panel**",
        parse_mode="Markdown",
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

    current = crypto_addresses[crypto]
    current_text = f"\nHozirgi: `{current}`" if current else "\nHozirgi: yo'q"

    cancel_keyboard = [[
        InlineKeyboardButton("❌ Bekor", callback_data="cancel_action", style="danger")
    ]]

    await query.edit_message_text(
        f"✏️ **{crypto}** manzilini yuboring:{current_text}",
        parse_mode="Markdown",
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
    del admin_edit_target[user_id]
    
    await update.message.reply_text(
        f"✅ **{crypto}** manzili o'zgartirildi!\n\n"
        f"```\n{new_address}\n```",
        parse_mode="Markdown"
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
