import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
# Telegram'ning eng so'nggi Rich message va Table ob'ektlarini chaqiramiz
from aiogram.types import RichMessage, RichBlockTable, RichBlockTableRow, RichBlockTableCell

# Bot tokeningizni kiriting (@BotFather bergan token)
API_TOKEN = '8245157509:AAH-cL3k2upery-lPPkhIgGvNKVMwGAXXcc'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # 1. Skrinshotdagi kabi jadval kataklarini (cells) va qatorlarini tuzamiz
    table_rows = [
        # Sarlavha qatori
        RichBlockTableRow(cells=[
            RichBlockTableCell(text="Field", align="left", is_header=True),
            RichBlockTableCell(text="Details", align="left", is_header=True)
        ]),
        # Foydalanuvchi ma'lumoti
        RichBlockTableRow(cells=[
            RichBlockTableCell(text="User Id"),
            RichBlockTableCell(text="Sarah(25•••••019)")
        ]),
        # Summa qatori
        RichBlockTableRow(cells=[
            RichBlockTableCell(text="Amount"),
            RichBlockTableCell(text="0.001946 BTC ~\n$135.70")
        ]),
        # Hamyon manzili
        RichBlockTableRow(cells=[
            RichBlockTableCell(text="Receiver"),
            RichBlockTableCell(text="bc1qn0cnsnw3m8s4snwn821w1785ams3m10qutg66p")
        ]),
        # Transaksiya Hash ID raqami
        RichBlockTableRow(cells=[
            RichBlockTableCell(text="Hash ID"),
            RichBlockTableCell(text="f09c2bbd2cb...4643db0f77")
        ])
    ]

    # 2. RichBlockTable ob'ektini barcha konfiguratsiyalar bilan yig'amiz
    native_table = RichBlockTable(
        rows=table_rows,
        is_bordered=True,       # Kataklar atrofida ingichka tekis chiziqlar chiqarish
        is_striped=True,        # Qatorlarni och va to'q rang qilib navbatlashtirish
        caption="New Withdraw Success" # Jadval tepasidagi sarlavha matni
    )

    # 3. Tayyor jadval blokini RichMessage tarkibiga joylaymiz
    rich_payload = RichMessage(
        blocks=[native_table]
    )

    # 4. Oddiy sendMessage o'rniga yangi sendRichMessage metodi orqali yuboramiz
    await bot.send_rich_message(
        chat_id=message.chat.id,
        rich_message=rich_payload
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
