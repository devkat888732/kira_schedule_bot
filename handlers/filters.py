from aiogram.utils import markdown as md
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from db.repository import ProjectRepo, TaskRepo
from keyboards.inline import projects_kb, filter_kb, task_card_kb, STATUS_EMOJI, PRIORITY_EMOJI
from states.forms import FilterForm

router = Router()


@router.message(F.text == "🔍 Фильтр задач")
@router.message(Command("filter"))
async def cmd_filter(message: Message, state: FSMContext, db_user, session: AsyncSession):
    projects = await ProjectRepo(session).get_user_projects(db_user.id)
    if not projects:
        await message.answer("У тебя нет проектов.")
        return
    await message.answer(
        "Выбери проект для фильтрации:",
        reply_markup=projects_kb(projects, prefix="filter_project"),
    )
    await state.set_state(FilterForm.waiting_project)


@router.callback_query(FilterForm.waiting_project, F.data.startswith("filter_project:"))
async def filter_choose_project(call: CallbackQuery, state: FSMContext):
    project_id = int(call.data.split(":")[1])
    await state.update_data(project_id=project_id, filters={})
    hint = "Выбери фильтры (можно несколько) и нажми «✅ Применить». Повторный тап снимает фильтр."
    await call.message.answer(hint, reply_markup=filter_kb())
    await state.set_state(FilterForm.waiting_filters)
    await call.answer()


@router.callback_query(FilterForm.waiting_filters, F.data.startswith("filter_status:"))
async def filter_by_status(call: CallbackQuery, state: FSMContext):
    status = call.data.split(":")[1]
    data = await state.get_data()
    filters = data.get("filters", {})
    if filters.get("status") == status:
        filters.pop("status")  # снять если нажали повторно
    else:
        filters["status"] = status
    await state.update_data(filters=filters)
    await call.message.edit_reply_markup(reply_markup=filter_kb(active_filters=filters))
    await call.answer()


@router.callback_query(FilterForm.waiting_filters, F.data.startswith("filter_priority:"))
async def filter_by_priority(call: CallbackQuery, state: FSMContext):
    priority = call.data.split(":")[1]
    data = await state.get_data()
    filters = data.get("filters", {})
    if filters.get("priority") == priority:
        filters.pop("priority")
    else:
        filters["priority"] = priority
    await state.update_data(filters=filters)
    await call.message.edit_reply_markup(reply_markup=filter_kb(active_filters=filters))
    await call.answer()


@router.callback_query(FilterForm.waiting_filters, F.data == "filter_reset")
async def filter_reset(call: CallbackQuery, state: FSMContext):
    await state.update_data(filters={})
    await call.message.edit_reply_markup(reply_markup=filter_kb(active_filters={}))
    await call.answer("Фильтры сброшены")


@router.callback_query(FilterForm.waiting_filters, F.data == "filter_apply")
async def apply_filters(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    filters = data.get("filters", {})
    project_id = data["project_id"]
    await state.clear()

    tasks = await TaskRepo(session).get_filtered(project_id=project_id, filters=filters)

    if not tasks:
        await call.message.answer("😶 Задач по выбранным фильтрам не найдено.")
        await call.answer()
        return

    active = []
    if "status" in filters:
        active.append(f"статус: {filters['status']}")
    if "priority" in filters:
        active.append(f"приоритет: {filters['priority']}")
    filter_label = " · ".join(active) if active else "все"

    lines = [f"📋 <b>Найдено ({len(tasks)})</b> · {filter_label}\n"]
    for t in tasks[:20]:
        s = STATUS_EMOJI.get(t.status, "")
        p = PRIORITY_EMOJI.get(t.priority, "")
        due = f" · {t.due_date.strftime('%d.%m')}" if t.due_date else ""
        lines.append(f"{s}{p} {md.html.quote(t.title)}{due} — /task_{t.id}")
    if len(tasks) > 20:
        lines.append(f"\n…ещё {len(tasks) - 20} задач")

    await call.message.answer("\n".join(lines), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()
