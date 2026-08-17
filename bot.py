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
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return bar

# ========== BOT KOMANDALARI ==========

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎯 *Yuklanish Botiga Xush Kelibsiz!*\n\n"
        "▶️ /load - Yuklanishni boshlash\n"
        "📊 1% → 2% → 3% → ... → 100%\n"
        "⏱️ Har bir foiz 0.3 sekund",
        parse_mode="Markdown"
    )

@dp.message(Command("load"))
async def load_animation(message: types.Message):
    msg = await message.answer("⏳ 0%")
    
    # 1% dan 100% gacha - HAR BIR FOIZDA yangilanadi
    for percent in range(1, 101):  # 1,2,3,4,5...100
        bar = progress_bar(percent)
        await asyncio.sleep(0.3)  # 0.3 sekund - sekin va aniq
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
    
    # 1% dan 100% gacha - HAR BIR FOIZDA yangilanadi
    for percent in range(1, 101):  # 1,2,3,4,5...100
        bar = progress_bar(percent)
        await asyncio.sleep(0.3)  # 0.3 sekund - sekin va aniq
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

@dp.message(Command("fast"))
async def fast_load(message: types.Message):
    """Tez yuklanish - 0.05 sekund"""
    msg = await message.answer("⚡ 0%")
    
    for percent in range(1, 101):
        bar = progress_bar(percent)
        await asyncio.sleep(0.05)
        await msg.edit_text(f"⚡ {bar} {percent}%")
    
    await msg.edit_text("✅ *Tez yuklash tugallandi!*", parse_mode="Markdown")

@dp.message(Command("slow"))
async def slow_load(message: types.Message):
    """Sekin yuklanish - 0.5 sekund"""
    msg = await message.answer("🐢 0%")
    
    for percent in range(1, 101):
        bar = progress_bar(percent)
        await asyncio.sleep(0.5)
        await msg.edit_text(f"🐢 {bar} {percent}%")
    
    await msg.edit_text("✅ *Sekin yuklash tugallandi!*", parse_mode="Markdown")

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "📖 *Buyruqlar:*\n\n"
        "/start - Boshlash\n"
        "/load - Oddiy yuklanish (0.3 sekund)\n"
        "/fast - Tez yuklanish (0.05 sekund)\n"
        "/slow - Sekin yuklanish (0.5 sekund)\n"
        "/help - Yordam\n\n"
        "📊 1% → 2% → 3% → ... → 100%",
        parse_mode="Markdown"
    )

# ========== BOT ISHGA TUSHIRISH ==========

async def main():
    print("=" * 50)
    print("🤖 BOT ISHGA TUSHDI!")
    print("📊 1% → 2% → 3% → ... → 100%")
    print("⏱️ Har bir foiz 0.3 sekund")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
