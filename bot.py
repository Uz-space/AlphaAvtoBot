# --- bot.py ---
import logging
import os
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")  # masalan: @mychannelname yoki -1001234567890


def parse_input_to_rows(text: str) -> list[dict]:
    rows = []
    for line in text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            rows.append({"field": key.strip(), "details": value.strip()})
        elif line.strip():
            rows.append({"field": "Qiymat", "details": line.strip()})
    return rows


def build_html_table(rows: list[dict], username: str) -> str:
    header = "🏅 <b>New Withdraw Success</b>\n\n"

    # Blockquote ichida congratulations
    quote = f"<blockquote>🎁 <i>Congratulations <b>{username}</b>, ma'lumotlaringiz muvaffaqiyatli qayta ishlandi.</i></blockquote>\n\n"

    # Table header
    field_w = 12
    detail_w = 20
    separator = "─" * (field_w + detail_w + 3)

    table = f"<code>"
    table += f"{'Field':<{field_w}}  {'Details':<{detail_w}}\n"
    table += f"{separator}\n"
    for row in rows:
        field = row['field'][:field_w]
        details = row['details'][:detail_w]
        table += f"{field:<{field_w}}  {details:<{detail_w}}\n"
    table += f"</code>"

    return header + quote + table


async def send_message_html(chat_id: str | int, html: str) -> bool:
    payload = {
        "chat_id": chat_id,
        "text": html,
        "parse_mode": "HTML",
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=10.0,
        )
        data = response.json()
        if not data.get("ok"):
            logger.error(f"sendMessage xatosi ({chat_id}): {data}")
            return False
        return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Salom! Menga ma'lumot yuboring:\n\n"
        "Misol:\n"
        "Ism: Sardor\n"
        "Yosh: 22\n"
        "Shahar: Toshkent\n\n"
        "Men tableni chatga va kanalga yuboraman."
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    username = user.first_name or "Foydalanuvchi"
    user_input = update.message.text.strip()
    chat_id = update.effective_chat.id

    if len(user_input) < 2:
        await update.message.reply_text("❌ Kamida biror narsa yozing.")
        return

    rows = parse_input_to_rows(user_input)
    if not rows:
        await update.message.reply_text("❌ Formatni tekshiring: 'Kalit: Qiymat' ko'rinishida yozing.")
        return

    html = build_html_table(rows, username)

    # Chatga yuborish
    await send_message_html(chat_id, html)

    # Kanalga yuborish
    if CHANNEL_ID:
        await send_message_html(CHANNEL_ID, html)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Xato: {context.error}")


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable topilmadi.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
