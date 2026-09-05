import asyncio
import logging
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ButtonStyle
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
    {"name": "TronPick", "emoji": "", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "LitePick", "emoji": "", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
    {"name": "DogePick", "emoji": "", "active": False, "multiplier": None, "claims": 0, "max_claims": "∞", "balance": 0, "accounts": [], "logs": []},
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

# ─── Har bir kran uchun timer start vaqti ──────────────────────────────────
CRANE_TIMERS = {}

def get_crane_timer(crane_name: str):
    """Kran uchun timer vaqtini oladi yoki yangi yaratadi"""
    if crane_name not in CRANE_TIMERS:
        CRANE_TIMERS[crane_name] = datetime.now(timezone.utc)
    return CRANE_TIMERS[crane_name]

# ─── FSM States ──────────────────────────────────────────────────────────────
class AddAccount(StatesGroup):
    email    = State()
    password = State()


class SettingsFSM(StatesGroup):
    api_key = State()


# ─── Settings ma'lumotlari (foydalanuvchi bo'yicha) ─────────────────────────
USER_SETTINGS = {}  # chat_id -> {"api_key": str|None, "language": "uz_latin"|"uz_cyrillic"}

LANGUAGES = {
    "uz_latin": "🇺🇿 O'zbekcha (lotin)",
    "uz_cyrillic": "🇺🇿 Ўзбекча (кирилл)",
}


def get_user_settings(chat_id: int) -> dict:
    return USER_SETTINGS.setdefault(chat_id, {"api_key": None, "language": "uz_latin"})


# ─── TARJIMALAR ──────────────────────────────────────────────────────────────
TEXTS = {
    "uz_latin": {
        "dashboard_title": "ALPHA",
        "motivation_text": "🚀 Har bir qadam katta yutuqqa boshlaydi — sabr va izchillik bilan davom eting, natija albatta keladi!",
        "col_account": "Akkauntlar",
        "col_next_claim": "Keyingi olish",
        "col_balance": "Balanslari",

        "btn_settings": "⚙️ Sozlamalar",
        "btn_refresh": "🔄 Yangilash",
        "btn_add_account": "➕ Akkaunt qo'shish",
        "btn_back": "◀️ Orqaga",
        "btn_cancel": "❌ Bekor qilish",
        "btn_api_key": "🔑 API Kalit",
        "btn_language": "🌐 Til",
        "btn_support": "🆘 Yordam",
        "btn_main_menu": "🏠 Bosh menyu",
        "btn_back_to_crane": "◀️ {crane}ga qaytish",

        "not_found": "Topilmadi!",
        "updated": "♻️ Yangilandi!",
        "cancelled": "❌ Bekor qilindi.",
        "plain_text_warning": "⚠️ Iltimos, oddiy matn yuboring, rasm/stiker/fayl emas.\n\n/cancel — bekor qilish uchun.",

        "crane_control_panel": "{emoji} {name} - Boshqaruv paneli",
        "crane_claims_balance": "📊 {claims} ta olish | 💰 {balance}",
        "crane_active_accounts": "Faol akkauntlar ({active}/{total})",
        "crane_no_accounts": "Faol akkaunt yo'q - qo'shish uchun + bosing",
        "crane_trx_stats_heading": "📊 TRX Statistikasi",
        "crane_live_logs_heading": "📡 Jonli loglar",
        "crane_no_claims_yet": "⏳ Hali olishlar yo'q...",

        "stats_col_account": "Akkaunt",
        "stats_col_next_claim": "Keyingi olish",
        "stats_col_balance": "Balans",

        "add_account_title": "{emoji} Akkaunt qo'shish - {crane}",
        "field_label": "Belgi: {label}",
        "add_account_send_email": "Akkaunt emailini yuboring:",
        "email_line": "Email: {email}",
        "send_password": "Endi parolni yuboring:",
        "password_line": "Parol: ✅",
        "cancel_hint": "/cancel — bekor qilish uchun.",

        "account_added": "Akkaunt qo'shildi!",
        "next_claim_in": "⏱️ Keyingi olish: 60:00",

        "settings_title": "⚙️ Sozlamalar",
        "settings_api_key_line": "🔑 API Kalit: {status}",
        "settings_language_line": "🌐 Til: {lang}",
        "api_key_set": "✅ O'rnatilgan",
        "api_key_not_set": "❌ O'rnatilmagan",
        "send_api_key": "🔑 API kalitingizni yuboring:",
        "api_key_saved": "✅ API Kalit saqlandi!",
        "choose_language": "🌐 Tilni tanlang:",
    },
    "uz_cyrillic": {
        "dashboard_title": "ALPHA",
        "motivation_text": "🚀 Ҳар бир қадам катта ютуққа бошлайди — сабр ва изчиллик билан давом этинг, натижа албатта келади!",
        "col_account": "Аккаунтлар",
        "col_next_claim": "Кейинги олиш",
        "col_balance": "Баланслари",

        "btn_settings": "⚙️ Созламалар",
        "btn_refresh": "🔄 Янгилаш",
        "btn_add_account": "➕ Аккаунт қўшиш",
        "btn_back": "◀️ Орқага",
        "btn_cancel": "❌ Бекор қилиш",
        "btn_api_key": "🔑 API Калит",
        "btn_language": "🌐 Тил",
        "btn_support": "🆘 Ёрдам",
        "btn_main_menu": "🏠 Бош меню",
        "btn_back_to_crane": "◀️ {crane}га қайтиш",

        "not_found": "Топилмади!",
        "updated": "♻️ Янгиланди!",
        "cancelled": "❌ Бекор қилинди.",
        "plain_text_warning": "⚠️ Илтимос, оддий матн юборинг, расм/стикер/файл эмас.\n\n/cancel — бекор қилиш учун.",

        "crane_control_panel": "{emoji} {name} - Бошқарув панели",
        "crane_claims_balance": "📊 {claims} та олиш | 💰 {balance}",
        "crane_active_accounts": "Фаол аккаунтлар ({active}/{total})",
        "crane_no_accounts": "Фаол аккаунт йўқ - қўшиш учун + босинг",
        "crane_trx_stats_heading": "📊 TRX Статистикаси",
        "crane_live_logs_heading": "📡 Жонли логлар",
        "crane_no_claims_yet": "⏳ Ҳали олишлар йўқ...",

        "stats_col_account": "Аккаунт",
        "stats_col_next_claim": "Кейинги олиш",
        "stats_col_balance": "Баланс",

        "add_account_title": "{emoji} Аккаунт қўшиш - {crane}",
        "field_label": "Белги: {label}",
        "add_account_send_email": "Аккаунт email'ини юборинг:",
        "email_line": "Email: {email}",
        "send_password": "Энди паролни юборинг:",
        "password_line": "Парол: ✅",
        "cancel_hint": "/cancel — бекор қилиш учун.",

        "account_added": "Аккаунт қўшилди!",
        "next_claim_in": "⏱️ Кейинги олиш: 60:00",

        "settings_title": "⚙️ Созламалар",
        "settings_api_key_line": "🔑 API Калит: {status}",
        "settings_language_line": "🌐 Тил: {lang}",
        "api_key_set": "✅ Ўрнатилган",
        "api_key_not_set": "❌ Ўрнатилмаган",
        "send_api_key": "🔑 API калитингизни юборинг:",
        "api_key_saved": "✅ API Калит сақланди!",
        "choose_language": "🌐 Тилни танланг:",
    },
}


def t(chat_id: int, key: str, **kwargs) -> str:
    """Foydalanuvchi tiliga qarab tarjima matnini qaytaradi."""
    lang = get_user_settings(chat_id).get("language", "uz_latin")
    table = TEXTS.get(lang, TEXTS["uz_latin"])
    template = table.get(key, TEXTS["uz_latin"].get(key, key))
    return template.format(**kwargs) if kwargs else template


# ─── Helpers ─────────────────────────────────────────────────────────────────
def get_crane(name: str):
    return next((c for c in CRANES if c["name"] == name), None)


def cancel_keyboard(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_add")]
    ])


def format_countdown(seconds: float) -> str:
    """Format seconds to MM:SS"""
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


def get_countdown(timer_start: datetime) -> str:
    """Timer start vaqtidan boshlab 60 daqiqa sanaydi"""
    elapsed = (datetime.now(timezone.utc) - timer_start).total_seconds()
    remaining = max(0, 60 * 60 - elapsed)  # 60 daqiqa = 3600 sekund
    return format_countdown(remaining)


def get_account_countdown(next_claim_at) -> str:
    """Account timer - akkaunt qo'shilgan vaqtdan boshlab sanaydi"""
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
        await message.answer(t(message.chat.id, "plain_text_warning"))
        return None
    return message.text.strip()


# ─── RICH TABLE - Asosiy dashboard ──────────────────────────────────────────
def build_main_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left", colspan: int | None = None) -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header, colspan=colspan)

    # ALPHA - alohida, mustaqil jadval
    alpha_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "dashboard_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )

    # Sarlavha qatori - 3 ustun: Akkauntlar / Keyingi olish / Balanslari
    header_row = [
        cell(t(chat_id, "col_account"), header=True),
        cell(t(chat_id, "col_next_claim"), header=True, align="center"),
        cell(t(chat_id, "col_balance"), header=True, align="right"),
    ]

    data_rows = []
    for crane in CRANES:
        accounts = crane.get("accounts", [])
        crane_timer = get_crane_timer(crane['name'])

        if not accounts:
            data_rows.append([
                cell(crane['name']),
                cell(get_countdown(crane_timer), align="center"),
                cell("0.000000", align="right"),
            ])
        else:
            for acc in accounts:
                email = acc.get("email", "Unknown")
                balance = acc.get("balance", 0.0)
                countdown = get_account_countdown(acc.get("next_claim_at"))
                data_rows.append([
                    cell(email),
                    cell(countdown, align="center"),
                    cell(f"{balance:.6f}", align="right"),
                ])

    data_table = InputRichBlockTable(
        cells=[header_row, *data_rows],
        is_bordered=True,
        is_striped=True,
    )

    # Motivatsion matn - alohida, mustaqil jadval
    motivation_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "motivation_text"), align="center")]],
        is_bordered=True,
        is_striped=True,
    )

    return InputRichMessage(blocks=[
        alpha_table,
        data_table,
        motivation_table,
    ])


def build_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Asosiy menyu (dashboard) klaviaturasi.
    - Barcha pick tugmalari (TronPick, DogePick, ...): ko'k (primary)
    - Settings va Refresh: yashil (success)
    """
    buttons = []
    row = []

    for c in CRANES:
        btn = InlineKeyboardButton(
            text=f"{c['name']}",
            callback_data=f"crane_{c['name']}",
            style=ButtonStyle.PRIMARY,
        )
        row.append(btn)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton(
            text=t(chat_id, "btn_support"),
            url="https://t.me/alphadevlab",
            style=ButtonStyle.DANGER,
        ),
    ])

    buttons.append([
        InlineKeyboardButton(
            text=t(chat_id, "btn_settings"),
            callback_data="settings",
            style=ButtonStyle.SUCCESS,
        ),
        InlineKeyboardButton(
            text=t(chat_id, "btn_refresh"),
            callback_data="refresh",
            style=ButtonStyle.SUCCESS,
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_settings_rich_message(chat_id: int) -> InputRichMessage:
    def cell(text: str, header: bool = False, align: str = "left") -> RichBlockTableCell:
        return RichBlockTableCell(align=align, valign="middle", text=text, is_header=header)

    s = get_user_settings(chat_id)
    api_status = t(chat_id, "api_key_set") if s.get("api_key") else t(chat_id, "api_key_not_set")
    lang_name = LANGUAGES.get(s.get("language", "uz_latin"), s.get("language"))

    # Sarlavha - alohida, mustaqil jadval (ALPHA uslubida)
    title_table = InputRichBlockTable(
        cells=[[cell(t(chat_id, "settings_title"), header=True, align="center")]],
        is_bordered=True,
        is_striped=True,
    )

    # Ma'lumotlar - alohida jadval
    info_table = InputRichBlockTable(
        cells=[
            [cell(t(chat_id, "settings_api_key_line", status=api_status))],
            [cell(t(chat_id, "settings_language_line", lang=lang_name))],
        ],
        is_bordered=True,
        is_striped=True,
    )

    return InputRichMessage(blocks=[
        title_table,
        info_table,
    ])


def build_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    api_key_set = bool(get_user_settings(chat_id).get("api_key"))
    api_key_style = ButtonStyle.SUCCESS if api_key_set else ButtonStyle.DANGER
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_api_key"), callback_data="settings_api_key", style=api_key_style)],
        [InlineKeyboardButton(text=t(chat_id, "btn_language"), callback_data="settings_language", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_back"), callback_data="back_main", style=ButtonStyle.SUCCESS)],
    ])


def build_language_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text=name, callback_data=f"lang_{code}")] for code, name in LANGUAGES.items()]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_cancel_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_cancel"), callback_data="cancel_settings")]
    ])


def build_crane_keyboard(chat_id: int, crane_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_add_account"), callback_data=f"add_account_{crane_name}", style=ButtonStyle.DANGER)],
        [
            InlineKeyboardButton(text=t(chat_id, "btn_refresh"), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS),
            InlineKeyboardButton(text=t(chat_id, "btn_back"), callback_data="back_main", style=ButtonStyle.SUCCESS),
        ],
    ])


def build_trx_stats_text(chat_id: int, crane: dict) -> str:
    accounts = crane.get("accounts", [])

    col_account = t(chat_id, "stats_col_account")
    col_next = t(chat_id, "stats_col_next_claim")
    col_balance = t(chat_id, "stats_col_balance")

    lines = []
    lines.append(f"{col_account:<15} {col_next:<12} {col_balance:<15}")
    lines.append("-" * 42)

    if not accounts:
        # Akkaunt yo'q - kran timeri
        crane_timer = get_crane_timer(crane['name'])
        lines.append(f"{crane['name']:<15} {get_countdown(crane_timer):<12} {'0.000000':<15}")
    else:
        for acc in accounts:
            email = acc.get("email", "Unknown")[:15]
            balance = acc.get("balance", 0.0)

            countdown = get_account_countdown(acc.get("next_claim_at"))

            lines.append(f"{email:<15} {countdown:<12} {balance:<15.6f}")

    return "\n".join(lines)


def build_live_logs_rich_block(chat_id: int, crane: dict) -> InputRichBlockPreformatted:
    logs = crane.get("logs", [])
    if not logs:
        body = t(chat_id, "crane_no_claims_yet")
    else:
        body = "\n".join(f"[{e['time']}] {e['text']}" for e in logs[-8:])
    return InputRichBlockPreformatted(text=body)


def build_crane_rich_message(chat_id: int, crane: dict) -> InputRichMessage:
    accounts = crane.get("accounts", [])
    acc_count = len(accounts)
    active_count = sum(1 for a in accounts if a.get("active", False))

    blocks = [
        InputRichBlockParagraph(text=[RichTextBold(text=t(chat_id, "crane_control_panel", emoji=crane['emoji'], name=crane['name']).strip())]),
        InputRichBlockParagraph(text=t(chat_id, "crane_claims_balance", claims=crane['claims'], balance=crane['balance'])),
        InputRichBlockSectionHeading(text=t(chat_id, "crane_active_accounts", active=active_count, total=acc_count), size=4),
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
        blocks.append(InputRichBlockParagraph(text=t(chat_id, "crane_no_accounts")))

    blocks.append(InputRichBlockSectionHeading(text=t(chat_id, "crane_trx_stats_heading"), size=4))
    stats_text = build_trx_stats_text(chat_id, crane)
    blocks.append(InputRichBlockPreformatted(text=stats_text))

    blocks.append(InputRichBlockSectionHeading(text=t(chat_id, "crane_live_logs_heading"), size=4))
    blocks.append(build_live_logs_rich_block(chat_id, crane))

    return InputRichMessage(blocks=blocks)


# ─── Bot va Dispatcher ───────────────────────────────────────────────────────
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ─── Xabarlarni saqlash uchun ──────────────────────────────────────────────
main_messages = {}  # chat_id -> message_id


# ─── Auto refresh timer ─────────────────────────────────────────────────────
async def auto_refresh():
    """Har 1 sekundda avtomatik yangilaydi"""
    while True:
        await asyncio.sleep(1)
        try:
            # Barcha active xabarlarni yangilash
            for chat_id, message_id in list(main_messages.items()):
                try:
                    # Rich message ni edit qilish
                    await bot.edit_message_rich(
                        chat_id=chat_id,
                        message_id=message_id,
                        rich_message=build_main_rich_message(chat_id),
                        reply_markup=build_keyboard(chat_id)
                    )
                except Exception as e:
                    # Agar xabar o'chirilgan bo'lsa, ro'yxatdan o'chiramiz
                    if "message to edit not found" in str(e) or "message is not modified" in str(e):
                        if chat_id in main_messages:
                            del main_messages[chat_id]
                    pass
        except Exception as e:
            logging.error(f"Auto refresh error: {e}")


# ─── /start ──────────────────────────────────────────────────────────────────
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    msg = await message.answer_rich(
        rich_message=build_main_rich_message(message.chat.id),
        reply_markup=build_keyboard(message.chat.id)
    )
    # Xabarni ro'yxatga qo'shamiz
    main_messages[message.chat.id] = msg.message_id


# ─── /cancel ─────────────────────────────────────────────────────────────────
@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()
    await message.answer(t(message.chat.id, "cancelled"))
    if current_state and current_state.startswith("SettingsFSM"):
        await message.answer_rich(
            rich_message=build_settings_rich_message(message.chat.id),
            reply_markup=build_settings_keyboard(message.chat.id),
        )
    elif crane_name:
        crane = get_crane(crane_name)
        if crane:
            await message.answer_rich(
                rich_message=build_crane_rich_message(message.chat.id, crane),
                reply_markup=build_crane_keyboard(message.chat.id, crane_name),
            )


# ─── Refresh ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "refresh")
async def cb_refresh(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.delete()
    except:
        pass
    msg = await call.message.answer_rich(
        rich_message=build_main_rich_message(call.message.chat.id),
        reply_markup=build_keyboard(call.message.chat.id)
    )
    # Xabarni ro'yxatga yangilaymiz
    main_messages[call.message.chat.id] = msg.message_id
    await call.answer(t(call.message.chat.id, "updated"))


# ─── Back to main ────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.delete()
    except:
        pass
    msg = await call.message.answer_rich(
        rich_message=build_main_rich_message(call.message.chat.id),
        reply_markup=build_keyboard(call.message.chat.id)
    )
    # Xabarni ro'yxatga yangilaymiz
    main_messages[call.message.chat.id] = msg.message_id
    await call.answer()


# ─── Crane panel ─────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("crane_"))
async def cb_crane(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("crane_", "")
    crane = get_crane(crane_name)
    if not crane:
        await call.answer(t(call.message.chat.id, "not_found"), show_alert=True)
        return
    await call.message.delete()
    # Crane panelga o'tganda main xabarni ro'yxatdan o'chiramiz
    if call.message.chat.id in main_messages:
        del main_messages[call.message.chat.id]
    await call.message.answer_rich(
        rich_message=build_crane_rich_message(call.message.chat.id, crane),
        reply_markup=build_crane_keyboard(call.message.chat.id, crane_name),
    )
    await call.answer()


# ─── Add Account: Step 1 — Email ─────────────────────────────────────────────
@dp.callback_query(F.data.startswith("add_account_"))
async def cb_add_account(call: CallbackQuery, state: FSMContext):
    crane_name = call.data.replace("add_account_", "")
    crane = get_crane(crane_name)
    if not crane:
        await call.answer(t(call.message.chat.id, "not_found"), show_alert=True)
        return

    acc_num = len(crane["accounts"]) + 1
    label = f"Account {acc_num}"

    await state.set_state(AddAccount.email)
    await state.update_data(crane_name=crane_name, label=label)

    chat_id = call.message.chat.id
    await call.message.delete()
    await call.message.answer(
        text=(
            f"{t(chat_id, 'add_account_title', emoji=crane['emoji'], crane=crane_name).strip()}\n\n"
            f"{t(chat_id, 'field_label', label=label)}\n\n"
            f"{t(chat_id, 'add_account_send_email')}\n\n"
            f"{t(chat_id, 'cancel_hint')}"
        ),
        reply_markup=cancel_keyboard(chat_id),
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

    chat_id = message.chat.id
    await message.answer(
        text=(
            f"{t(chat_id, 'email_line', email=email)}\n\n"
            f"{t(chat_id, 'send_password')}\n\n"
            f"{t(chat_id, 'cancel_hint')}"
        ),
        reply_markup=cancel_keyboard(chat_id),
    )


# ─── Add Account: Step 2 tugagach — yakunlash ────────────────────────────────
@dp.message(AddAccount.password)
async def fsm_password(message: Message, state: FSMContext):
    password = await require_text(message)
    if password is None:
        return
    await state.update_data(password=password)
    await _finish_add_account(message, state, via_callback=False)


# ─── Finish: Account qo'shish ────────────────────────────────────────────────
async def _finish_add_account(message: Message, state: FSMContext, via_callback: bool):
    data = await state.get_data()
    crane_name = data["crane_name"]
    label = data["label"]
    email = data["email"]
    password = data["password"]

    crane = get_crane(crane_name)
    if crane is None:
        await state.clear()
        return

    # Akkaunt uchun 60 daqiqa vaqt
    next_claim_time = datetime.now(timezone.utc) + timedelta(minutes=60)

    new_acc = {
        "label": label,
        "email": email,
        "password": password,
        "active": True,
        "balance": 0.0,
        "next_claim_at": next_claim_time,
    }
    crane["accounts"].append(new_acc)
    crane["active"] = True

    add_log(crane, f"Connecting to {crane_name} Server...")
    add_log(crane, f"Account linked: {email}")

    chat_id = message.chat.id
    crane_line = f"{crane['emoji']} {crane_name} #{len(crane['accounts'])}".strip()
    summary = (
        f"{t(chat_id, 'account_added')}\n\n"
        f"{crane_line}\n"
        f"{t(chat_id, 'field_label', label=label)}\n"
        f"{t(chat_id, 'email_line', email=email)}\n"
        f"{t(chat_id, 'password_line')}\n\n"
        f"{t(chat_id, 'next_claim_in')}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(chat_id, "btn_back_to_crane", crane=crane_name), callback_data=f"crane_{crane_name}", style=ButtonStyle.SUCCESS)],
        [InlineKeyboardButton(text=t(chat_id, "btn_main_menu"), callback_data="back_main")],
    ])

    await state.clear()
    await message.answer(text=summary, reply_markup=keyboard)


# ─── Cancel callback ─────────────────────────────────────────────────────────
@dp.callback_query(F.data == "cancel_add")
async def cb_cancel_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    crane_name = data.get("crane_name", "")
    await state.clear()

    chat_id = call.message.chat.id
    crane = get_crane(crane_name)
    if crane:
        await call.message.delete()
        await call.message.answer_rich(
            rich_message=build_crane_rich_message(chat_id, crane),
            reply_markup=build_crane_keyboard(chat_id, crane_name),
        )
    else:
        await call.message.delete()
        msg = await call.message.answer_rich(
            rich_message=build_main_rich_message(chat_id),
            reply_markup=build_keyboard(chat_id)
        )
        main_messages[chat_id] = msg.message_id
    await call.answer(t(chat_id, "cancelled"))


# ─── Settings: asosiy menyu ──────────────────────────────────────────────────
@dp.callback_query(F.data == "settings")
async def cb_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await call.message.delete()
    except:
        pass
    if call.message.chat.id in main_messages:
        del main_messages[call.message.chat.id]
    await call.message.answer_rich(
        rich_message=build_settings_rich_message(call.message.chat.id),
        reply_markup=build_settings_keyboard(call.message.chat.id),
    )
    await call.answer()


# ─── Settings: API Key so'rash ───────────────────────────────────────────────
@dp.callback_query(F.data == "settings_api_key")
async def cb_settings_api_key(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsFSM.api_key)
    chat_id = call.message.chat.id
    await call.message.delete()
    await call.message.answer(
        text=(
            f"{t(chat_id, 'send_api_key')}\n\n"
            f"{t(chat_id, 'cancel_hint')}"
        ),
        reply_markup=settings_cancel_keyboard(chat_id),
    )
    await call.answer()


@dp.message(SettingsFSM.api_key)
async def fsm_api_key(message: Message, state: FSMContext):
    api_key = await require_text(message)
    if api_key is None:
        return
    settings = get_user_settings(message.chat.id)
    settings["api_key"] = api_key
    await state.clear()
    chat_id = message.chat.id
    await message.answer_rich(
        rich_message=build_settings_rich_message(chat_id),
        reply_markup=build_settings_keyboard(chat_id),
    )


# ─── Settings: Language tanlash ──────────────────────────────────────────────
@dp.callback_query(F.data == "settings_language")
async def cb_settings_language(call: CallbackQuery):
    chat_id = call.message.chat.id
    await call.message.edit_text(
        text=t(chat_id, "choose_language"),
        reply_markup=build_language_keyboard(chat_id),
    )
    await call.answer()


@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang_select(call: CallbackQuery):
    code = call.data.replace("lang_", "")
    chat_id = call.message.chat.id
    if code not in LANGUAGES:
        await call.answer(t(chat_id, "not_found"), show_alert=True)
        return
    settings = get_user_settings(chat_id)
    settings["language"] = code
    await call.message.delete()
    await call.message.answer_rich(
        rich_message=build_settings_rich_message(chat_id),
        reply_markup=build_settings_keyboard(chat_id),
    )
    await call.answer(f"✅ {LANGUAGES[code]}")


# ─── Settings: API Key kiritishni bekor qilish ──────────────────────────────
@dp.callback_query(F.data == "cancel_settings")
async def cb_cancel_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = call.message.chat.id
    await call.message.delete()
    await call.message.answer_rich(
        rich_message=build_settings_rich_message(chat_id),
        reply_markup=build_settings_keyboard(chat_id),
    )
    await call.answer(t(chat_id, "cancelled"))


# ─── Startup ─────────────────────────────────────────────────────────────────
async def main():
    # Auto refreshni ishga tushiramiz
    asyncio.create_task(auto_refresh())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
