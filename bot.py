import asyncio
import random
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

# ========== ANIMATSIYALAR ==========
LOADING_ANIMATIONS = [
    "⏳ ████████░░░░ 67%",
    "⏳ ██░░░░░░░░░░ 17%",
    "⏳ ██████████░░ 89%",
    "⏳ ██████░░░░░░ 52%",
    "⏳ ████░░░░░░░░ 33%",
    "⏳ ████████████ 100%",
    "⏳ ███████░░░░░ 58%",
    "⏳ █████████░░░ 82%",
    "⏳ ███░░░░░░░░░ 25%",
    "⏳ ███████████░ 94%",
    "🌐 Yuklanmoqda... ⠋",
    "🌐 Yuklanmoqda... ⠙",
    "🌐 Yuklanmoqda... ⠹",
    "🌐 Yuklanmoqda... ⠸",
    "🌐 Yuklanmoqda... ⠼",
    "🌐 Yuklanmoqda... ⠴",
    "🌐 Yuklanmoqda... ⠦",
    "🌐 Yuklanmoqda... ⠧",
    "🌐 Yuklanmoqda... ⠇",
    "🌐 Yuklanmoqda... ⠏",
    "📡 Yuklanmoqda.",
    "📡 Yuklanmoqda..",
    "📡 Yuklanmoqda...",
    "📡 Yuklanmoqda....",
    "📡 Yuklanmoqda.....",
    "📡 Yuklanmoqda......",
    "💓 Yuklanmoqda... ████░░ 40%",
    "💗 Yuklanmoqda... ██████░ 70%",
    "💖 Yuklanmoqda... ████████ 90%",
    "❤️ Yuklanmoqda... ████████ 100%",
    "🌅 ░░░░░░░░░░░░ 0%",
    "🌅 ██░░░░░░░░░░ 20%",
    "🌅 ██████░░░░░░ 50%",
    "🌅 ████████████ 100% ☀️",
    "☔️ Yuklanmoqda... 💧💧💧",
    "☔️ Yuklanmoqda... 💧💧",
    "☔️ Yuklanmoqda... 💧",
    "☔️ Yuklanmoqda... 🌧️",
    "🚀 TAYYOR...",
    "🚀 3...",
    "🚀 2...",
    "🚀 1...",
    "🚀 UCHIRILDI! 🔥🔥🔥",
    "🚀 Kosmosga uchmoqda... 🌌",
    "🏎️ ████░░░░░░ 40%",
    "🏎️ ████████░░ 80%",
    "🏎️ ██████████ 100% 🏁",
    "🏎️ VROOOOM! 💨",
    "☕️ Qahva tayyorlanmoqda... ██░░ 20%",
    "☕️ Qahva tayyorlanmoqda... ██████ 60%",
    "☕️ Qahva tayyorlanmoqda... ████████ 90%",
    "☕️ Qahva tayyor! ✅",
    "☕️ Qahva iching! 😋",
    "🍕 Xamir tayyor... ██░░ 25%",
    "🍕 Sos surtilmoqda... ████ 50%",
    "🍕 Pishirilmoqda... ██████ 75%",
    "🍕 Tayyor! 🌟",
    "🍕 Yeyishga tayyor! 😋",
    "🧟 Yuklanmoqda... 🧠🧠🧠",
    "🧟 Yuklanmoqda... 🧠🧠",
    "🧟 Yuklanmoqda... 🧠",
    "🧟 BRAAAAINS! 🧟‍♂️",
    "🥷 Yuklanmoqda... ████ 40%",
    "🥷 Yuklanmoqda... ██████ 70%",
    "🥷 Yuklanmoqda... ████████ 100% 🗡️",
    "🥷 Ninja tayyor! ⚔️",
    "🧑‍🚀 Orbitaga chiqish... ██ 20%",
    "🧑‍🚀 Vaznsizlik... ██████ 60%",
    "🧑‍🚀 Koinotga yetib keldi! 🌟",
    "🧑‍🚀 Yer ko'rinmoqda! 🌍",
    "🤖 Tizim ishga tushmoqda...",
    "🤖 Yuklanmoqda... ████░░ 45%",
    "🤖 Yuklanmoqda... ██████░ 78%",
    "🤖 TAYYOR! ⚡",
    "🤖 BEEP BOOP! 🔧",
    "🎵 Yuklanmoqda... ♪",
    "🎵 Yuklanmoqda... ♫",
    "🎵 Yuklanmoqda... ♬",
    "🎵 Yuklanmoqda... ♩",
    "🎵 Musiqa tayyor! 🎶",
    "🎵 DANCE TIME! 💃",
    "🎮 Yuklanmoqda... ██ 15%",
    "🎮 Yuklanmoqda... ██████ 55%",
    "🎮 Yuklanmoqda... ████████ 85%",
    "🎮 O'YIN BOSHLANDI! 🕹️",
    "🎮 LEVEL UP! ⬆️",
    "📖 Sahifa 1... ██░░ 20%",
    "📖 Sahifa 2... ████ 40%",
    "📖 Sahifa 3... ██████ 60%",
    "📖 Sahifa 4... ████████ 80%",
    "📖 Kitob tugadi! 📚",
    "🎬 Yuklanmoqda... ██ 10%",
    "🎬 Yuklanmoqda... ██████ 50%",
    "🎬 Yuklanmoqda... ████████ 90%",
    "🎬 FILM BOSHLANDI! 🍿",
    "🎬 Popkorn tayyor! 🍿",
    "🏃 Yuklanmoqda... ██ 30%",
    "🏃 Yuklanmoqda... ██████ 60%",
    "🏃 Yuklanmoqda... ████████ 90%",
    "🏃 MARRA! 🏆",
    "🏃 REKORD! 🥇",
    "🌊 Yuklanmoqda... 🌊",
    "🌊 Yuklanmoqda... 🌊🌊",
    "🌊 Yuklanmoqda... 🌊🌊🌊",
    "🌊 Sohilga yetib keldik! 🏖️",
    "🌊 Sörf qilamizmi? 🏄",
    "🚂 Yuklanmoqda... 🚃",
    "🚂 Yuklanmoqda... 🚃🚃",
    "🚂 Yuklanmoqda... 🚃🚃🚃",
    "🚂 Stansiyaga yetib keldik! 🚉",
    "🚂 CHOO CHOO! 🚂",
    "✈️ Uchishga tayyor... 30%",
    "✈️ Havoga ko'tarilmoqda... 60%",
    "✈️ Parvoz davom etmoqda... 85%",
    "✈️ MANZILGA YETIB KELDIK! 🛬",
    "✈️ Salqin parvoz! 🌤️",
    "🐟 Yuklanmoqda... ██ 20%",
    "🐟 Yuklanmoqda... ██████ 60%",
    "🐟 Yuklanmoqda... ████████ 90%",
    "🐟 Baliq tayyor! 🎣",
    "🐟 KATTA BALIQ! 🐋",
    "😊 ██░░░░░░ 25%",
    "😊 ██████░░ 65%",
    "😊 ████████ 100% 🎉",
    "😊 BAXT TOPILDI! 🌟",
    "💻 Tizim yuklanmoqda...",
    "💻 Yuklanmoqda... ████░░ 45%",
    "💻 Yuklanmoqda... ██████░ 78%",
    "💻 TIZIM TAYYOR! 🖥️",
    "💻 WINDOWS YUKLANDI! 🪟",
    "📱 Zaryadlanmoqda... ██ 20%",
    "📱 Zaryadlanmoqda... ██████ 60%",
    "📱 Zaryadlanmoqda... ████████ 90%",
    "📱 BATAREYA TO'LA! 🔋",
    "📱 100% ZARYAD! ✅",
    "🕷️ To'r to'qilmoqda... ██ 30%",
    "🕷️ To'r to'qilmoqda... ██████ 70%",
    "🕷️ To'r to'qilmoqda... ████████ 100% 🕸️",
    "🕷️ SPIDERMAN! 🦸",
    "🍎 Yuklanmoqda... ██ 20%",
    "🍎 Yuklanmoqda... ██████ 60%",
    "🍎 Yuklanmoqda... ████████ 90%",
    "🍎 OLMA TAYYOR! 🥧",
    "🎨 Rasm chizilmoqda... ██ 15%",
    "🎨 Rasm chizilmoqda... ██████ 55%",
    "🎨 Rasm chizilmoqda... ████████ 85%",
    "🎨 Rasm tayyor! 🖼️",
    "🎨 SAN'AT! ✨",
    "⏳ ⠋",
    "⏳ ⠙",
    "⏳ ⠹",
    "⏳ ⠸",
    "⏳ ⠼",
    "⏳ ⠴",
    "⏳ ⠦",
    "⏳ ⠧",
    "⏳ ⠇",
    "⏳ ⠏",
    "⭐ Yuklanmoqda... ☆",
    "⭐ Yuklanmoqda... ★",
    "⭐ Yuklanmoqda... ☆",
    "⭐ Yuklanmoqda... ★",
    "⭐ TAYYOR! ✨",
    "⭐ SUPERSTAR! 🌟",
    "🎲 Tashlanmoqda... ⚀",
    "🎲 Tashlanmoqda... ⚁",
    "🎲 Tashlanmoqda... ⚂",
    "🎲 Tashlanmoqda... ⚃",
    "🎲 Tashlanmoqda... ⚄",
    "🎲 Tashlanmoqda... ⚅",
    "🎲 NATIJA: 6! 🎉",
    "🔴 Yuklanmoqda... 1%",
    "🟡 Yuklanmoqda... 25%",
    "🟢 Yuklanmoqda... 50%",
    "🔵 Yuklanmoqda... 75%",
    "🟣 Yuklanmoqda... 100% ✅",
    "🐱 Yuklanmoqda... 😺",
    "🐱 Yuklanmoqda... 😸",
    "🐱 Yuklanmoqda... 😻",
    "🐱 MUSHUK TAYYOR! 🐈",
    "🐱 Nyaa~ 😽",
    "🐶 Yuklanmoqda... 🐕",
    "🐶 Yuklanmoqda... 🐩",
    "🐶 Yuklanmoqda... 🐕‍🦺",
    "🐶 IT TAYYOR! 🦮",
    "🐶 WOOF WOOF! 🐾",
    "🌸 Yuklanmoqda... 🌺",
    "🌸 Yuklanmoqda... 🌻",
    "🌸 Yuklanmoqda... 🌹",
    "🌸 GULLAR TAYYOR! 🌷",
    "🌸 BOG' GULLADI! 🌼",
    "🍜 Yuklanmoqda... 🍲",
    "🍜 Yuklanmoqda... 🥘",
    "🍜 Yuklanmoqda... 🍛",
    "🍜 OVQAT TAYYOR! 🍽️",
    "🍜 BON APPETIT! 😋",
    "🍦 Yuklanmoqda... 🍧",
    "🍦 Yuklanmoqda... 🍨",
    "🍦 Yuklanmoqda... 🍦",
    "🍦 MUZQAYMOQ TAYYOR! 🍦",
    "🍦 YEYISHGA TAYYOR! 😋",
    "🎥 Yuklanmoqda... 📽️",
    "🎥 Yuklanmoqda... 🎞️",
    "🎥 Yuklanmoqda... 🎬",
    "🎥 KINO TAYYOR! 🍿",
    "🎥 PREMYERA! 🌟",
]

# ========== KOMANDALAR ==========

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎯 *Yuklanish Animatsiyalari Botiga Xush Kelibsiz!*\n\n"
        "▶️ /load - Yuklanishni boshlash\n"
        f"🎭 {len(LOADING_ANIMATIONS)}+ animatsiya mavjud",
        parse_mode="Markdown"
    )

@dp.message(Command("load"))
async def load_animation(message: types.Message):
    msg = await message.answer("🎬 Yuklanmoqda...")
    
    for _ in range(6):
        anim = random.choice(LOADING_ANIMATIONS)
        await asyncio.sleep(0.4)
        await msg.edit_text(f"🔄 {anim}")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Qayta yuklash", callback_data="reload")]
        ]
    )
    
    await msg.edit_text(
        "✅ *Yuklash tugallandi!*\n\n"
        f"🎭 {len(LOADING_ANIMATIONS)} ta animatsiya\n"
        "🔄 Qayta boshlash uchun tugmani bosing",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "reload")
async def reload_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("🔄 Yangilanmoqda...")
    
    msg = await callback.message.answer("🎬 Yuklanmoqda...")
    
    for _ in range(6):
        anim = random.choice(LOADING_ANIMATIONS)
        await asyncio.sleep(0.4)
        await msg.edit_text(f"🌀 {anim}")
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yana bir marta", callback_data="reload")]
        ]
    )
    
    await msg.edit_text(
        "✅ *Tayyor!*\n\n"
        "🔄 Yana boshlash uchun tugmani bosing",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "📖 *Buyruqlar:*\n\n"
        "/start - Boshlash\n"
        "/load - Yuklanish\n"
        "/help - Yordam\n"
        "/stats - Statistika",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    await message.answer(
        f"📊 *Statistika:*\n\n"
        f"🎭 Animatsiyalar: {len(LOADING_ANIMATIONS)}+",
        parse_mode="Markdown"
    )

# ========== BOT ISHGA TUSHIRISH ==========

async def main():
    print("=" * 40)
    print("🤖 BOT ISHGA TUSHDI!")
    print(f"📊 {len(LOADING_ANIMATIONS)} TA ANIMATSIYA")
    print("=" * 40)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
