#!/usr/bin/env python3
"""
Telegram Emoji Pack Downloader Bot
Foydalanuvchi t.me/addemoji/PackName yoki t.me/addstickers/PackName linkini yuborsa,
emoji/sticker packni tartib bilan yuklab ZIP qilib qaytaradi.
"""

import os
import io
import zipfile
import asyncio
import logging
import re
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import aiohttp

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8996187608:AAFaCrrqwqoF6HKRnwJ336hNGyn2Nwa7O_Q")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_pack_name(text: str) -> str | None:
    """Extract sticker/emoji set short name from various link formats."""
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
    # Maybe user sent just the short name directly
    if re.fullmatch(r"[A-Za-z0-9_]+", text):
        return text
    return None


async def fetch_sticker_set(bot, set_name: str):
    """Return a StickerSet object or raise."""
    return await bot.get_sticker_set(set_name)


async def download_sticker_bytes(session: aiohttp.ClientSession, file_url: str) -> bytes:
    async with session.get(file_url) as resp:
        resp.raise_for_status()
        return await resp.read()


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men Telegram emoji/sticker pack yuklovchi botman.\n\n"
        "Menga emoji yoki sticker pack linkini yuboring:\n"
        "• https://t.me/addemoji/PackNomi\n"
        "• https://t.me/addstickers/PackNomi\n\n"
        "Men packni to'g'ri tartibda ZIP qilib yuboraman! 🎉"
    )


async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Foydalanish:\n\n"
        "1️⃣  Emoji pack linkini yuboring:\n"
        "    https://t.me/addemoji/QuotexFlags\n\n"
        "2️⃣  Sticker pack linkini yuboring:\n"
        "    https://t.me/addstickers/SomeStickers\n\n"
        "3️⃣  Bot packni yuklab, ZIP arxiv qilib yuboradi.\n\n"
        "⚠️  Faqat ommaviy (public) packlar ishlaydi."
    )


async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    pack_name = parse_pack_name(text)

    if not pack_name:
        await update.message.reply_text(
            "❌ Noto'g'ri format. Iltimos, t.me/addemoji/PackNomi yoki "
            "t.me/addstickers/PackNomi ko'rinishidagi link yuboring."
        )
        return

    status_msg = await update.message.reply_text(
        f"🔍 <b>{pack_name}</b> pack yuklanmoqda...",
        parse_mode="HTML",
    )

    try:
        sticker_set = await fetch_sticker_set(ctx.bot, pack_name)
    except Exception as e:
        logger.error("get_sticker_set error: %s", e)
        await status_msg.edit_text(
            f"❌ Pack topilmadi: <code>{pack_name}</code>\n\n"
            "Pack mavjud yoki ommaviy emasmi? Linkni tekshiring.",
            parse_mode="HTML",
        )
        return

    stickers = sticker_set.stickers
    total = len(stickers)
    set_title = sticker_set.title

    await status_msg.edit_text(
        f"📦 <b>{set_title}</b>\n"
        f"Jami: {total} ta emoji/sticker\n"
        f"⏳ Yuklanmoqda...",
        parse_mode="HTML",
    )

    # Figure out extension
    is_video = stickers[0].is_video if stickers else False
    is_animated = stickers[0].is_animated if stickers else False

    if is_video:
        ext = ".webm"
    elif is_animated:
        ext = ".tgs"
    else:
        ext = ".webp"

    zip_buffer = io.BytesIO()
    digits = len(str(total))  # padding width

    async with aiohttp.ClientSession() as session:
        with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, sticker in enumerate(stickers, start=1):
                try:
                    tg_file = await ctx.bot.get_file(sticker.file_id)
                    file_bytes = await download_sticker_bytes(session, tg_file.file_path)

                    # Emoji hint for filename (sanitised)
                    emoji_char = (sticker.emoji or "").encode("ascii", "ignore").decode() or "emoji"
                    safe_emoji = re.sub(r'[\\/*?:"<>|]', "", emoji_char) or f"item{idx}"

                    filename = f"{str(idx).zfill(digits)}_{safe_emoji}{ext}"
                    zf.writestr(filename, file_bytes)

                    # Progress update every 20 items
                    if idx % 20 == 0 or idx == total:
                        await status_msg.edit_text(
                            f"📦 <b>{set_title}</b>\n"
                            f"⏳ {idx}/{total} yuklandi...",
                            parse_mode="HTML",
                        )

                except Exception as e:
                    logger.warning("Sticker %d download failed: %s", idx, e)

    zip_buffer.seek(0)
    zip_size_mb = zip_buffer.getbuffer().nbytes / 1_048_576

    if zip_size_mb > 50:
        await status_msg.edit_text(
            f"❌ ZIP fayl juda katta ({zip_size_mb:.1f} MB). "
            "Telegram 50 MB dan katta fayllarni qabul qilmaydi."
        )
        return

    await status_msg.edit_text(f"📤 ZIP yuborilmoqda ({zip_size_mb:.1f} MB)...")

    safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", pack_name)
    zip_filename = f"{safe_name}.zip"

    await update.message.reply_document(
        document=zip_buffer,
        filename=zip_filename,
        caption=(
            f"✅ <b>{set_title}</b>\n"
            f"📁 {total} ta fayl\n"
            f"📦 {zip_size_mb:.1f} MB\n\n"
            f"Fayllar tartib raqami bilan nomlangan (01_, 02_, ...)."
        ),
        parse_mode="HTML",
    )
    await status_msg.delete()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")
        print("   export BOT_TOKEN='sizning_token_bu_yerga'")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🤖 Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
