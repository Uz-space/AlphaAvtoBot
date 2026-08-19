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
CHANNEL_ID = os.environ.get("CHANNEL_ID")


def parse_input_to_rows(text: str) -> list[dict]:
    rows = []
    for line in text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            rows.append({"field": key.strip(), "details": value.strip()})
        elif line.strip():
            rows.append({"field": "Qiymat", "details": line.strip()})
    return rows


async def send_rich_table(chat_id: int | str, username: str, rows: list[dict]) -> bool:
    table_lines = ["| Field | Details |", "|-------|---------|"]
    for row in rows:
        table_lines.append(f"| {row['field']} | {row['details']} |")

    markdown = f"✅ **{username}**, ma'lumotlaringiz:\n\n" + "\n".join(table_lines)

    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "markdown": markdown
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendRichMessage",
            json=payload,
            timeout=10.0,
        )
        data = response.json()
        if not data.get("ok"):
            logger.error(f"sendRichMessage xatosi ({chat_id}): {data}")
            return False
        return True


async def send_fallback(chat_id: int | str, rows: list[dict], context: ContextTypes.DEFAULT_TYPE) -> None:
    lines = [f"{'Field':<15} | {'Details'}", "-" * 35]
    for row in rows:
        lines.append(f"{row['field']:<15} | {row['details']}")
    await context.bot.send_message(
        chat_id=chat_id,
        text="```\n" + "\n".join(lines) + "\n```",
        parse_mode="Markdown"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Salom! Menga ma'lumot yuboring:\n\n"
        "Misol:\n"
        "Ism: Sardor\n"
        "Yosh: 22\n"
        "Shahar: Toshkent"
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
        await update.message.reply_text("❌ Format: 'Kalit: Qiymat' ko'rinishida yozing.")
        return

    # Chatga yuborish
    success = await send_rich_table(chat_id, username, rows)
    if not success:
        await send_fallback(chat_id, rows, context)

    # Kanalga yuborish
    if CHANNEL_ID:
        await send_rich_table(CHANNEL_ID, username, rows)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Xato: {context.error}")


def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN topilmadi.")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
