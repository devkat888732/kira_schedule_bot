from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from keyboards.main_menu import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "Это твой личный таск-менеджер в Telegram.\n"
        "Выбери действие:",
        reply_markup=main_menu(),
        parse_mode="HTML",
    )
