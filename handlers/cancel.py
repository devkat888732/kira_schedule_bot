from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from keyboards.main_menu import main_menu

router = Router()


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    await state.clear()
    if current is None:
        await message.answer(
            "Нет активного действия.",
            reply_markup=main_menu(),
        )
    else:
        await message.answer(
            "❌ Действие отменено.",
            reply_markup=main_menu(),
        )
