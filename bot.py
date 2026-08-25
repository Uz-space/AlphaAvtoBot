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

# ==================== TILLAR ====================
LANGUAGES = {
    "en": {"name": "English", "flag": "🇬🇧"},
    "ru": {"name": "Русский", "flag": "🇷🇺"},
    "uz": {"name": "O'zbekcha", "flag": "🇺🇿"}
}

user_language = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ==================== TILGA MOS MATNLAR ====================
def get_texts(lang_code: str):
    if lang_code == "en":
        return {
            "select_crypto": "Select a cryptocurrency:",
            "no_address": "No address",
            "back_home": "🏠 Home",
            "address_updated": "address updated!",
            "copy_address": "📋 Copy address"
        }
    elif lang_code == "ru":
        return {
            "select_crypto": "Выберите криптовалюту:",
            "no_address": "Адрес отсутствует",
            "back_home": "🏠 Главная",
            "address_updated": "адрес обновлен!",
            "copy_address": "📋 Копировать адрес"
        }
    else:  # uz
        return {
            "select_crypto": "Kriptovalyutani tanlang:",
            "no_address": "Manzil yo'q",
            "back_home": "🏠 Bosh sahifa",
            "address_updated": "manzili o'zgartirildi!",
            "copy_address": "📋 Nusxalash"
        }

# ==================== TUGMA YARATISH ====================
def create_premium_button(code: str, info: dict):
    text = f"{info['name']} ({code})"
    
    return InlineKeyboardButton(
        text=text,
        callback_data=f"crypto_{code}",
        style=info.get('color', 'primary'),
        icon_custom_emoji_id=info['emoji_id']
    )

# ==================== TIL TANLASH ====================
async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en", style="primary")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru", style="primary")],
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz", style="primary")]
    ]
    
    # /start dan kelgan bo'lsa
    if update.message:
        await update.message.reply_text(
            "🌍 Choose language:\n"
            "🌍 Выберите язык:\n"
            "🌍 Tilni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    # Callback query dan kelgan bo'lsa
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            "🌍 Choose language:\n"
            "🌍 Выберите язык:\n"
            "🌍 Tilni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==================== TIL TANLANGANDA ====================
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    lang_code = query.data.replace("lang_", "")
    user_id = query.from_user.id
    
    user_language[user_id] = lang_code
    
    # Tanlangan tilni ko'rsatish
    lang_info = LANGUAGES[lang_code]
    texts = get_texts(lang_code)
    
    # Tilga mos xabar
    if lang_code == "en":
        msg = f"{lang_info['flag']} {lang_info['name']} selected! ✅\n\n{texts['select_crypto']}"
    elif lang_code == "ru":
        msg = f"{lang_info['flag']} {lang_info['name']} выбран! ✅\n\n{texts['select_crypto']}"
    else:
        msg = f"{lang_info['flag']} {lang_info['name']} tanlandi! ✅\n\n{texts['select_crypto']}"
    
    await query.edit_message_text(
        msg,
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

# ==================== ASOSIY KEYBOARD ====================
def get_main_keyboard():
    keyboard = []
    
    for code, info in CRYPTO_DATA.items():
        button = create_premium_button(code, info)
        keyboard.append([button])
    
    return keyboard

# ==================== /start ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await language_selection(update, context)

# ==================== CRYPTO CALLBACK - HTML FORMAT ====================
async def crypto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crypto = query.data.replace("crypto_", "")
    address = crypto_addresses.get(crypto, "")
    info = CRYPTO_DATA.get(crypto, {})
    
    user_id = query.from_user.id
    lang_code = user_language.get(user_id, "uz")
    texts = get_texts(lang_code)

    emoji = f'<tg-emoji emoji-id="{info["emoji_id"]}">⬛</tg-emoji>'

    if address:
        keyboard = [[
            InlineKeyboardButton(texts['back_home'], callback_data="back_start", style="primary")
        ]]
        
        await query.edit_message_text(
            f"{emoji} <code>{address}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        keyboard = [[
            InlineKeyboardButton(texts['back_home'], callback_data="back_start", style="primary")
        ]]
        
        await query.edit_message_text(
            f"{emoji} {texts['no_address']}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def back_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    lang_code = user_language.get(user_id, "uz")
    texts = get_texts(lang_code)
    
    await query.edit_message_text(
        texts['select_crypto'],
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
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
    
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(crypto_callback, pattern="^crypto_"))
    app.add_handler(CallbackQueryHandler(back_start, pattern="^back_start$"))

    print("🤖 Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
