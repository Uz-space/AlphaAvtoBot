#!/usr/bin/env python3
import os
import io
import zipfile
import logging
import re
import unicodedata

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8996187608:AAFaCrrqwqoF6HKRnwJ336hNGyn2Nwa7O_Q")


def parse_pack_name(text: str):
    text = text.strip()
    patterns = [
        r"t\.me/addemoji/([A-Za-z0-9_]+)",
        r"t\.me/addstickers/([A-Za-z0-9_]+)",
        r"telegram\.me/addemoji/([A-Za-z0-9_]+)",
        r"telegram\.me/addstickers/([A-Za-z0-9_]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_]+", text):
        return text
    return None


def emoji_to_name(emoji_char: str) -> str:
    if not emoji_char:
        return "emoji"
    try:
        name = unicodedata.name(emoji_char[0], "").lower()
        name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
        return name[:30] if name else "emoji"
    except Exception:
        return "_".join(f"u{ord(c):04x}" for c in emoji_char[:2])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📖 Qo'llanma", callback_data="help")]]
    await update.message.reply_text(
        "👋 Salom!\n\n"
        "Men Telegram emoji yoki sticker pack yuklovchi botman.\n\n"
        "📌 Ishlatish:\n"
        "Pack linkini shu formatda yuboring:\n"
        "<code>https://t.me/addemoji/PackNomi</code>\n"
        "<code>https://t.me/addstickers/PackNomi</code>\n\n"
        "Bot packni to'liq tartibda yuklab, ZIP qilib yuboradi ✅",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📖 <b>Qo'llanma</b>\n\n"
        "1. Emoji pack linkini yuboring:\n"
        "   <code>https://t.me/addemoji/QuotexFlags</code>\n\n"
        "2. Sticker pack linkini yuboring:\n"
        "   <code>https://t.me/addstickers/NomiBu</code>\n\n"
        "3. Bot avtomatik yuklab ZIP yuboradi.\n\n"
        "⚠️ Faqat ochiq (public) packlar ishlaydi.",
        parse_mode="HTML",
    )


async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    pack_name = parse_pack_name(text)

    if not pack_name:
        await update.message.reply_text(
            "❌ Link noto'g'ri.\n\n"
            "To'g'ri format:\n"
            "<code>https://t.me/addemoji/PackNomi</code>",
            parse_mode="HTML",
        )
        return

    status_msg = await update.message.reply_text(
        f"🔍 <b>{pack_name}</b> qidirilmoqda...",
        parse_mode="HTML",
    )

    # Pack ma'lumotlarini olish
    try:
        sticker_set = await ctx.bot.get_sticker_set(pack_name)
    except Exception as e:
        logger.error("get_sticker_set: %s", e)
        await status_msg.edit_text(
            f"❌ <b>{pack_name}</b> topilmadi.\n\n"
            "Pack mavjud emas yoki yopiq bo'lishi mumkin.",
            parse_mode="HTML",
        )
        return

    stickers = sticker_set.stickers
    total = len(stickers)
    title = sticker_set.title

    # Fayl formatini aniqlash
    s0 = stickers[0] if stickers else None
    if s0 and s0.is_video:
        ext = ".webm"
    elif s0 and s0.is_animated:
        ext = ".tgs"
    else:
        ext = ".webp"

    await status_msg.edit_text(
        f"📦 <b>{title}</b>\n"
        f"Jami: {total} ta fayl\n"
        f"⏳ Yuklanmoqda...",
        parse_mode="HTML",
    )

    digits = len(str(total))
    zip_buffer = io.BytesIO()
    failed = 0

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_STORED) as zf:
        for idx, sticker in enumerate(stickers, start=1):
            try:
                # python-telegram-bot o'zi yuklab beradi — URL kerak emas
                tg_file = await ctx.bot.get_file(sticker.file_id)
                file_bytes = await tg_file.download_as_bytearray()

                emoji_name = emoji_to_name(sticker.emoji or "")
                filename = f"{str(idx).zfill(digits)}_{emoji_name}{ext}"
                zf.writestr(filename, bytes(file_bytes))

            except Exception as e:
                logger.warning("Sticker %d xato: %s", idx, e)
                failed += 1

            # Har 15 tada progress yangilash
            if idx % 15 == 0 or idx == total:
                try:
                    await status_msg.edit_text(
                        f"📦 <b>{title}</b>\n"
                        f"⏳ {idx}/{total} yuklandi...",
                        parse_mode="HTML",
                    )
                except Exception:
                    pass

    zip_buffer.seek(0)
    size_mb = zip_buffer.getbuffer().nbytes / 1_048_576

    if size_mb > 50:
        await status_msg.edit_text(
            f"❌ Fayl juda katta ({size_mb:.1f} MB).\n"
            "Telegram 50 MB dan katta fayllarni qabul qilmaydi."
        )
        return

    await status_msg.edit_text(f"📤 ZIP yuborilmoqda ({size_mb:.1f} MB)...")

    safe = re.sub(r"[^A-Za-z0-9_-]", "_", pack_name)
    caption = (
        f"✅ <b>{title}</b>\n"
        f"📁 {total - failed}/{total} fayl\n"
        f"📦 {size_mb:.1f} MB"
    )
    if failed:
        caption += f"\n⚠️ {failed} ta fayl yuklanmadi"

    await update.message.reply_document(
        document=zip_buffer,
        filename=f"{safe}.zip",
        caption=caption,
        parse_mode="HTML",
    )
    await status_msg.delete()


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN o'rnatilmagan!")
        print("   export BOT_TOKEN='tokeningiz'")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(help_button, pattern="^help$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🤖 Bot ishga tushdi! Ctrl+C — to'xtatish")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
