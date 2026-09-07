from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import logging

TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)
dp.middleware.setup(LoggingMiddleware())

# ✅ Asosiy tugmalar (doimiy)
def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "🆕 Bot yaratish",
        "📋 Botlarim",
        "💰 Balans",
        "👥 Referal",
        "🌐 Web ilova",
        "❓ Yordam",
        "⚙️ Sozlamalar",
        "🛠 Maker Bo'lim",
        "✉️ Xabar"
    ]
    for btn in buttons:
        keyboard.add(KeyboardButton(btn))
    return keyboard

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Xush kelibsiz!\n\n"
        "📌 Makefy Bot | MAKER bot\n"
        "🚀 20 Gbit/s tezkor Web Platforma\n\n"
        "🔹 Bu loyiha orqali Telegram botlaringizni web ilovamiz orqali yarating!\n"
        "🔹 Quyidagi tugmalardan foydalaning:",
        reply_markup=main_keyboard()
    )

@dp.message_handler(lambda msg: msg.text == "🆕 Bot yaratish")
async def create_bot(message: types.Message):
    await message.answer("🤖 Yangi bot yaratish bo'limi.", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "📋 Botlarim")
async def my_bots(message: types.Message):
    await message.answer("📋 Sizning botlaringiz ro'yxati.", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "💰 Balans")
async def balance(message: types.Message):
    await message.answer("💰 Sizning balansingiz: 0 so'm", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "👥 Referal")
async def referral(message: types.Message):
    await message.answer("👥 Referal havolangiz: https://t.me/...", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "🌐 Web ilova")
async def web_app(message: types.Message):
    await message.answer("🌐 Web ilovaga o'tish: [link]", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "❓ Yordam")
async def help_command(message: types.Message):
    await message.answer("❓ Yordam: admin bilan bog'lang.", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "⚙️ Sozlamalar")
async def settings(message: types.Message):
    await message.answer("⚙️ Sozlamalar bo'limi.", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "🛠 Maker Bo'lim")
async def maker_section(message: types.Message):
    await message.answer("🛠 Maker bo'limi (faqat adminlar uchun).", reply_markup=main_keyboard())

@dp.message_handler(lambda msg: msg.text == "✉️ Xabar")
async def send_message(message: types.Message):
    await message.answer("✉️ Xabar yozish bo'limi.", reply_markup=main_keyboard())

if __name__ == "__main__":
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
