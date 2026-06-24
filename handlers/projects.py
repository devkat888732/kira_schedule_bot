from aiogram.utils import markdown as md
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repository import ProjectRepo, TaskRepo
from db.models import TaskStatus
from keyboards.inline import projects_kb, task_card_kb, STATUS_EMOJI, PRIORITY_EMOJI
from states.forms import ProjectForm

router = Router()


@router.message(F.text == "📁 Проекты")
@router.message(Command("projects"))
async def show_projects(message: Message, db_user, session: AsyncSession):
    repo = ProjectRepo(session)
    projects = await repo.get_user_projects(db_user.id)
    if not projects:
        await message.answer(
            "У тебя пока нет проектов.\nСоздай первый! 👇",
            reply_markup=projects_kb([]),
        )
    else:
        await message.answer(
            f"📁 <b>Твои проекты</b> ({len(projects)}):",
            reply_markup=projects_kb(projects),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "project:new")
async def new_project_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Введи название нового проекта:")
    await state.set_state(ProjectForm.waiting_name)
    await call.answer()


@router.message(ProjectForm.waiting_name)
async def new_project_name(message: Message, state: FSMContext, db_user, session: AsyncSession):
    if len(message.text.strip()) < 2:
        await message.answer("Название слишком короткое. Попробуй ещё раз:")
        return
    # FIX S9: максимальная длина
    if len(message.text.strip()) > 128:
        await message.answer("Название слишком длинное (максимум 128 символов). Сократи:")
        return
    repo = ProjectRepo(session)
    project = await repo.create_project(name=message.text.strip(), owner_id=db_user.id)
    await state.clear()
    await message.answer(
        f"✅ Проект <b>{project.name}</b> создан!\n"
        f"ID: <code>{project.id}</code>",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("project:"))
async def open_project(call: CallbackQuery, session: AsyncSession):
    project_id_str = call.data.split(":")[1]
    if project_id_str == "new":
        return
    project_id = int(project_id_str)
    repo = ProjectRepo(session)
    project = await repo.get_by_id(project_id)
    if not project:
        await call.answer("Проект не найден.", show_alert=True)
        return

    tasks = await TaskRepo(session).get_project_tasks(project_id)

    lines = [f"📁 <b>{md.html.quote(project.name)}</b>\n"]
    if not tasks:
        lines.append("Задач пока нет.")
    else:
        for t in tasks[:10]:
            s = STATUS_EMOJI.get(t.status, "")
            p = PRIORITY_EMOJI.get(t.priority, "")
            due = f" · {t.due_date.strftime('%d.%m')}" if t.due_date else ""
            lines.append(f"{s}{p} {md.html.quote(t.title)}{due} — /task_{t.id}")
        if len(tasks) > 10:
            lines.append(f"\n…ещё {len(tasks) - 10} задач")

    await call.message.answer("\n".join(lines), parse_mode="HTML")
    await call.answer()
