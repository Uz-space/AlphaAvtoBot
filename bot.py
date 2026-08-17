import asyncio
import random
import sys
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ========== BOT TOKEN ==========
TOKEN = "8863932002:AAE7AaYQFBCycRzv-M1zfAIa-ye5HniJj2Q"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ========== 120+ TURLI ANIMATSIYALAR ==========
LOADING_ANIMATIONS = [
    # 1. Progress-barlar
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
    
    # 2. Aylanuvchi spinnerlar
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
    
    # 3. Nuqtali animatsiyalar
    "📡 Yuklanmoqda.",
    "📡 Yuklanmoqda..",
    "📡 Yuklanmoqda...",
    "📡 Yuklanmoqda....",
    "📡 Yuklanmoqda.....",
    "📡 Yuklanmoqda......",
    
    # 4. Yurak urishi
    "💓 Yuklanmoqda... ████░░ 40%",
    "💗 Yuklanmoqda... ██████░ 70%",
    "💖 Yuklanmoqda... ████████ 90%",
    "❤️ Yuklanmoqda... ████████ 100%",
    
    # 5. Quyosh chiqishi
    "🌅 ░░░░░░░░░░░░ 0%",
    "🌅 ██░░░░░░░░░░ 20%",
    "🌅 ██████░░░░░░ 50%",
    "🌅 ████████████ 100% ☀️",
    
    # 6. Yomg'ir
    "☔️ Yuklanmoqda... 💧💧💧",
    "☔️ Yuklanmoqda... 💧💧",
    "☔️ Yuklanmoqda... 💧",
    "☔️ Yuklanmoqda... 🌧️",
    
    # 7. Raketa
    "🚀 TAYYOR...",
    "🚀 3...",
    "🚀 2...",
    "🚀 1...",
    "🚀 UCHIRILDI! 🔥🔥🔥",
    "🚀 Kosmosga uchmoqda... 🌌",
    
    # 8. Poyga mashinasi
    "🏎️ ████░░░░░░ 40%",
    "🏎️ ████████░░ 80%",
    "🏎️ ██████████ 100% 🏁",
    "🏎️ VROOOOM! 💨",
    
    # 9. Qahva tayyorlash
    "☕️ Qahva tayyorlanmoqda... ██░░ 20%",
    "☕️ Qahva tayyorlanmoqda... ██████ 60%",
    "☕️ Qahva tayyorlanmoqda... ████████ 90%",
    "☕️ Qahva tayyor! ✅",
    "☕️ Qahva iching! 😋",
    
    # 10. Pitsa tayyorlash
    "🍕 Xamir tayyor... ██░░ 25%",
    "🍕 Sos surtilmoqda... ████ 50%",
    "🍕 Pishirilmoqda... ██████ 75%",
    "🍕 Tayyor! 🌟",
    "🍕 Yeyishga tayyor! 😋",
    
    # 11. Zombi
    "🧟 Yuklanmoqda... 🧠🧠🧠",
    "🧟 Yuklanmoqda... 🧠🧠",
    "🧟 Yuklanmoqda... 🧠",
    "🧟 BRAAAAINS! 🧟‍♂️",
    
    # 12. Ninja
    "🥷 Yuklanmoqda... ████ 40%",
    "🥷 Yuklanmoqda... ██████ 70%",
    "🥷 Yuklanmoqda... ████████ 100% 🗡️",
    "🥷 Ninja tayyor! ⚔️",
    
    # 13. Kosmonavt
    "🧑‍🚀 Orbitaga chiqish... ██ 20%",
    "🧑‍🚀 Vaznsizlik... ██████ 60%",
    "🧑‍🚀 Koinotga yetib keldi! 🌟",
    "🧑‍🚀 Yer ko'rinmoqda! 🌍",
    
    # 14. Robot
    "🤖 Tizim ishga tushmoqda...",
    "🤖 Yuklanmoqda... ████░░ 45%",
    "🤖 Yuklanmoqda... ██████░ 78%",
    "🤖 TAYYOR! ⚡",
    "🤖 BEEP BOOP! 🔧",
    
    # 15. Musiqa
    "🎵 Yuklanmoqda... ♪",
    "🎵 Yuklanmoqda... ♫",
    "🎵 Yuklanmoqda... ♬",
    "🎵 Yuklanmoqda... ♩",
    "🎵 Musiqa tayyor! 🎶",
    "🎵 DANCE TIME! 💃",
    
    # 16. O'yin
    "🎮 Yuklanmoqda... ██ 15%",
    "🎮 Yuklanmoqda... ██████ 55%",
    "🎮 Yuklanmoqda... ████████ 85%",
    "🎮 O'YIN BOSHLANDI! 🕹️",
    "🎮 LEVEL UP! ⬆️",
    
    # 17. Kitob o'qish
    "📖 Sahifa 1... ██░░ 20%",
    "📖 Sahifa 2... ████ 40%",
    "📖 Sahifa 3... ██████ 60%",
    "📖 Sahifa 4... ████████ 80%",
    "📖 Kitob tugadi! 📚",
    
    # 18. Film
    "🎬 Yuklanmoqda... ██ 10%",
    "🎬 Yuklanmoqda... ██████ 50%",
    "🎬 Yuklanmoqda... ████████ 90%",
    "🎬 FILM BOSHLANDI! 🍿",
    "🎬 Popkorn tayyor! 🍿",
    
    # 19. Sport
    "🏃 Yuklanmoqda... ██ 30%",
    "🏃 Yuklanmoqda... ██████ 60%",
    "🏃 Yuklanmoqda... ████████ 90%",
    "🏃 MARRA! 🏆",
    "🏃 REKORD! 🥇",
    
    # 20. Dengiz
    "🌊 Yuklanmoqda... 🌊",
    "🌊 Yuklanmoqda... 🌊🌊",
    "🌊 Yuklanmoqda... 🌊🌊🌊",
    "🌊 Sohilga yetib keldik! 🏖️",
    "🌊 Sörf qilamizmi? 🏄",
    
    # 21. Poyezd
    "🚂 Yuklanmoqda... 🚃",
    "🚂 Yuklanmoqda... 🚃🚃",
    "🚂 Yuklanmoqda... 🚃🚃🚃",
    "🚂 Stansiyaga yetib keldik! 🚉",
    "🚂 CHOO CHOO! 🚂",
    
    # 22. Samolyot
    "✈️ Uchishga tayyor... 30%",
    "✈️ Havoga ko'tarilmoqda... 60%",
    "✈️ Parvoz davom etmoqda... 85%",
    "✈️ MANZILGA YETIB KELDIK! 🛬",
    "✈️ Salqin parvoz! 🌤️",
    
    # 23. Baliq
    "🐟 Yuklanmoqda... ██ 20%",
    "🐟 Yuklanmoqda... ██████ 60%",
    "🐟 Yuklanmoqda... ████████ 90%",
    "🐟 Baliq tayyor! 🎣",
    "🐟 KATTA BALIQ! 🐋",
    
    # 24. Baxtli
    "😊 ██░░░░░░ 25%",
    "😊 ██████░░ 65%",
    "😊 ████████ 100% 🎉",
    "😊 BAXT TOPILDI! 🌟",
    
    # 25. Kompyuter
    "💻 Tizim yuklanmoqda...",
    "💻 Yuklanmoqda... ████░░ 45%",
    "💻 Yuklanmoqda... ██████░ 78%",
    "💻 TIZIM TAYYOR! 🖥️",
    "💻 WINDOWS YUKLANDI! 🪟",
    
    # 26. Telefon
    "📱 Zaryadlanmoqda... ██ 20%",
    "📱 Zaryadlanmoqda... ██████ 60%",
    "📱 Zaryadlanmoqda... ████████ 90%",
    "📱 BATAREYA TO'LA! 🔋",
    "📱 100% ZARYAD! ✅",
    
    # 27. O'rgimchak
    "🕷️ To'r to'qilmoqda... ██ 30%",
    "🕷️ To'r to'qilmoqda... ██████ 70%",
    "🕷️ To'r to'qilmoqda... ████████ 100% 🕸️",
    "🕷️ SPIDERMAN! 🦸",
    
    # 28. Olma
    "🍎 Yuklanmoqda... ██ 20%",
    "🍎 Yuklanmoqda... ██████ 60%",
    "🍎 Yuklanmoqda... ████████ 90%",
    "🍎 OLMA TAYYOR! 🥧",
    "🍎 DOCTOR KEEP AWAY! 👨‍⚕️",
    
    # 29. Rasm chizish
    "🎨 Rasm chizilmoqda... ██ 15%",
    "🎨 Rasm chizilmoqda... ██████ 55%",
    "🎨 Rasm chizilmoqda... ████████ 85%",
    "🎨 Rasm tayyor! 🖼️",
    "🎨 SAN'AT! ✨",
    
    # 30. Doiraviy spinner
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
    
    # 31. Yulduzlar
    "⭐ Yuklanmoqda... ☆",
    "⭐ Yuklanmoqda... ★",
    "⭐ Yuklanmoqda... ☆",
    "⭐ Yuklanmoqda... ★",
    "⭐ TAYYOR! ✨",
    "⭐ SUPERSTAR! 🌟",
    
    # 32. O'yin kubi
    "🎲 Tashlanmoqda... ⚀",
    "🎲 Tashlanmoqda... ⚁",
    "🎲 Tashlanmoqda... ⚂",
    "🎲 Tashlanmoqda... ⚃",
    "🎲 Tashlanmoqda... ⚄",
    "🎲 Tashlanmoqda... ⚅",
    "🎲 NATIJA: 6! 🎉",
    
    # 33. LED yozuv
    "🔴 Yuklanmoqda... 1%",
    "🟡 Yuklanmoqda... 25%",
    "🟢 Yuklanmoqda... 50%",
    "🔵 Yuklanmoqda... 75%",
    "🟣 Yuklanmoqda... 100% ✅",
    
    # 34. Mushuk
    "🐱 Yuklanmoqda... 😺",
    "🐱 Yuklanmoqda... 😸",
    "🐱 Yuklanmoqda... 😻",
    "🐱 MUSHUK TAYYOR! 🐈",
    "🐱 Nyaa~ 😽",
    
    # 35. It
    "🐶 Yuklanmoqda... 🐕",
    "🐶 Yuklanmoqda... 🐩",
    "🐶 Yuklanmoqda... 🐕‍🦺",
    "🐶 IT TAYYOR! 🦮",
    "🐶 WOOF WOOF! 🐾",
    
    # 36. Gullar
    "🌸 Yuklanmoqda... 🌺",
    "🌸 Yuklanmoqda... 🌻",
    "🌸 Yuklanmoqda... 🌹",
    "🌸 GULLAR TAYYOR! 🌷",
    "🌸 BOG' GULLADI! 🌼",
    
    # 37. Issiq ovqat
    "🍜 Yuklanmoqda... 🍲",
    "🍜 Yuklanmoqda... 🥘",
    "🍜 Yuklanmoqda... 🍛",
    "🍜 OVQAT TAYYOR! 🍽️",
    "🍜 BON APPETIT! 😋",
    
    # 38. Muzqaymoq
    "🍦 Yuklanmoqda... 🍧",
    "🍦 Yuklanmoqda... 🍨",
    "🍦 Yuklanmoqda... 🍦",
    "🍦 MUZQAYMOQ TAYYOR! 🍦",
    "🍦 YEYISHGA TAYYOR! 😋",
    
    # 39. Kino
    "🎥 Yuklanmoqda... 📽️",
    "🎥 Yuklanmoqda... 🎞️",
    "🎥 Yuklanmoqda... 🎬",
    "🎥 KINO TAYYOR! 🍿",
    "🎥 PREMYERA! 🌟",
]

# ========== BOT KOMANDALARI ==========

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "🎯 *Qiziqarli Yuklanish Animatsiyalari Botiga Xush Kelibsiz!*\n\n"
        "▶️ Yuklanishni boshlash uchun /load buyrug'ini yuboring.\n"
        "🔄 Har safar yangi va turli animatsiya ko'rasiz!\n\n"
        "🎭 *120+ turli animatsiya mavjud!*",
        parse_mode="Markdown"
    )

@dp.message(Command("load"))
async def load_animation(message: types.Message):
    msg = await message.answer("🎬 Yuklanish boshlanmoqda...")
    
    # 8 xil turli animatsiya ko'rsatish
    for _ in range(8):
        anim = random.choice(LOADING_ANIMATIONS)
        await asyncio.sleep(0.3 + random.uniform(0, 0.2))
        await msg.edit_text(f"🔄 {anim}")
    
    # Final tasodifiy xabarlar
    final_msgs = [
        "✅ *Yuklash tugallandi!*",
        "🎉 *Muvaffaqiyatli yakunlandi!*",
        "🌟 *Hamma narsa tayyor!*",
        "🔥 *Ish bajarildi!*",
        "💪 *Yuklash muvaffaqiyatli!*",
        "🚀 *Mukammal bajarildi!*",
        "✨ *Tayyor!*",
        "⚡ *Tez va sifatli!*"
    ]
    
    # Animatsiya turi haqida
    anim_types = [
        "Spinner", "Progress-bar", "Yurak", "Quyosh", "Raketa",
        "Poyga", "Qahva", "Pitsa", "Zombi", "Ninja",
        "Kosmonavt", "Robot", "Musiqa", "O'yin", "Kitob",
        "Film", "Sport", "Dengiz", "Poyezd", "Samolyot",
        "Baliq", "Baxt", "Kompyuter", "Telefon", "O'rgimchak",
        "Olma", "Rasm", "Yulduz", "Kub", "LED",
        "Mushuk", "It", "Gul", "Ovqat", "Muzqaymoq"
    ]
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yana bir marta", callback_data="reload")],
            [InlineKeyboardButton(text="📊 Animatsiya soni", callback_data="count")]
        ]
    )
    
    await msg.edit_text(
        f"{random.choice(final_msgs)}\n\n"
        f"🎭 *Animatsiya turi:* {random.choice(anim_types)}\n"
        f"📊 *Jami animatsiyalar:* {len(LOADING_ANIMATIONS)}+ ta\n\n"
        "🔄 Qayta boshlash uchun tugmani bosing.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "reload")
async def reload_callback(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer("🔄 Yangi yuklanish boshlanmoqda...")
    
    new_msg = await callback.message.answer("🎬 Yangi yuklanish...")
    
    # 8 xil animatsiya
    for _ in range(8):
        anim = random.choice(LOADING_ANIMATIONS)
        await asyncio.sleep(0.3 + random.uniform(0, 0.2))
        await new_msg.edit_text(f"🌀 {anim}")
    
    # Final xabar
    final_msgs = [
        "✅ *Yuklash tugallandi!*",
        "🎉 *Muvaffaqiyatli!*",
        "🌟 *Ajoyib!*",
        "🔥 *Zo'r!*",
        "💪 *Barakalla!*"
    ]
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yana bir marta", callback_data="reload")],
            [InlineKeyboardButton(text="📊 Animatsiya soni", callback_data="count")]
        ]
    )
    
    await new_msg.edit_text(
        f"{random.choice(final_msgs)}\n\n"
        f"🎭 *Har safar yangi animatsiya!*\n"
        f"📊 *Jami:* {len(LOADING_ANIMATIONS)} ta\n\n"
        "🔄 Qayta boshlash uchun tugmani bosing.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "count")
async def count_callback(callback: types.CallbackQuery):
    await callback.answer(
        f"📊 Jami {len(LOADING_ANIMATIONS)} ta animatsiya mavjud!",
        show_alert=True
    )

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(
        "📖 *Yordam:*\n\n"
        "/start - Botni ishga tushirish\n"
        "/load - Yuklanish animatsiyasini ko'rsatish\n"
        "/help - Yordam olish\n"
        "/stats - Animatsiyalar soni\n\n"
        "🔹 *Xususiyatlar:*\n"
        f"• {len(LOADING_ANIMATIONS)}+ turli animatsiya\n"
        "• Har safar tasodifiy animatsiya\n"
        "• Real vaqtda yangilanadi\n"
        "• Tugma orqali qayta yuklash",
        parse_mode="Markdown"
    )

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    await message.answer(
        f"📊 *Bot Statistikasi:*\n\n"
        f"🎭 *Animatsiyalar soni:* {len(LOADING_ANIMATIONS)}+ ta\n"
        f"🔄 *Har bir yuklash:* 8 ta animatsiya\n"
        f"🎨 *Turlari:* 35+ xil tur\n\n"
        f"🌟 *Eng yaxshi animatsiya:* {random.choice(LOADING_ANIMATIONS)[:30]}...",
        parse_mode="Markdown"
    )

# ========== BOT ISHGA TUSHIRISH ==========

async def main():
    print("=" * 40)
    print("🤖 BOT ISHGA TUSHMOQDA...")
    print(f"📊 {len(LOADING_ANIMATIONS)} TA ANIMATSIYA YUKLANDI")
    print("=" * 40)
    print("✅ Bot tayyor!")
    print("=" * 40)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
