from aiogram.utils import markdown as md
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from db.repository import TaskRepo
from db.models import TaskStatus
from keyboards.inline import STATUS_EMOJI, PRIORITY_EMOJI, task_card_kb

router = Router()

STATUS_LABELS = {
    TaskStatus.TODO: "⬜ To Do",
    TaskStatus.IN_PROGRESS: "🔄 In Progress",
    TaskStatus.REVIEW: "👀 Review",
    TaskStatus.DONE: "✅ Done",
}


@router.message(F.text == "✅ Мои задачи")
@router.message(Command("tasks"))
async def my_tasks(message: Message, db_user, session: AsyncSession):
    repo = TaskRepo(session)
    tasks = await repo.get_user_tasks(db_user.id)

    if not tasks:
        await message.answer("У тебя пока нет задач. Создай первую через «➕ Создать задачу»!")
        return

    # Группируем по статусу
    grouped: dict[TaskStatus, list] = {}
    for t in tasks:
        grouped.setdefault(t.status, []).append(t)

    lines = [f"📋 <b>Мои задачи</b> ({len(tasks)})\n"]
    for status in TaskStatus:
        bucket = grouped.get(status, [])
        if not bucket:
            continue
        lines.append(f"\n{STATUS_LABELS[status]} ({len(bucket)})")
        for t in bucket:
            p = PRIORITY_EMOJI.get(t.priority, "")
            due = f" · {t.due_date.strftime('%d.%m')}" if t.due_date else ""
            lines.append(f"  {p} {md.html.quote(t.title)}{due} — /task_{t.id}")

    await message.answer("\n".join(lines), parse_mode="HTML")
