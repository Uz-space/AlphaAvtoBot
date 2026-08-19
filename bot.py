# --- bot.py ---
import logging
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

BOT_TOKEN = "8245157509:AAH-cL3k2upery-lPPkhIgGvNKVMwGAXXcc"


def build_rich_table(rows: list[dict]) -> dict:
    """
    Markdown pipe table'ni RichBlockTable formatiga o'tkazadi.
    rows = [{"field": "User Id", "details": "Sarah(25...019)"}, ...]
    """
    header_cells = [
        {"RichBlockTableCell": {"content": [{"RichBlockText": {"text": "Field"}}], "is_header": True}},
        {"RichBlockTableCell": {"content": [{"RichBlockText": {"text": "Details"}}], "is_header": True}},
    ]

    data_rows = []
    for row in rows:
        data_rows.append([
            {"RichBlockTableCell": {"content": [{"RichBlockText": {"text": row["field"]}}]}},
            {"RichBlockTableCell": {"content": [{"RichBlockText": {"text": row["details"]}}]}},
        ])

    return {
        "RichBlockTable": {
            "rows": [header_cells] + data_rows,
            "is_bordered": True,
            "is_striped": True,
        }
    }


async def send_rich_message(chat_id: int, text: str, table: dict) -> bool:
    """
    sendRichMessage API call — Bot API 10.1+
    python-telegram-bot hali wrap qilmagan, to'g'ridan-to'g'ri HTTP ishlatamiz.
    """
    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "blocks": [
                {"RichBlockText": {"text": text}},
                table,
            ]
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
            logger.error(f"sendRichMessage xatosi: {data}")
            return False
        return True


def parse_input_to_rows(text: str) -> list[dict]:
    """
    Foydalanuvchi kiritgan matnni table row'larga o'tkazadi.
    Format: "Ism: Sardor\nYosh: 22"
    """
    rows = []
    for line in text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            rows.append({"field": key.strip(), "details": value.strip()})
        elif line.strip():
            rows.append({"field": "Qiymat", "details": line.strip()})
    return rows


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Salom! Menga ma'lumot yuboring:\n\n"
        "Misol:\n"
        "Ism: Sardor\n"
        "Yosh: 22\n"
        "Shahar: Toshkent\n\n"
        "Men native table sifatida ko'rsataman."
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

    table = build_rich_table(rows)
    header_text = f"✅ {username}, ma'lumotlaringiz:"

    success = await send_rich_message(chat_id, header_text, table)

    if not success:
        # Fallback: eski monospace usul
        lines = [f"{'Field':<15} | {'Details'}", "-" * 35]
        for row in rows:
            lines.append(f"{row['field']:<15} | {row['details']}")
        fallback = "```\n" + "\n".join(lines) + "\n```"
        await update.message.reply_text(fallback, parse_mode="Markdown")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Xato: {context.error}")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
