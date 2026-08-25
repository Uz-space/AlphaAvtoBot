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

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8703345128:AAHBBt-GbbLaa-B_vKI0jSAPHQRQNCuktZA")
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

    def nav_btn(label, step):
        new_idx = idx + step
        if 0 <= new_idx < total:
            return InlineKeyboardButton(label, callback_data=f"nav:{uid}:{new_idx}")
        return InlineKeyboardButton("·", callback_data="noop")

    rows = [
        [
            nav_btn("⬅️", -1),
            InlineKeyboardButton(f"#{idx+1} / {total}", callback_data="noop"),
            nav_btn("➡️", +1),
        ],
        [
            nav_btn("2❯", +2),
            nav_btn("4❯", +4),
            nav_btn("6❯", +6),
            nav_btn("8❯", +8),
            nav_btn("10❯", +10),
        ],
        [InlineKeyboardButton("🔢 Jump to #", callback_data=f"jump:{uid}", style="primary")],
        [InlineKeyboardButton("📥 Download this emoji", callback_data=f"dl1:{uid}:{idx}", style="success")],
        [InlineKeyboardButton("🆔 Get this emoji ID", callback_data=f"id1:{uid}:{idx}"), InlineKeyboardButton("📋 Get all IDs", callback_data=f"idall:{uid}")],
        [InlineKeyboardButton("📦 Download all as ZIP", callback_data=f"zip:{uid}", style="danger")],
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
    sess = sessions[uid]
    sticker = sess["stickers"][sess["idx"]]
    ext = sess["ext"]

    tg_file = await ctx.bot.get_file(sticker.file_id)
    fb = bytes(await tg_file.download_as_bytearray())
    buf = io.BytesIO(fb)

    if edit_msg:
        try:
            await edit_msg.delete()
        except Exception:
            pass

    kwargs = dict(caption=make_caption(uid), parse_mode="HTML", reply_markup=make_keyboard(uid))

    if ext == ".webm":
        buf.name = "emoji.webm"
        await target.reply_video(video=buf, **kwargs)
    elif ext == ".tgs":
        buf.name = "emoji.tgs"
        await target.reply_animation(animation=buf, **kwargs)
    else:
        buf.name = "emoji.webp"
        await target.reply_document(document=buf, filename="preview.webp", **kwargs)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Emoji Pack Downloader</b>\n\n"
        "📦 <b>Download a pack:</b>\n"
        "<code>https://t.me/addemoji/PackName</code>\n"
        "<code>https://t.me/addstickers/PackName</code>\n\n"
        "✨ <b>Get Premium Emoji ID:</b>\n"
        "Forward or send any message containing premium custom emojis — "
        "I'll extract their IDs instantly.",
        parse_mode="HTML",
    )


async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = (msg.text or msg.caption or "").strip()
    uid = update.effective_user.id
    sess = sessions.get(uid)

    # --- Premium custom emoji ID extraction ---
    entities = list(msg.entities or []) + list(msg.caption_entities or [])
    custom = [e for e in entities if e.type == "custom_emoji"]
    if custom:
        full_text = msg.text or msg.caption or ""
        lines = []
        seen = set()
        for e in custom:
            if e.custom_emoji_id in seen:
                continue
            seen.add(e.custom_emoji_id)
            emoji_char = full_text[e.offset: e.offset + e.length]
            lines.append(f"{emoji_char}  <code>{e.custom_emoji_id}</code>")
        result = "\n".join(lines)
        await msg.reply_text(
            f"✨ <b>Custom Emoji ID{('s' if len(lines) > 1 else '')}:</b>\n\n{result}",
            parse_mode="HTML",
        )
        return

    # Jump to number mode
    if sess and sess.get("awaiting_jump"):
        if not text.isdigit():
            await update.message.reply_text("❌ Please send a number only.")
            return
        num = int(text)
        total = len(sess["stickers"])
        if num < 1 or num > total:
            await update.message.reply_text(f"❌ Enter a number between 1 and {total}.")
            return
        sess["awaiting_jump"] = False
        sess["idx"] = num - 1
        wait = await update.message.reply_text("⏳ Loading...")
        await send_preview(update.message, ctx, uid, edit_msg=wait)
        return

    # Pack link
    pack_name = parse_pack_name(text)
    if not pack_name:
        await update.message.reply_text(
            "❌ Invalid link.\nExample: <code>https://t.me/addemoji/PackName</code>",
            parse_mode="HTML",
        )
        return

    msg = await update.message.reply_text(f"🔍 Looking up <b>{pack_name}</b>...", parse_mode="HTML")

    try:
        sticker_set = await ctx.bot.get_sticker_set(pack_name)
    except Exception as e:
        logger.error(e)
        await msg.edit_text("❌ Pack not found. Check the link and try again.")
        return

    stickers = sticker_set.stickers
    s0 = stickers[0] if stickers else None
    ext = ".webm" if (s0 and s0.is_video) else ".tgs" if (s0 and s0.is_animated) else ".webp"

    sessions[uid] = {
        "pack_name": pack_name,
        "stickers": stickers,
        "title": sticker_set.title,
        "ext": ext,
        "idx": 0,
        "awaiting_jump": False,
    }

    await msg.edit_text("⏳ Loading preview...")
    await send_preview(update.message, ctx, uid, edit_msg=msg)


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "noop":
        return

    if data.startswith("nav:"):
        _, uid, idx = data.split(":")
        uid, idx = int(uid), int(idx)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Session expired. Please send the pack link again.")
            return
        sessions[uid]["idx"] = idx
        wait = await query.message.reply_text("⏳")
        try:
            await query.message.delete()
        except Exception:
            pass
        await send_preview(query.message, ctx, uid, edit_msg=wait)

    elif data.startswith("jump:"):
        _, uid = data.split(":")
        uid = int(uid)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Session expired. Please send the pack link again.")
            return
        total = len(sessions[uid]["stickers"])
        sessions[uid]["awaiting_jump"] = True
        await query.message.reply_text(
            f"🔢 Jump to which emoji?\n"
            f"Send a number from <b>1</b> to <b>{total}</b>:",
            parse_mode="HTML",
        )

    elif data.startswith("dl1:"):
        _, uid, idx = data.split(":")
        uid, idx = int(uid), int(idx)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Session expired.")
            return
        sess = sessions[uid]
        sticker = sess["stickers"][idx]
        single_name = f"alpha{sess['ext']}"

        wait = await query.message.reply_text("⏳ Downloading...")
        try:
            tg_file = await ctx.bot.get_file(sticker.file_id)
            fb = bytes(await tg_file.download_as_bytearray())
            buf = io.BytesIO(fb)
            buf.name = single_name
            await query.message.reply_document(
                document=buf,
                filename=single_name,
            )
            await wait.delete()
        except Exception as e:
            await wait.edit_text(f"❌ Error: {e}")

    elif data.startswith("zip:"):
        _, uid = data.split(":")
        uid = int(uid)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Session expired. Please send the pack link again.")
            return
        sess = sessions[uid]
        stickers = sess["stickers"]
        total = len(stickers)
        ext = sess["ext"]
        digits = len(str(total))

        msg = await query.message.reply_text(f"⏳ Building ZIP... 0/{total}")
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
                        await msg.edit_text(f"⏳ Building ZIP... {i}/{total}")
                    except Exception:
                        pass

        zip_buf.seek(0)
        size_mb = zip_buf.getbuffer().nbytes / 1_048_576
        if size_mb > 50:
            await msg.edit_text(f"❌ File too large ({size_mb:.1f} MB). Telegram's limit is 50 MB.")
            return

        safe = re.sub(r"[^A-Za-z0-9_-]", "_", sess["pack_name"])
        await msg.edit_text(f"📤 Sending ({size_mb:.1f} MB)...")
        await query.message.reply_document(
            document=zip_buf,
            filename=f"{safe}.zip",
            caption=(
                f"✅ <b>{sess['title']}</b>\n"
                f"📁 {total - failed}/{total} files  📦 {size_mb:.1f} MB"
            ),
            parse_mode="HTML",
        )
        await msg.delete()

    # --- Single emoji ID ---
    elif data.startswith("id1:"):
        _, uid, idx = data.split(":")
        uid, idx = int(uid), int(idx)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Session expired. Please send the pack link again.")
            return
        sess = sessions[uid]
        sticker = sess["stickers"][idx]
        emoji_id = sticker.custom_emoji_id or sticker.file_unique_id
        await query.message.reply_text(
            f"{sticker.emoji or ''}  <code>{emoji_id}</code>",
            parse_mode="HTML",
        )

    # --- All emoji IDs as txt ---
    elif data.startswith("idall:"):
        _, uid = data.split(":")
        uid = int(uid)
        if uid not in sessions:
            await query.message.reply_text("⚠️ Session expired. Please send the pack link again.")
            return
        sess = sessions[uid]
        stickers = sess["stickers"]
        total = len(stickers)

        lines = []
        for i, s in enumerate(stickers, 1):
            emoji_id = s.custom_emoji_id or s.file_unique_id
            lines.append(f"{i}. {s.emoji or ''} {emoji_id}")

        txt = sess["title"] + " — " + str(total) + " emojis\n\n" + "\n".join(lines)
        buf = io.BytesIO(txt.encode("utf-8"))
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", sess["pack_name"])
        await query.message.reply_document(
            document=buf,
            filename=safe + "_ids.txt",
            caption="📋 <b>" + sess["title"] + "</b>\n" + str(total) + " emoji IDs",
            parse_mode="HTML",
        )


def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is not set!\n   export BOT_TOKEN='your_token_here'")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
