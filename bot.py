import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ========== LOGING ==========
logging.basicConfig(level=logging.INFO)

# ========== BOT TOKEN ==========
TOKEN = "8863932002:AAE7AaYQFBCycRzv-M1zfAIa-ye5HniJj2Q"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== PROGRESS-BAR FUNKSIYASI ==========
def progress_bar(percent, length=20):
    """Progress-bar yaratish ████░░░░"""
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return bar

# ========== BOT KOMANDALARI ==========

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎯 *Yuklanish Botiga Xush Kelibsiz!*\n\n"
        "▶️ /load - Yuklanishni boshlash\n"
        "📊 1% dan 100% gacha (1,2,3,4,5...100)",
        parse_mode="Markdown"
    )

@dp.message(Command("load"))
async def load_animation(message: types.Message):
    msg = await message.answer("⏳ 0%")
    
    # 1% dan 100% gacha - har bir foizda yangilanadi
    for percent in range(1, 101):  # 1,2,3,4,5...100
        bar = progress_bar(percent)
        await asyncio.sleep(0.05)  # 0.05 sekund
        await msg.edit_text(f"⏳ {bar} {percent}%")
    
    # Tugallandi
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Qayta yuklash", callback_data="reload")]
        ]
    )
    
    await msg.edit_text(
        "✅ *Yuklash tugallandi!*\n"
        "🎉 100% tayyor!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "reload")
async def reload_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("🔄 Yangi yuklanish...")
    
    msg = await callback.message.answer("⏳ 0%")
    
    # 1% dan 100% gacha - har bir foizda yangilanadi
    for percent in range(1, 101):  # 1,2,3,4,5...100
        bar = progress_bar(percent)
        await asyncio.sleep(0.05)
        await msg.edit_text(f"⏳ {bar} {percent}%")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yana bir marta", callback_data="reload")]
        ]
    )
    
    await msg.edit_text(
        "✅ *Yuklash tugallandi!*\n"
        "🌟 100% muvaffaqiyatli!",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "📖 *Buyruqlar:*\n\n"
        "/start - Boshlash\n"
        "/load - Yuklanish (1,2,3,4,5...100)\n"
        "/help - Yordam",
        parse_mode="Markdown"
    )

# ========== BOT ISHGA TUSHIRISH ==========

async def main():
    print("=" * 40)
    print("🤖 BOT ISHGA TUSHDI!")
    print("📊 1% dan 100% gacha (1,2,3,4,5...100)")
    print("=" * 40)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
