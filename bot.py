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

CRYPTO_DATA = {
    "BTC": {"name": "Bitcoin", "emoji": "₿", "color": "danger"},
    "ETH": {"name": "Ethereum", "emoji": "⟠", "color": "primary"},
    "BNB": {"name": "BNB", "emoji": "◆", "color": "success"},
    "SOL": {"name": "Solana", "emoji": "◎", "color": "primary"},
    "LTC": {"name": "Litecoin", "emoji": "Ł", "color": "success"},
    "TON": {"name": "Toncoin", "emoji": "⧫", "color": "primary"},
    "TRX": {"name": "TRON", "emoji": "◈", "color": "danger"},
    "DOGE": {"name": "Dogecoin", "emoji": "Ð", "color": "success"}
}

crypto_addresses = {k: "" for k in CRYPTO_DATA.keys()}

WAITING_ADDRESS = 1
admin_edit_target = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ==================== ASOSIY FUNKSIYA: TUGMALARNI BIRMA-BIR QO'SHISH ====================
async def show_crypto_step_by_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tugmalarni birma-bir qo'shib borish
    """
    # Birinchi xabarni yuborish
    msg = await update.message.reply_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "⏳ Kriptovalyutalar yuklanmoqda...\n"
        "▌",
        parse_mode="Markdown"
    )
    
    # Har bir kripto uchun
    crypto_list = list(CRYPTO_DATA.items())
    current_buttons = []
    
    for i, (code, info) in enumerate(crypto_list):
        # 0.5 soniya kutish (qo'shish tezligi)
        await asyncio.sleep(0.7)
        
        # Yangi tugmani qo'shish
        button = InlineKeyboardButton(
            text=f"{info['emoji']} {code}",
            callback_data=f"crypto_{code}",
            style=info.get('color', 'primary')
        )
        current_buttons.append([button])  # Har biri alohida qatorda
        
        # Keyboard yaratish
        keyboard = InlineKeyboardMarkup(current_buttons)
        
        # Holat matni
        progress = "▌" * (i + 1) + " " * (len(crypto_list) - i - 1)
        status_text = f"💰 **Kripto to'lov tizimi**\n\n"
        status_text += f"🔄 Yuklanmoqda... {i+1}/{len(crypto_list)}\n"
        status_text += f"`{progress}`\n\n"
        status_text += f"✅ {code} qo'shildi!"
        
        # Xabarni yangilash
        try:
            await msg.edit_text(
                status_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except Exception as e:
            logging.error(f"Edit error: {e}")
    
    # Yakuniy holat
    await asyncio.sleep(0.5)
    await msg.edit_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "✅ Barcha kriptovalyutalar yuklandi!\n"
        "👇 Quyidagilardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(current_buttons)
    )

# ==================== ALTERNATIV: 1-QATORGA 1 TA, KEYIN 2 TA, KEYIN 3 TA ====================
async def show_crypto_fancy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Tugmalarni chiroyli formatda: 1, 2, 3, 2 ta qilib
    """
    msg = await update.message.reply_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "⏳ Yuklanmoqda...",
        parse_mode="Markdown"
    )
    
    crypto_list = list(CRYPTO_DATA.items())
    
    # Qatorlar tartibi: [1, 2, 3, 2]
    layout = [1, 2, 3, 2]
    keyboard = []
    index = 0
    
    for row_count in layout:
        await asyncio.sleep(0.8)  # Har bir qator uchun kutish
        
        row = []
        for _ in range(row_count):
            if index < len(crypto_list):
                code, info = crypto_list[index]
                button = InlineKeyboardButton(
                    text=f"{info['emoji']} {code}",
                    callback_data=f"crypto_{code}",
                    style=info.get('color', 'primary')
                )
                row.append(button)
                index += 1
        
        if row:
            keyboard.append(row)
            
            # Xabarni yangilash
            progress = f"✅ {index}/{len(crypto_list)} yuklandi"
            await msg.edit_text(
                f"💰 **Kripto to'lov tizimi**\n\n"
                f"⏳ {progress}\n"
                f"`{'▌' * index}{' ' * (len(crypto_list) - index)}`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    # Yakuniy
    await asyncio.sleep(0.5)
    keyboard.append([
        InlineKeyboardButton("📊 Kurslar", callback_data="prices", style="primary"),
        InlineKeyboardButton("❓ Yordam", callback_data="help", style="primary")
    ])
    
    await msg.edit_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "✅ Barcha kriptovalyutalar yuklandi!\n"
        "👇 Quyidagilardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== ALTERNATIV 2: BIRMA-BIR PASTGA TUSHIB BORISH ====================
async def show_crypto_one_by_one(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Har bir kripto alohida qatorda va asta-sekin pastga tushib boradi
    """
    msg = await update.message.reply_text(
        "⏳ Kriptovalyutalar yuklanmoqda...",
        parse_mode="Markdown"
    )
    
    crypto_list = list(CRYPTO_DATA.items())
    keyboard = []
    
    for i, (code, info) in enumerate(crypto_list):
        await asyncio.sleep(0.6)
        
        # Tugma qo'shish
        button = InlineKeyboardButton(
            text=f"{info['emoji']} {code}",
            callback_data=f"crypto_{code}",
            style=info.get('color', 'primary')
        )
        keyboard.append([button])  # Har biri alohida qatorda
        
        # Xabarni yangilash
        await msg.edit_text(
            f"💰 **Kripto to'lov tizimi**\n\n"
            f"✅ {i+1}/{len(crypto_list)} yuklandi\n\n"
            f"`{'█' * (i+1)}{'░' * (len(crypto_list) - i - 1)}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Yakuniy
    await asyncio.sleep(0.5)
    await msg.edit_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "✅ Barcha kriptovalyutalar yuklandi!\n"
        "👇 Quyidagilardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 3 xil usuldan birini tanlang:
    
    # 1-usul: Oddiy birma-bir (har biri alohida qatorda)
    await show_crypto_one_by_one(update, context)
    
    # 2-usul: 1-2-3-2 formatda (chiroyli)
    # await show_crypto_fancy(update, context)
    
    # 3-usul: har biri alohida qatorda, lekin progress bilan
    # await show_crypto_step_by_step(update, context)

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
    
    text = "📊 **JORIY KURS** (taxminiy)\n\n"
    for code, price in prices.items():
        emoji = CRYPTO_DATA[code]['emoji']
        text += f"{emoji} **{code}:** {price}\n"
    
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
        "❓ **YORDAM**\n\n"
        "1️⃣ Kriptovalyutani tanlang\n"
        "2️⃣ To'lov manzilini nusxalang\n"
        "3️⃣ Manzilga to'lovni yuboring\n"
        "4️⃣ To'lov tasdiqlanishini kuting"
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
            f"⚠️ **{info['emoji']} {crypto}** adresi hali kiritilmagan.\n\n"
            f"⏳ Admin tez orada manzilni qo'shadi!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(back_keyboard),
        )
        return

    await query.edit_message_text(
        f"💳 **{info['emoji']} {crypto} ADRESI**\n\n"
        f"```\n{address}\n```\n\n"
        f"📤 Yuqoridagi manzilga to'lovni yuboring.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(back_keyboard),
    )

async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Qaytishda ham xuddi shunday effekt
    await query.edit_message_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "🔄 Qayta yuklanmoqda...",
        parse_mode="Markdown"
    )
    
    # Tezda tugmalarni qayta yaratish
    crypto_list = list(CRYPTO_DATA.items())
    keyboard = []
    
    for code, info in crypto_list:
        button = InlineKeyboardButton(
            text=f"{info['emoji']} {code}",
            callback_data=f"crypto_{code}",
            style=info.get('color', 'primary')
        )
        keyboard.append([button])
    
    keyboard.append([
        InlineKeyboardButton("📊 Kurslar", callback_data="prices", style="primary"),
        InlineKeyboardButton("❓ Yordam", callback_data="help", style="primary")
    ])
    
    await query.edit_message_text(
        "💰 **Kripto to'lov tizimi**\n\n"
        "👇 Quyidagilardan birini tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==================== ADMIN FUNKSIYALARI ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    keyboard = []
    for crypto, info in CRYPTO_DATA.items():
        addr = crypto_addresses[crypto]
        
        if addr:
            btn_text = f"✅ {info['emoji']} {crypto} - yangilash"
            btn_style = "success"
        else:
            btn_text = f"❌ {info['emoji']} {crypto} - kiritish"
            btn_style = "danger"

        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"admin_edit_{crypto}",
            style=btn_style
        )])

    await update.message.reply_text(
        "⚙️ **ADMIN PANEL**\n\n"
        "O'zgartirish uchun tangani tanlang:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

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

    cancel_keyboard = [[
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_action", style="danger")
    ]]

    await query.edit_message_text(
        f"✏️ **{crypto}** uchun yangi hamyon manzilini yuboring:{current_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(cancel_keyboard)
    )
    return WAITING_ADDRESS

async def receive_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Siz admin emassiz!")
        return ConversationHandler.END
    
    crypto = admin_edit_target.get(user_id)
    if not crypto:
        await update.message.reply_text("❌ Xatolik!")
        return ConversationHandler.END

    new_address = update.message.text.strip()
    crypto_addresses[crypto] = new_address
    del admin_edit_target[user_id]
    
    info = CRYPTO_DATA.get(crypto, {})
    
    await update.message.reply_text(
        f"✅ **{info['emoji']} {crypto}** manzili o'zgartirildi!\n\n"
        f"```\n{new_address}\n```",
        parse_mode="Markdown"
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    print("🤖 Bot ishga tushdi! Tugmalar birma-bir qo'shiladi...")
    app.run_polling()

if __name__ == "__main__":
    main()
