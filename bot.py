#!/usr/bin/env python3
"""
Emoji Pack Bot — preview + navigatsiya + yuklab olish BITTA xabarda
Sticker WebP ni rasm sifatida, WebM/TGS ni animatsiya sifatida yuboradi
shu bilan caption va tugmalar ham o'sha xabardayoq bo'ladi.
"""

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

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8996187608:AAFaCrrqwqoF6HKRnwJ336hNGyn2Nwa7O_Q")

# user_id -> {stickers, title, ext, pack_name, idx}
sessions: dict = {}


def parse_pack_name(text: str):
    for pat in [
        r"t\.me/addemoji/([A-Za-z0-9_]+)",
        r"t\.me/addstickers/([A-Za-z0-9_]+)",
        r"telegram\.me/addemoji/([A-Za-z0-9_]+)",
        r"telegram\.me/addstickers/([A-Za-z0-9_]+)",
    ]:
        m = re.search(pat, text.strip())
        if m:
            return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_]+", text.strip()):
        return text.strip()
    return None


def emoji_to_name(ch: str) -> str:
    if not ch:
        return "emoji"
    try:
        name = unicodedata.name(ch[0], "").lower()
        return re.sub(r"[^a-z0-9]+", "_", name).strip("_")[:25] or "emoji"
    except Exception:
        return "_".join(f"u{ord(c):04x}" for c in ch[:2])


def make_keyboard(uid: int) -> InlineKeyboardMarkup:
    sess = sessions[uid]
    idx = sess["idx"]
    total = len(sess["stickers"])
    rows = [
        [
            InlineKeyboardButton("⬅️", callback_data=f"nav:{uid}:{idx-1}") if idx > 0 else InlineKeyboardButton("·", callback_data="noop"),
            InlineKeyboardButton(f"{idx+1} / {total}", callback_data="noop"),
            InlineKeyboardButton("➡️", callback_data=f"nav:{uid}:{idx+1}") if idx < total - 1 else InlineKeyboardButton("·", callback_data="noop"),
        ],
        [InlineKeyboardButton("📥 Shu emojiyi yuklab olish", callback_data=f"dl1:{uid}:{idx}")],
        [InlineKeyboardButton("📦 Hammasini ZIP qilib yuborish", callback_data=f"zip:{uid}")],
    ]
    return InlineKeyboardMarkup(rows)


def make_caption(uid: int) -> str:
    sess = sessions[uid]
    idx = sess["idx"]
    total = len(sess["stickers"])
    sticker = sess["stickers"][idx]
    digits = len(str(total))
    name = emoji_to_name(sticker.emoji or "")
    filename = f"{str(idx+1).zfill(digits)}_{name}{sess['ext']}"
    return (
        f"📦 <b>{sess['title']}</b>\n"
        f"#{idx+1} / {total}  {sticker.emoji or ''}\n"
        f"<code>{filename}</code>"
    )


async def send_preview(target, ctx, uid: int, edit_msg=None):
    """
    Stickerni file_id orqali yuklab bytes oladi,
    keyin bitta xabar sifatida (rasm/animatsiya) caption + keyboard bilan yuboradi.
    edit_msg berilsa o'sha xabarni o'chiradi.
    """
    sess = sessions[uid]
    idx = sess["idx"]
    sticker = sess["stickers"][idx]
    keyboard = make_keyboard(uid)
    caption = make_caption(uid)
    ext = sess["ext"]

    tg_file = await ctx.bot.get_file(sticker.file_id)
    fb = bytes(await tg_file.download_as_bytearray())

    if edit_msg:
        try:
            await edit_msg.delete()
        except Exception:
            pass

    buf = io.BytesIO(fb)

    if ext == ".webp":
        # Rasmga convert qilmasdan to'g'ridan document sifatida yuboramiz
        # lekin photo sifatida yuborib, caption + keyboard birlashadi
        buf.name = "emoji.webp"
        await target.reply_document(
            document=buf,
            filename=f"preview.webp",
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    elif ext == ".webm":
        buf.name = "emoji.webm"
        await target.reply_video(
            video=buf,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    elif ext == ".tgs":
        buf.name = "emoji.tgs"
        await target.reply_animation(
            animation=buf,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    else:
        buf.name = f"emoji{ext}"
        await target.reply_document(
            document=buf,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard,
        )


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom!\n\n"
        "Pack linkini yuboring:\n"
        "<code>https://t.me/addemoji/PackNomi</code>\n"
        "<code>https://t.me/addstickers/PackNomi</code>",
        parse_mode="HTML",
    )


async def handle_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    pack_name = parse_pack_name(update.message.text or "")
    if not pack_name:
        await update.message.reply_text(
            "❌ Noto'g'ri link.\nNamuna: <code>https://t.me/addemoji/PackNomi</code>",
            parse_mode="HTML",
        )
        return

    msg = await update.message.reply_text(f"🔍 <b>{pack_name}</b> qidirilmoqda...", parse_mode="HTML")

    try:
        sticker_set = await ctx.bot.get_sticker_set(pack_name)
    except Exception as e:
        logger.error(e)
        await msg.edit_text("❌ Pack topilmadi. Linkni tekshiring.")
        return

    stickers = sticker_set.stickers
    s0 = stickers[0] if stickers else None
    ext = ".webm" if (s0 and s0.is_video) else ".tgs" if (s0 and s0.is_animated) else ".webp"

    uid = update.effective_user.id
    sessions[uid] = {
        "pack_name": pack_name,
        "stickers": stickers,
        "title": sticker_set.title,
        "ext": ext,
        "idx": 0,
    }

    await msg.edit_text(f"⏳ Preview yuklanmoqda...", parse_mode="HTML")
    await send_preview(update.message, ctx, uid, edit_msg=msg)


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "noop":
        return

    # --- Navigatsiya ---
    if data.startswith("nav:"):
        _, uid, idx = data.split(":")
        uid, idx = int(uid), int(idx)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Sessiya tugagan. Pack linkini qayta yuboring.")
            return

        sessions[uid]["idx"] = idx

        wait = await query.message.reply_text("⏳")
        # Eski xabarni o'chirib, yangi bitta xabar yuboramiz
        try:
            await query.message.delete()
        except Exception:
            pass
        await send_preview(query.message, ctx, uid, edit_msg=wait)

    # --- Bitta emoji yuklab berish ---
    elif data.startswith("dl1:"):
        _, uid, idx = data.split(":")
        uid, idx = int(uid), int(idx)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Sessiya tugagan.")
            return

        sess = sessions[uid]
        sticker = sess["stickers"][idx]
        digits = len(str(len(sess["stickers"])))
        name = emoji_to_name(sticker.emoji or "")
        filename = f"{str(idx+1).zfill(digits)}_{name}{sess['ext']}"

        wait = await query.message.reply_text("⏳ Yuklanmoqda...")
        try:
            tg_file = await ctx.bot.get_file(sticker.file_id)
            fb = bytes(await tg_file.download_as_bytearray())
            buf = io.BytesIO(fb)
            await query.message.reply_document(
                document=buf,
                filename=filename,
                caption=f"✅ <code>{filename}</code>",
                parse_mode="HTML",
            )
            await wait.delete()
        except Exception as e:
            await wait.edit_text(f"❌ Xato: {e}")

    # --- Hammasini ZIP ---
    elif data.startswith("zip:"):
        _, uid = data.split(":")
        uid = int(uid)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Sessiya tugagan. Pack linkini qayta yuboring.")
            return

        sess = sessions[uid]
        stickers = sess["stickers"]
        total = len(stickers)
        ext = sess["ext"]
        digits = len(str(total))

        msg = await query.message.reply_text(f"⏳ ZIP tayyorlanmoqda... 0/{total}")

        zip_buf = io.BytesIO()
        failed = 0
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_STORED) as zf:
            for i, s in enumerate(stickers, 1):
                try:
                    tg_file = await ctx.bot.get_file(s.file_id)
                    fb = bytes(await tg_file.download_as_bytearray())
                    fname = f"{str(i).zfill(digits)}_{emoji_to_name(s.emoji or '')}{ext}"
                    zf.writestr(fname, fb)
                except Exception as e:
                    logger.warning("Sticker %d: %s", i, e)
                    failed += 1
                if i % 25 == 0 or i == total:
                    try:
                        await msg.edit_text(f"⏳ ZIP tayyorlanmoqda... {i}/{total}")
                    except Exception:
                        pass

        zip_buf.seek(0)
        size_mb = zip_buf.getbuffer().nbytes / 1_048_576

        if size_mb > 50:
            await msg.edit_text(f"❌ Fayl juda katta ({size_mb:.1f} MB). Telegram 50 MB limitidan oshdi.")
            return

        safe = re.sub(r"[^A-Za-z0-9_-]", "_", sess["pack_name"])
        await msg.edit_text(f"📤 Yuborilmoqda ({size_mb:.1f} MB)...")
        await query.message.reply_document(
            document=zip_buf,
            filename=f"{safe}.zip",
            caption=f"✅ <b>{sess['title']}</b>\n📁 {total-failed}/{total} fayl  📦 {size_mb:.1f} MB",
            parse_mode="HTML",
        )
        await msg.delete()


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN o'rnatilmagan!\n   export BOT_TOKEN='tokeningiz'")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("🤖 Bot ishga tushdi! Ctrl+C — to'xtatish")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
