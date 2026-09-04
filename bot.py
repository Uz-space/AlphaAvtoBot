import asyncio
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputRichMessage, InputRichBlockParagraph, InputRichBlockSectionHeading,
    InputRichBlockTable, InputRichBlockPreformatted, InputRichBlockList,
    InputRichBlockListItem, RichTextBold,
)
from aiogram.types.rich_block_table_cell import RichBlockTableCell
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8609710969:AAGXxcahH3xRET51brLJCOdPVNl226e_co8"

# ─── Kran konfiguratsiyasi ───────────────────────────────────────────────────
CRANES = [
    {"name": "TronPick", "emoji": "🔴", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "LitePick", "emoji": "🌕", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "DogePick", "emoji": "🐕", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "PolPick",  "emoji": "🪙", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "BnbPick",  "emoji": "🟡", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "SolPick",  "emoji": "☀️", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "SuiPick",  "emoji": "💧", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "UsdPick",  "emoji": "💵", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "TonPick",  "emoji": "💎", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "BchPick",  "emoji": "🟤", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
]

API_STATE = {
    "connected": False,
    "domain": "sctg.xyz",
    "plan": "Trial",
    "accounts": 0,
    "total_claims": 0,
}

LIVE_LOG = {
    "crane_emoji": "",
    "crane_name": "",
    "log_text": "",
}

# ─── FSM States ──────────────────────────────────────────────────────────────
class AddAccount(StatesGroup):
    email    = State()
    password = State()
    cookies  = State()
    ua       = State()


# ─── Helpers ─────────────────────────────────────────────────────────────────
def get_crane(name: str):
    return next((c for c in CRANES if c["name"] == name), None)


def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_add")]
    ])


def skip_cookies_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_add")],
        [InlineKeyboardButton(text="⏭️ Skip Cookies", callback_data="skip_cookies")],
    ])


def skip_ua_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_add")],
        [InlineKeyboardButton(text="⏭️ Skip UA", callback_data="skip_ua")],
    ])


def format_countdown(seconds: float) -> str:
    """Format seconds to MM:SS"""
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def get_countdown(next_claim_at) -> str:
    """Calculate real-time countdown"""
    if not next_claim_at:
        return "--:--"
    
    remaining = (next_claim_at - datetime.now(timezone.utc)).total_seconds()
    if remaining <= 0:
        return "Ready"
    
    return format_countdown(remaining)


def add_log(crane: dict, text: str):
    crane.setdefault("logs", []).append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "text": text,
    })
    crane["logs"] = crane["logs"][-20:]


async def require_text(message: Message) -> str | None:
    if not message.text:
        await message.answer("⚠️ Please send plain text, not a photo/sticker/file.\n\n/cancel to abort.")
        return None
    return message.text.strip()


# ─── RICH TABLE - Asosiy dashboard ──────────────────────────────────────────
def build_main_rich_message() -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    # 3 ta ustun: ACCOUNT, NEXT CLAIM, BALANCE
    rows = [[
        cell("ACCOUNT", header=True),
        cell("NEXT CLAIM", header=True, align="center"),
        cell("BALANCE", header=True, align="right"),
    ]]

    for crane in CRANES:
        accounts = crane.get("accounts", [])
        
        if not accounts:
            # Akkaunt yo'q - faqat kran nomi
            rows.append([
                cell(crane['name']),
                cell("--:--", align="center"),
                cell("0.000000", align="right"),
            ])
        else:
            # Har bir akkaunt uchun alohida qator
            for acc in accounts:
                email = acc.get("email", "Unknown")
                balance = acc.get("balance", 0.0)
                
                # Real vaqtda countdown
                countdown = get_countdown(acc.get("next_claim_at"))
                
                rows.append([
                    cell(email),
                    cell(countdown, align="center"),
                    cell(f"{balance:.6f}", align="right"),
                ])

    table = InputRichBlockTable(cells=rows, is_bordered=True, is_striped=True)
    
    return InputRichMessage(blocks=[
        InputRichBlockParagraph(text=[RichTextBold(text="📊 TRX Stats Dashboard")]),
        table,
        InputRichBlockParagraph(text="💡 Tap a crane button below to manage accounts")
    ])


def build_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    
    for c in CRANES:
        icon = "🟢" if c["active"] else "⚠️"
        btn = InlineKeyboardButton(
            text=f"{icon} {c['name']}",
            callback_data=f"crane_{c['name']}"
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(text="🆘 Support", url="https://t.me/alphadevlab"),
    ])

    buttons.append([
        InlineKeyboardButton(text="⚙️ Settings", callback_data="settings"),
        InlineKeyboardButton(text="🔄", callback_data="refresh"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_crane_keyboard(crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Account", callback_data=f"add_account_{crane_name}")],
        [
            InlineKeyboardButton(text="🔄 Refresh", callback_data=f"crane_{crane_name}"),
            InlineKeyboardButton(text="◀️ Back", callback_data="back_main"),
        ],
    ])


def build_trx_stats_text(crane: dict) -> str:
    accounts = crane.get("accounts", [])
    
    if not accounts:
        return "No accounts yet."
    
    lines = []
    lines.append(f"{'Account':<15} {'Next Claim':<12} {'Balance':<15}")
    lines.append("-" * 42)
    
    for acc in accounts:
        email = acc.get("email", "Unknown")[:15]
        balance = acc.get("balance", 0.0)
        
        # Real vaqtda countdown
        countdown = get_countdown(acc.get("next_claim_at"))
            
        lines.append(f"{email:<15} {countdown:<12} {balance:<15.6f}")
    
    return "\n".join(lines)


def build_live_logs_rich_block(crane: dict) -> InputRichBlockPreformatted:
    logs = crane.get("logs", [])
    if not logs:
        body = "⏳ No claims yet..."
    else:
        body = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-8:])
    return InputRichBlockPreformatted(text=body)


def build_crane_rich_message(crane: dict) -> InputRichMessage:
    accounts = crane.get("accounts", [])
    acc_count = len(accounts)
    active_count = sum(1 for a in accounts if a.get("active", False))

    blocks = [
        InputRichBlockParagraph(text=[RichTextBold(text=f"{crane['emoji']} {crane['name']} - Control Panel")]),
        InputRichBlockParagraph(text=f"📊 {crane['claims']} claims | 💰 {crane['balance']}"),
        InputRichBlockSectionHeading(text=f"Active accounts ({active_count}/{acc_count})", size=4),
    ]

    if accounts:
        items = []
        for acc in accounts:
            status = "🟢" if acc.get("active") else "🔴"
            items.append(InputRichBlockListItem(blocks=[
                InputRichBlockParagraph(text=f"{status} {acc['label']} - {acc['email']}")
            ]))
        blocks.append(InputRichBlockList(items=items))
    else:
        blocks.append(InputRichBlockParagraph(text="No active accounts - tap + to add"))

    blocks.append(InputRichBlockSectionHeading(text="📊 TRX Stats", size=4))
    stats_text = build_trx_stats_text(crane)
    blocks.append(InputRichBlockPreformatted(text=stats_text))
    
    blocks.append(InputRichBlockSectionHeading(text="📡 Live Logs", size=4))
    blocks.append(build_live_logs_rich_block(crane))

    return InputRichMessage(blocks=blocks)


# ─── Bot va Dispatcher ───────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ─── /start ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer_rich(
        rich_message=build_main_rich_message(),
        reply_markup=build_keyboard()
    )


# ─── /cancel ─────────────────────────────────────────────────────────────────
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()
    await message.answer("❌ Cancelled.")
    if crane_name:
        crane = get_crane(crane_name)
        if crane:
            await message.answer_rich(
                rich_message=build_crane_rich_message(crane),
                reply_markup=build_crane_keyboard(crane_name),
            )


# ─── Refresh ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "refresh")
async def cb_refresh(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer_rich(
        rich_message=build_main_rich_message(),
        reply_markup=build_keyboard()
    )
    await call.answer("♻️ Updated!")


# ─── Back to main ────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.delete()
    await call.message.answer_rich(
        rich_message=build_main_rich_message(),
        reply_markup=build_keyboard()
    )
    await call.answer()


# ─── Crane panel ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("crane_"))
async def cb_crane(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("crane_", "")
    crane = get_crane(crane_name)
    if not crane:
        await call.answer("Not found!", show_alert=True)
        return
    await call.message.delete()
    await call.message.answer_rich(
        rich_message=build_crane_rich_message(crane),
        reply_markup=build_crane_keyboard(crane_name),
    )
    await call.answer()


# ─── Add Account: Step 1 — Email ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("add_account_", "")
    crane = get_crane(crane_name)
    if not crane:
        await call.answer("Not found!", show_alert=True)
        return

    acc_num = len(crane["accounts"]) + 1
    label = f"Account {acc_num}"

    await state.set_state(AddAccount.email)
    await state.update_data(crane_name=crane_name, label=label)

    await call.message.delete()
    await call.message.answer(
        text=(
            f"{crane['emoji']} Add Account - {crane_name}\n\n"
            f"Label: {label}\n\n"
            f"Send the account email:\n\n"
            f"/cancel to abort."
        ),
        reply_markup=cancel_keyboard(),
    )
    await call.answer()


# ─── Add Account: Step 2 — Password ──────────────────────────────────────────
@dp.message(AddAccount.email)
async def fsm_email(message: Message, state: FSMContext):
    email = await require_text(message)
    if email is None:
        return
    await state.update_data(email=email)
    await state.set_state(AddAccount.password)

    await message.answer(
        text=(
            f"Email: {email}\n\n"
            f"Now send the password:\n\n"
            f"/cancel to abort."
        ),
        reply_markup=cancel_keyboard(),
    )


# ─── Add Account: Step 3 — Cookies ───────────────────────────────────────────
@dp.message(AddAccount.password)
async def fsm_password(message: Message, state: FSMContext):
    password = await require_text(message)
    if password is None:
        return
    await state.update_data(password=password)
    await state.set_state(AddAccount.cookies)

    await message.answer(
        text=(
            f"Password: ✅\n\n"
            f"Cookies (optional - send cookies or tap Skip):\n\n"
            f"F12 > Console > document.cookie\n\n"
            f"/cancel to abort."
        ),
        reply_markup=skip_cookies_keyboard(),
    )


# ─── Skip Cookies ────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "skip_cookies")
async def cb_skip_cookies(call: CallbackQuery, state: FSMContext):
    await state.update_data(cookies=None)
    await state.set_state(AddAccount.ua)
    await call.message.edit_text(
        text=(
            f"Cookies: Skipped\n\n"
            f"User-Agent (optional - send UA or tap Skip):\n\n"
            f"F12 > Console > navigator.userAgent\n\n"
            f"/cancel to abort."
        ),
        reply_markup=skip_ua_keyboard(),
    )
    await call.answer()


# ─── Cookies kiritildi ────────────────────────────────────────────────────────
@dp.message(AddAccount.cookies)
async def fsm_cookies(message: Message, state: FSMContext):
    cookies = await require_text(message)
    if cookies is None:
        return
    chars = len(cookies)
    await state.update_data(cookies=cookies)
    await state.set_state(AddAccount.ua)

    await message.answer(
        text=(
            f"Cookies: ✅ ({chars} chars)\n\n"
            f"User-Agent (optional - send UA or tap Skip):\n\n"
            f"F12 > Console > navigator.userAgent\n\n"
            f"/cancel to abort."
        ),
        reply_markup=skip_ua_keyboard(),
    )


# ─── Skip UA ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "skip_ua")
async def cb_skip_ua(call: CallbackQuery, state: FSMContext):
    await state.update_data(ua=None)
    await _finish_add_account(call.message, state, via_callback=True)
    await call.answer()


# ─── UA kiritildi ────────────────────────────────────────────────────────────
@dp.message(AddAccount.ua)
async def fsm_ua(message: Message, state: FSMContext):
    ua = await require_text(message)
    if ua is None:
        return
    await state.update_data(ua=ua)
    await _finish_add_account(message, state, via_callback=False)


# ─── Finish: Account qo'shish ────────────────────────────────────────────────
async def _finish_add_account(message: Message, state: FSMContext, via_callback: bool):
    data = await state.get_data()
    crane_name = data["crane_name"]
    label = data["label"]
    email = data["email"]
    password = data["password"]
    cookies = data.get("cookies")
    ua = data.get("ua")

    crane = get_crane(crane_name)
    if crane is None:
        await state.clear()
        return

    # 60 daqiqa (3600 sekund) vaqt qo'yamiz
    next_claim_time = datetime.now(timezone.utc) + timedelta(minutes=60)

    new_acc = {
        "label": label,
        "email": email,
        "password": password,
        "cookies": cookies,
        "ua": ua,
        "active": True,
        "balance": 0.0,
        "next_claim_at": next_claim_time,
    }
    crane["accounts"].append(new_acc)
    crane["active"] = True

    add_log(crane, f"Connecting to {crane_name} Server...")
    add_log(crane, f"Account linked: {email}")

    cookies_icon = "✅" if cookies else "⏭️"
    ua_icon = "✅" if ua else "⏭️"

    summary = (
        f"Account added!\n\n"
        f"{crane['emoji']} {crane_name} #{len(crane['accounts'])}\n"
        f"Label: {label}\n"
        f"Email: {email}\n"
        f"Password: ✅\n"
        f"Cookies: {cookies_icon}\n"
        f"UA: {ua_icon}\n\n"
        f"⏱️ Next claim in: 60:00"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"◀️ Back to {crane_name}", callback_data=f"crane_{crane_name}")],
        [InlineKeyboardButton(text="🏠 Main Menu", callback_data="back_main")],
    ])

    await state.clear()
    await message.answer(text=summary, reply_markup=keyboard)


# ─── Cancel callback ─────────────────────────────────────────────────────────
@dp.callback_query(F.data == "cancel_add")
async def cb_cancel_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()

    crane = get_crane(crane_name)
    if crane:
        await call.message.delete()
        await call.message.answer_rich(
            rich_message=build_crane_rich_message(crane),
            reply_markup=build_crane_keyboard(crane_name),
        )
    else:
        await call.message.delete()
        await call.message.answer_rich(
            rich_message=build_main_rich_message(),
            reply_markup=build_keyboard()
        )
    await call.answer("❌ Cancelled.")


# ─── Settings ────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery):
    await call.answer("⚙️ Settings (coming soon...)", show_alert=False)


# ─── Startup ─────────────────────────────────────────────────────────────────
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
