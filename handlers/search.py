from aiogram.utils import markdown as md
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Task, TaskList, ProjectMember
from keyboards.inline import STATUS_EMOJI, PRIORITY_EMOJI
from states.forms import SearchForm

router = Router()


@router.message(F.text == "🔎 Поиск")
@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    await message.answer("Введи ключевое слово для поиска:")
    await state.set_state(SearchForm.waiting_query)


@router.message(SearchForm.waiting_query)
async def do_search(message: Message, state: FSMContext, db_user, session: AsyncSession):
    query = message.text.strip()
    await state.clear()

    if len(query) < 2:
        await message.answer("Запрос слишком короткий — минимум 2 символа.")
        return

    result = await session.execute(
        select(Task)
        .join(TaskList, Task.list_id == TaskList.id)
        .join(ProjectMember, TaskList.project_id == ProjectMember.project_id)
        .where(ProjectMember.user_id == db_user.id)
        .where(Task.title.ilike(f"%{query}%"))
        .order_by(Task.created_at.desc())
        .limit(15)
    )
    tasks = result.scalars().all()

    if not tasks:
        await message.answer(
            f"😶 По запросу <b>«{md.html.quote(query)}»</b> ничего не найдено.",
            parse_mode="HTML",
        )
        return

    lines = [f"🔎 <b>Результаты по «{md.html.quote(query)}»</b> ({len(tasks)}):\n"]
    for t in tasks:
        s = STATUS_EMOJI.get(t.status, "")
        p = PRIORITY_EMOJI.get(t.priority, "")
        due = f" · {t.due_date.strftime('%d.%m')}" if t.due_date else ""
        lines.append(f"{s}{p} {md.html.quote(t.title)}{due} — /task_{t.id}")

    await message.answer("\n".join(lines), parse_mode="HTML")
