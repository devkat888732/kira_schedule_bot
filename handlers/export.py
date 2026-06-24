import csv
import io
from aiogram.utils import markdown as md
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Task, TaskList, User
from db.repository import ProjectRepo, TaskRepo
from keyboards.inline import projects_kb
from states.forms import ExportForm

router = Router()


@router.message(F.text == "📥 Экспорт CSV")
@router.message(Command("export"))
async def cmd_export(message: Message, state: FSMContext, db_user, session: AsyncSession):
    projects = await ProjectRepo(session).get_user_projects(db_user.id)
    if not projects:
        await message.answer("Нет проектов для экспорта.")
        return
    await message.answer(
        "Выбери проект для экспорта в CSV:",
        reply_markup=projects_kb(projects, prefix="export_project"),
    )
    await state.set_state(ExportForm.waiting_project)


@router.callback_query(ExportForm.waiting_project, F.data.startswith("export_project:"))
async def do_export(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    project_id = int(call.data.split(":")[1])
    await state.clear()

    result = await session.execute(
        select(Task, User)
        .outerjoin(User, Task.assignee_id == User.id)
        .join(TaskList, Task.list_id == TaskList.id)
        .where(TaskList.project_id == project_id)
        .order_by(Task.status, Task.priority.desc())
    )
    rows = result.all()

    if not rows:
        await call.message.answer("В проекте нет задач для экспорта.")
        await call.answer()
        return

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Название", "Статус", "Приоритет", "Исполнитель", "Дедлайн", "Создана"])

    for task, assignee in rows:
        writer.writerow([
            task.id,
            task.title,
            task.status.value,
            task.priority.value,
            f"@{assignee.username}" if assignee and assignee.username else (assignee.full_name if assignee else "—"),
            task.due_date.strftime("%d.%m.%Y") if task.due_date else "—",
            task.created_at.strftime("%d.%m.%Y %H:%M"),
        ])

    # utf-8-sig чтобы Excel корректно открыл без настройки кодировки
    csv_bytes = output.getvalue().encode("utf-8-sig")
    file = BufferedInputFile(csv_bytes, filename=f"project_{project_id}_tasks.csv")

    await call.message.answer_document(
        file,
        caption=f"📥 <b>Экспорт задач проекта</b>\n{len(rows)} задач",
        parse_mode="HTML",
    )
    await call.answer()
