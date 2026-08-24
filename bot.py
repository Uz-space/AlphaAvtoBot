import asyncio
import os
import logging
import sqlite3
import threading
import shutil
import re
from datetime import datetime, timedelta
from io import BytesIO

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetShortName
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
)
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import yt_dlp

# =====================================================================
# SOZLAMALAR — .env yoki to'g'ridan-to'g'ri
# =====================================================================
API_ID   = int(os.getenv("API_ID", "39156803"))
API_HASH = os.getenv("API_HASH", "614ff1005dd51d4067dbf02915cf7b47")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8809744706:AAFQHnhvwG7MaT6eK-KDUYIMrBroifFrJzI")
# =====================================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Papkalar ──────────────────────────────────────────────────────────
BASE_DIR           = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR       = os.path.join(BASE_DIR, "sessions")
SAVED_MEDIA_DIR    = os.path.join(BASE_DIR, "saved_media")
TEMP_DIR           = os.path.join(BASE_DIR, "temp")
VIDEOS_DIR         = os.path.join(BASE_DIR, "downloaded_videos")
STICKERS_DIR       = os.path.join(BASE_DIR, "stickers")
for _d in [SESSIONS_DIR, SAVED_MEDIA_DIR, TEMP_DIR, VIDEOS_DIR, STICKERS_DIR]:
    os.makedirs(_d, exist_ok=True)

# ── SQLite ────────────────────────────────────────────────────────────
DB_PATH  = os.path.join(BASE_DIR, "panel.sqlite3")
db_lock  = threading.RLock()

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id      INTEGER PRIMARY KEY,
                phone        TEXT,
                session_str  TEXT,
                created_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS bandman (
                chat_id  INTEGER PRIMARY KEY,
                enabled  INTEGER DEFAULT 1,
                message  TEXT,
                cooldown INTEGER DEFAULT 300
            );
            CREATE TABLE IF NOT EXISTS broadcast_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id    INTEGER,
                text       TEXT,
                success    INTEGER DEFAULT 0,
                fail       INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sticker_packs (
                chat_id    INTEGER PRIMARY KEY,
                pack_name  TEXT,
                pack_title TEXT
            );
            CREATE TABLE IF NOT EXISTS edit_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id      INTEGER,
                msg_chat_id  INTEGER,
                msg_id       INTEGER,
                original     TEXT,
                created_at   TEXT
            );
            CREATE TABLE IF NOT EXISTS last_bandman (
                user_id    INTEGER PRIMARY KEY,
                owner_id   INTEGER,
                last_at    TEXT
            );
        """)
        conn.commit()

init_db()

# ── Foydalanuvchi holatlari (RAM) ─────────────────────────────────────
user_states: dict = {}

# ── Faol Telethon clientlar ───────────────────────────────────────────
active_clients: dict[int, TelegramClient] = {}
client_lock = asyncio.Lock()

# =====================================================================
# YORDAMCHI FUNKSIYALAR
# =====================================================================

def get_session_path(chat_id: int) -> str:
    return os.path.join(SESSIONS_DIR, f"user_{chat_id}")

def get_user(chat_id: int):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE chat_id=?", (chat_id,)
        ).fetchone()

def save_user(chat_id: int, phone: str, session_str: str):
    with db_lock:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO users(chat_id, phone, session_str, created_at)
                   VALUES(?,?,?,?)
                   ON CONFLICT(chat_id) DO UPDATE SET
                       phone=excluded.phone,
                       session_str=excluded.session_str""",
                (chat_id, phone, session_str, datetime.now().isoformat()),
            )
            conn.commit()

def get_file_size(path: str) -> str:
    try:
        s = os.path.getsize(path)
        if s < 1024:        return f"{s} B"
        elif s < 1048576:   return f"{s/1024:.1f} KB"
        else:               return f"{s/1048576:.1f} MB"
    except OSError:
        return "?"

def safe_text(t, limit=900):
    t = str(t or "")
    t = t.replace("`", "'")
    return t[:limit] + ("…" if len(t) > limit else "")

# =====================================================================
# INLINE KLAVIATURA (kod kiritish uchun)
# =====================================================================
def code_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1", callback_data="c_1"),
         InlineKeyboardButton("2", callback_data="c_2"),
         InlineKeyboardButton("3", callback_data="c_3")],
        [InlineKeyboardButton("4", callback_data="c_4"),
         InlineKeyboardButton("5", callback_data="c_5"),
         InlineKeyboardButton("6", callback_data="c_6")],
        [InlineKeyboardButton("7", callback_data="c_7"),
         InlineKeyboardButton("8", callback_data="c_8"),
         InlineKeyboardButton("9", callback_data="c_9")],
        [InlineKeyboardButton("❌ O'chir", callback_data="c_clear"),
         InlineKeyboardButton("0",         callback_data="c_0"),
         InlineKeyboardButton("✅ Tasdiqlash", callback_data="c_submit")],
    ])

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Broadcast", callback_data="m_broadcast"),
         InlineKeyboardButton("📵 Bandman",   callback_data="m_bandman")],
        [InlineKeyboardButton("💾 Media saqlash", callback_data="m_save"),
         InlineKeyboardButton("📥 Video yuklash", callback_data="m_down")],
        [InlineKeyboardButton("🎨 Sticker",   callback_data="m_sticker"),
         InlineKeyboardButton("✏️ Edit track", callback_data="m_editinfo")],
        [InlineKeyboardButton("📊 Statistika", callback_data="m_stats"),
         InlineKeyboardButton("🚪 Chiqish",   callback_data="m_logout")],
    ])

# =====================================================================
# /start — LOGIN OQIMI
# =====================================================================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user    = get_user(chat_id)

    if user and user["session_str"]:
        await update.message.reply_text(
            "✅ Siz allaqachon tizimdasiz!\n\n"
            "Quyidagi menyudan foydalaning:",
            reply_markup=main_menu(),
        )
        return

    user_states[chat_id] = {"step": "PHONE"}
    await update.message.reply_text(
        "👋 Xush kelibsiz!\n\n"
        "📱 Telegram raqamingizni yuboring:\n"
        "Misol: `+998901234567`",
        parse_mode="Markdown",
    )

# =====================================================================
# /menu
# =====================================================================
async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user    = get_user(chat_id)
    if not user or not user["session_str"]:
        await update.message.reply_text("❌ Avval /start orqali kiring.")
        return
    await update.message.reply_text("📋 Asosiy menyu:", reply_markup=main_menu())

# =====================================================================
# XABAR HANDLER — login oqimi + buyruqlar
# =====================================================================
async def msg_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text    = (update.message.text or "").strip()
    state   = user_states.get(chat_id, {})
    step    = state.get("step", "")

    # ── 1. Telefon raqami ─────────────────────────────────────────────
    if step == "PHONE":
        if not re.match(r"^\+\d{7,15}$", text):
            await update.message.reply_text(
                "❌ Noto'g'ri format. Misol: `+998901234567`",
                parse_mode="Markdown",
            )
            return

        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        try:
            sent = await client.send_code_request(text)
            user_states[chat_id] = {
                "step":            "CODE",
                "phone":           text,
                "client":          client,
                "phone_code_hash": sent.phone_code_hash,
                "entered_code":    "",
            }
            await update.message.reply_text(
                "📩 Telegram kodingiz yuborildi!\n\n"
                "Quyidagi tugmalar orqali kodni kiriting:",
                reply_markup=code_keyboard(),
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Xatolik: {safe_text(e, 200)}")
            await client.disconnect()
            user_states.pop(chat_id, None)

    # ── 2. 2FA parol ──────────────────────────────────────────────────
    elif step == "2FA":
        client = state["client"]
        try:
            await client.sign_in(password=text)
            session_str = client.session.save()
            save_user(chat_id, state["phone"], session_str)
            await client.disconnect()
            user_states.pop(chat_id, None)
            await update.message.reply_text(
                "✅ 2FA orqali muvaffaqiyatli kirdingiz!\n\n"
                "Menyudan foydalaning:",
                reply_markup=main_menu(),
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Parol xato: {safe_text(e, 200)}")

    # ── 3. Broadcast matni ────────────────────────────────────────────
    elif step == "BROADCAST_TEXT":
        user_states[chat_id]["broadcast_text"] = text
        user_states[chat_id]["step"] = "BROADCAST_CONFIRM"
        await update.message.reply_text(
            f"📝 Xabar:\n\n{text}\n\n"
            "Barcha guruhlarga yuborilsinmi?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Ha, yuvor", callback_data="bc_yes"),
                 InlineKeyboardButton("❌ Bekor", callback_data="bc_no")],
            ]),
        )

    # ── 4. Bandman matni ──────────────────────────────────────────────
    elif step == "BANDMAN_TEXT":
        with db_lock:
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO bandman(chat_id, enabled, message)
                       VALUES(?,1,?)
                       ON CONFLICT(chat_id) DO UPDATE SET enabled=1, message=excluded.message""",
                    (chat_id, text),
                )
                conn.commit()
        user_states.pop(chat_id, None)
        await update.message.reply_text(
            "✅ Bandman yoqildi va matn saqlandi!\n"
            f"📝 Matn: {text[:100]}",
        )

    # ── 5. Video URL ──────────────────────────────────────────────────
    elif step == "VIDEO_URL":
        user_states.pop(chat_id, None)
        await _download_and_send(update, ctx, text)

    else:
        user = get_user(chat_id)
        if not user or not user["session_str"]:
            await update.message.reply_text(
                "❌ /start orqali kiring yoki /menu yozing."
            )

# =====================================================================
# CALLBACK HANDLER
# =====================================================================
async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    chat_id = update.effective_chat.id
    data    = query.data
    state   = user_states.get(chat_id, {})

    await query.answer()

    # ── Kod kiritish tugmalari ─────────────────────────────────────────
    if data.startswith("c_"):
        if state.get("step") != "CODE":
            await query.answer("⚠️ /start bosing", show_alert=True)
            return

        key = data[2:]
        if key == "clear":
            state["entered_code"] = ""
            await query.edit_message_text(
                "📩 Kod:\n┌────────────────────┐\n│ Kiritildi:         │\n└────────────────────┘",
                reply_markup=code_keyboard(),
            )
            return

        if key == "submit":
            code   = state.get("entered_code", "")
            client = state["client"]
            if len(code) < 4:
                await query.answer("❌ Kod kamida 4 ta raqam!", show_alert=True)
                return
            try:
                await client.sign_in(
                    phone=state["phone"],
                    code=code,
                    phone_code_hash=state["phone_code_hash"],
                )
                session_str = client.session.save()
                save_user(chat_id, state["phone"], session_str)
                await client.disconnect()
                user_states.pop(chat_id, None)
                await query.edit_message_text(
                    "✅ Muvaffaqiyatli kirdingiz!\n\nMenyudan foydalaning:",
                    reply_markup=main_menu(),
                )
            except SessionPasswordNeededError:
                state["step"] = "2FA"
                await query.edit_message_text(
                    "🔒 2FA parol kerak. Parolni chatga yozing:"
                )
            except (PhoneCodeInvalidError, PhoneCodeExpiredError):
                await query.edit_message_text("❌ Kod xato yoki muddati o'tgan. /start bosing.")
                await client.disconnect()
                user_states.pop(chat_id, None)
            except Exception as e:
                await query.edit_message_text(f"❌ Xatolik: {safe_text(e,200)}")
                await client.disconnect()
                user_states.pop(chat_id, None)
            return

        # raqam
        state["entered_code"] = state.get("entered_code", "") + key
        dots = "•" * len(state["entered_code"])
        await query.edit_message_text(
            f"📩 Kod:\n┌────────────────────┐\n│ Kiritildi: {dots:<10}│\n└────────────────────┘",
            reply_markup=code_keyboard(),
        )
        return

    # ── Broadcast tasdiqlash ───────────────────────────────────────────
    if data == "bc_yes":
        if state.get("step") != "BROADCAST_CONFIRM":
            return
        btext = state.get("broadcast_text", "")
        user_states.pop(chat_id, None)
        await query.edit_message_text("🔄 Yuborilmoqda... Iltimos kuting.")
        await _do_broadcast(update, ctx, chat_id, btext)
        return

    if data == "bc_no":
        user_states.pop(chat_id, None)
        await query.edit_message_text("❌ Bekor qilindi.", reply_markup=main_menu())
        return

    # ── Asosiy menyu tugmalari ─────────────────────────────────────────
    user = get_user(chat_id)
    if not user or not user["session_str"]:
        await query.edit_message_text("❌ Avval /start orqali kiring.")
        return

    if data == "m_broadcast":
        user_states[chat_id] = {"step": "BROADCAST_TEXT"}
        await query.edit_message_text(
            "📢 Barcha guruhlaringizga yubormoqchi bo'lgan xabar matnini yozing:"
        )

    elif data == "m_bandman":
        await query.edit_message_text(
            "📵 Bandman rejimi:\n\n"
            "Kimdir sizga yozganda avtomatik javob beradi.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Yoqish (standart)", callback_data="bm_on_default"),
                 InlineKeyboardButton("✍️ Matn bilan yoqish", callback_data="bm_on_custom")],
                [InlineKeyboardButton("❌ O'chirish", callback_data="bm_off")],
                [InlineKeyboardButton("📊 Holat", callback_data="bm_status")],
                [InlineKeyboardButton("🔙 Orqaga", callback_data="m_back")],
            ]),
        )

    elif data == "bm_on_default":
        with db_lock:
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO bandman(chat_id, enabled, message)
                       VALUES(?,1,NULL)
                       ON CONFLICT(chat_id) DO UPDATE SET enabled=1, message=NULL""",
                    (chat_id,),
                )
                conn.commit()
        await query.edit_message_text(
            "✅ Bandman yoqildi!\n"
            "📝 Standart matn: 'Hozir bandman, keyinroq javob beraman.'",
            reply_markup=main_menu(),
        )

    elif data == "bm_on_custom":
        user_states[chat_id] = {"step": "BANDMAN_TEXT"}
        await query.edit_message_text(
            "✍️ Bandman matningizni yozing:\n"
            "Misol: Hozir uxlayapman, ertaga javob beraman."
        )

    elif data == "bm_off":
        with db_lock:
            with get_db() as conn:
                conn.execute(
                    "UPDATE bandman SET enabled=0 WHERE chat_id=?", (chat_id,)
                )
                conn.commit()
        await query.edit_message_text("✅ Bandman o'chirildi.", reply_markup=main_menu())

    elif data == "bm_status":
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM bandman WHERE chat_id=?", (chat_id,)
            ).fetchone()
        if not row:
            status = "O'chirilgan"
            msg    = "—"
        else:
            status = "✅ Yoqilgan" if row["enabled"] else "❌ O'chirilgan"
            msg    = row["message"] or "Standart matn"
        await query.edit_message_text(
            f"📊 Bandman holati:\nStatus: {status}\nMatn: {msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Orqaga", callback_data="m_bandman")]
            ]),
        )

    elif data == "m_save":
        await query.edit_message_text(
            "💾 Media saqlash:\n\n"
            "Biror rasm/video/faylni menga yuboring — men uni serverga saqlayman.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Orqaga", callback_data="m_back")]
            ]),
        )
        user_states[chat_id] = {"step": "SAVE_MEDIA"}

    elif data == "m_down":
        user_states[chat_id] = {"step": "VIDEO_URL"}
        await query.edit_message_text(
            "📥 Video yuklash:\n\n"
            "YouTube, TikTok, Instagram va boshqa saytlar URL sini yuboring:"
        )

    elif data == "m_sticker":
        await query.edit_message_text(
            "🎨 Sticker yaratish:\n\n"
            "Rasm yuboring — men uni Telegram sticker formatiga o'tkazaman.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Orqaga", callback_data="m_back")]
            ]),
        )
        user_states[chat_id] = {"step": "STICKER_IMAGE"}

    elif data == "m_editinfo":
        await query.edit_message_text(
            "✏️ Edit Tracking:\n\n"
            "Sizga yozilgan xabarlar o'zgartirilsa, men asl matnni ko'rsataman.\n\n"
            "Bu funksiya avtomatik ishlaydi — userbot akkauntingiz orqali.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Orqaga", callback_data="m_back")]
            ]),
        )

    elif data == "m_stats":
        with get_db() as conn:
            bc_count = conn.execute(
                "SELECT COUNT(*) as c FROM broadcast_log WHERE chat_id=?", (chat_id,)
            ).fetchone()["c"]
            bm_row = conn.execute(
                "SELECT * FROM bandman WHERE chat_id=?", (chat_id,)
            ).fetchone()

        bm_status = "✅" if bm_row and bm_row["enabled"] else "❌"
        saved = len([f for f in os.listdir(SAVED_MEDIA_DIR) if f.startswith(f"{chat_id}_")])

        await query.edit_message_text(
            f"📊 Statistika:\n\n"
            f"📢 Broadcast yuborilgan: {bc_count} marta\n"
            f"📵 Bandman: {bm_status}\n"
            f"💾 Saqlangan media: {saved} ta\n",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Orqaga", callback_data="m_back")]
            ]),
        )

    elif data == "m_logout":
        with db_lock:
            with get_db() as conn:
                conn.execute("DELETE FROM users WHERE chat_id=?", (chat_id,))
                conn.commit()
        user_states.pop(chat_id, None)
        session_path = get_session_path(chat_id)
        for ext in [".session", ".session-journal"]:
            try:
                os.remove(session_path + ext)
            except OSError:
                pass
        await query.edit_message_text(
            "🚪 Tizimdan chiqdingiz. Qayta kirish uchun /start bosing."
        )

    elif data == "m_back":
        await query.edit_message_text("📋 Asosiy menyu:", reply_markup=main_menu())

# =====================================================================
# MEDIA SAQLASH (bot orqali)
# =====================================================================
async def media_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    state   = user_states.get(chat_id, {})

    if state.get("step") == "SAVE_MEDIA":
        msg = update.message
        if not msg.document and not msg.photo and not msg.video and not msg.audio:
            await msg.reply_text("❌ Bu fayl turi qo'llab-quvvatlanmaydi.")
            return

        file_obj  = msg.document or msg.video or msg.audio
        photo_obj = msg.photo[-1] if msg.photo else None
        tg_file   = await ctx.bot.get_file(
            file_obj.file_id if file_obj else photo_obj.file_id
        )
        ext   = os.path.splitext(tg_file.file_path or "file.bin")[1] or ".bin"
        fname = f"{chat_id}_{int(datetime.now().timestamp())}{ext}"
        fpath = os.path.join(SAVED_MEDIA_DIR, fname)
        await tg_file.download_to_drive(fpath)
        size = get_file_size(fpath)
        user_states.pop(chat_id, None)
        await msg.reply_text(
            f"✅ Fayl saqlandi!\n"
            f"📁 Nom: {fname}\n"
            f"📏 Hajm: {size}",
            reply_markup=main_menu(),
        )

    elif state.get("step") == "STICKER_IMAGE":
        msg = update.message
        photo = msg.photo[-1] if msg.photo else None
        doc   = msg.document if msg.document else None
        if not photo and not doc:
            await msg.reply_text("❌ Rasm yuboring.")
            return

        tg_file = await ctx.bot.get_file(
            photo.file_id if photo else doc.file_id
        )
        in_path  = os.path.join(TEMP_DIR, f"{chat_id}_in.jpg")
        out_path = os.path.join(STICKERS_DIR, f"{chat_id}_sticker.webp")
        await tg_file.download_to_drive(in_path)

        status_msg = await msg.reply_text("⏳ Sticker tayyorlanmoqda...")
        try:
            await asyncio.to_thread(_make_sticker, in_path, out_path)
            with open(out_path, "rb") as f:
                await ctx.bot.send_sticker(chat_id, f)
            await status_msg.edit_text(
                "✅ Sticker tayyor!\n"
                "Yuqoridagi stickerni to'plamingizga qo'shishingiz mumkin.",
                reply_markup=main_menu(),
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Sticker xatosi: {safe_text(e,200)}")
        finally:
            user_states.pop(chat_id, None)
            for p in [in_path, out_path]:
                try: os.remove(p)
                except: pass

# =====================================================================
# STICKER YARATISH
# =====================================================================
def _make_sticker(input_path: str, output_path: str):
    img = ImageOps.exif_transpose(Image.open(input_path)).convert("RGBA")
    img.thumbnail((512, 512), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    x = (512 - img.width) // 2
    y = (512 - img.height) // 2
    canvas.paste(img, (x, y), img)
    canvas = ImageEnhance.Color(canvas).enhance(1.1)
    canvas = ImageEnhance.Contrast(canvas).enhance(1.05)
    canvas.save(output_path, "WEBP", quality=90)

# =====================================================================
# VIDEO YUKLASH
# =====================================================================
async def _download_and_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE, url: str):
    chat_id = update.effective_chat.id

    if not re.match(r"^https?://", url):
        await update.message.reply_text("❌ Noto'g'ri URL.")
        return

    status = await update.message.reply_text("⏳ Video yuklanmoqda...")
    out_path = [None]

    def _dl():
        opts = {
            "format":  "best[height<=720]/best",
            "outtmpl": os.path.join(VIDEOS_DIR, f"{chat_id}_%(title).40s.%(ext)s"),
            "quiet":   True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            out_path[0] = ydl.prepare_filename(info)
            return info.get("title", "Video"), info.get("duration", 0)

    try:
        title, dur = await asyncio.to_thread(_dl)
        path = out_path[0]
        if not path or not os.path.exists(path):
            raise FileNotFoundError("Fayl topilmadi.")

        size = get_file_size(path)
        m, s = divmod(int(dur), 60)
        await status.edit_text(f"📤 Yuborilmoqda: {title[:50]}...")
        with open(path, "rb") as f:
            await ctx.bot.send_video(
                chat_id, f,
                caption=f"🎬 {title}\n⏱ {m}:{s:02d} | 📏 {size}",
                supports_streaming=True,
            )
        await status.delete()
        os.remove(path)
    except Exception as e:
        await status.edit_text(f"❌ Xatolik: {safe_text(e, 300)}", reply_markup=main_menu())

# =====================================================================
# BROADCAST
# =====================================================================
async def _do_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str):
    user = get_user(chat_id)
    if not user or not user["session_str"]:
        await ctx.bot.send_message(chat_id, "❌ Session topilmadi.")
        return

    uclient = TelegramClient(StringSession(user["session_str"]), API_ID, API_HASH)
    await uclient.connect()

    ok = fail = 0
    try:
        async for dialog in uclient.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                try:
                    await uclient.send_message(dialog.id, text)
                    ok += 1
                    await asyncio.sleep(3)
                except FloodWaitError as e:
                    await ctx.bot.send_message(
                        chat_id,
                        f"⚠️ Flood limit: {e.seconds}s kutilmoqda..."
                    )
                    await asyncio.sleep(e.seconds)
                except Exception:
                    fail += 1
    finally:
        await uclient.disconnect()

    with db_lock:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO broadcast_log(chat_id,text,success,fail,created_at) VALUES(?,?,?,?,?)",
                (chat_id, text[:500], ok, fail, datetime.now().isoformat()),
            )
            conn.commit()

    await ctx.bot.send_message(
        chat_id,
        f"📢 Broadcast yakunlandi!\n\n"
        f"✅ Yuborildi: {ok} ta\n"
        f"❌ Yuborilmadi: {fail} ta",
        reply_markup=main_menu(),
    )

# =====================================================================
# USERBOT SESSIYASINI ISHGA TUSHIRISH (edit tracking + bandman)
# =====================================================================
async def start_userbot_for(chat_id: int):
    """Har bir foydalanuvchi uchun Telethon clientni ishga tushiradi."""
    async with client_lock:
        if chat_id in active_clients:
            return

    user = get_user(chat_id)
    if not user or not user["session_str"]:
        return

    client = TelegramClient(StringSession(user["session_str"]), API_ID, API_HASH)
    await client.connect()

    # ── Edit tracking ──────────────────────────────────────────────────
    @client.on(events.MessageEdited)
    async def on_edit(event):
        if event.out:
            return
        try:
            sender = await event.get_sender()
            if not sender or getattr(sender, "bot", False):
                return
            if not event.is_private:
                return

            original = None
            with get_db() as conn:
                row = conn.execute(
                    "SELECT original FROM edit_history WHERE owner_id=? AND msg_chat_id=? AND msg_id=?",
                    (chat_id, event.chat_id, event.id),
                ).fetchone()
                if row:
                    original = row["original"]

            if not original:
                return

            new_text = event.raw_text or "[media]"
            if original == new_text:
                return

            name = getattr(sender, "first_name", None) or str(sender.id)
            await client.send_message(
                "me",
                f"✏️ Xabar tahrirlandi!\n\n"
                f"👤 Kim: {name}\n"
                f"📝 Asl: {original}\n"
                f"✏️ Yangi: {new_text}",
            )
        except Exception:
            pass

    # ── Yangi xabarni saqlash (edit track uchun) ──────────────────────
    @client.on(events.NewMessage(incoming=True))
    async def on_new(event):
        if not event.is_private or event.out:
            return
        try:
            text = event.raw_text or "[media]"
            with db_lock:
                with get_db() as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO edit_history
                           (owner_id, msg_chat_id, msg_id, original, created_at)
                           VALUES(?,?,?,?,?)""",
                        (chat_id, event.chat_id, event.id, text, datetime.now().isoformat()),
                    )
                    conn.commit()
        except Exception:
            pass

        # ── Bandman ───────────────────────────────────────────────────
        try:
            with get_db() as conn:
                bm = conn.execute(
                    "SELECT * FROM bandman WHERE chat_id=?", (chat_id,)
                ).fetchone()

            if not bm or not bm["enabled"]:
                return

            sender = await event.get_sender()
            if not sender or getattr(sender, "bot", False):
                return

            user_id  = event.sender_id
            cooldown = bm["cooldown"] or 300

            with get_db() as conn:
                last = conn.execute(
                    "SELECT last_at FROM last_bandman WHERE user_id=? AND owner_id=?",
                    (user_id, chat_id),
                ).fetchone()

            if last:
                diff = (datetime.now() - datetime.fromisoformat(last["last_at"])).total_seconds()
                if diff < cooldown:
                    return

            reply_text = (
                bm["message"] or
                "Hozir bandman, imkon bo'lishi bilan javob beraman."
            )

            with db_lock:
                with get_db() as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO last_bandman(user_id, owner_id, last_at)
                           VALUES(?,?,?)""",
                        (user_id, chat_id, datetime.now().isoformat()),
                    )
                    conn.commit()

            await asyncio.sleep(3)
            await event.reply(reply_text)
        except Exception:
            pass

    async with client_lock:
        active_clients[chat_id] = client

    logger.info(f"Userbot started for chat_id={chat_id}")

async def start_all_userbots():
    """Bot ishga tushganda barcha sessionlarni yoqadi."""
    with get_db() as conn:
        rows = conn.execute("SELECT chat_id FROM users WHERE session_str IS NOT NULL").fetchall()
    for row in rows:
        try:
            await start_userbot_for(row["chat_id"])
        except Exception as e:
            logger.warning(f"Userbot {row['chat_id']} xato: {e}")

# =====================================================================
# MAIN
# =====================================================================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu",  cmd_menu))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.AUDIO,
        media_handler,
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        msg_handler,
    ))

    async def on_startup(app):
        await start_all_userbots()

    app.post_init = on_startup

    print("🤖 Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
