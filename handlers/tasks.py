from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils import markdown as md
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.repository import ProjectRepo, TaskRepo, MemberRepo
from db.models import NEXT_STATUS, TaskStatus, TaskList, MemberRole, User
from keyboards.inline import (
    projects_kb, priorities_kb, reminder_kb,
    task_card_kb, confirm_delete_kb, skip_kb, assignee_kb,
    STATUS_EMOJI, PRIORITY_EMOJI,
)
from states.forms import TaskForm, ReassignForm
from utils.permissions import check_permission

router = Router()


# ── Вспомогательные функции ───────────────────────────────────────────────────

async def _get_task_list(session: AsyncSession, list_id: int) -> TaskList | None:
    result = await session.execute(select(TaskList).where(TaskList.id == list_id))
    return result.scalar_one_or_none()


async def _check_task_access(
    session: AsyncSession, db_user, task, required: MemberRole = MemberRole.OBSERVER
) -> bool:
    task_list = await _get_task_list(session, task.list_id)
    if not task_list:
        return False
    return await check_permission(session, db_user.id, task_list.project_id, required)


async def _task_card_text(session: AsyncSession, task) -> str:
    assignee = task.assignee
    if assignee is None and task.assignee_id:
        result = await session.execute(select(User).where(User.id == task.assignee_id))
        assignee = result.scalar_one_or_none()

    s = STATUS_EMOJI.get(task.status, "")
    p = PRIORITY_EMOJI.get(task.priority, "")
    title = md.html.quote(task.title)
    due = f"\n📅 Дедлайн: {task.due_date.strftime('%d.%m.%Y')}" if task.due_date else ""
    desc = f"\n📝 {md.html.quote(task.description)}" if task.description else ""
    assignee_text = ""
    if assignee:
        name = f"@{assignee.username}" if assignee.username else md.html.quote(assignee.full_name)
        assignee_text = f"\n👤 Исполнитель: {name}"
    return (
        f"{s} <b>{title}</b>{desc}\n"
        f"{p} Приоритет: {task.priority.value}{due}{assignee_text}\n"
        f"🆔 /task_{task.id}"
    )


# ── Создание задачи ───────────────────────────────────────────────────────────

@router.message(F.text == "➕ Создать задачу")
@router.message(Command("new_task"))
async def new_task_start(message: Message, state: FSMContext, db_user, session: AsyncSession):
    projects = await ProjectRepo(session).get_user_projects(db_user.id)
    if not projects:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        await message.answer(
            "У тебя нет проектов. Создай первый!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="➕ Создать проект", callback_data="project:new")
            ]])
        )
        return
    await state.update_data(creator_id=db_user.id)
    await message.answer("Выбери проект:", reply_markup=projects_kb(projects, prefix="task_project"))
    await state.set_state(TaskForm.waiting_project)


@router.callback_query(TaskForm.waiting_project, F.data.startswith("task_project:"))
async def task_choose_project(call: CallbackQuery, state: FSMContext, db_user, session: AsyncSession):
    project_id = int(call.data.split(":")[1])
    if not await check_permission(session, db_user.id, project_id, MemberRole.MEMBER):
        await call.answer("❌ У тебя нет доступа к этому проекту.", show_alert=True)
        return
    await state.update_data(project_id=project_id)
    await call.message.answer("Введи название задачи:")
    await state.set_state(TaskForm.waiting_title)
    await call.answer()


@router.message(TaskForm.waiting_title)
async def task_title(message: Message, state: FSMContext):
    text = message.text.strip()
    if len(text) < 2:
        await message.answer("Название слишком короткое. Введи ещё раз:")
        return
    if len(text) > 256:
        await message.answer("Слишком длинное (макс. 256 символов). Сократи:")
        return
    await state.update_data(title=text)
    # UX: skip_kb вместо /skip
    await message.answer("Описание задачи:", reply_markup=skip_kb())
    await state.set_state(TaskForm.waiting_description)


@router.message(TaskForm.waiting_description)
async def task_description(message: Message, state: FSMContext, session: AsyncSession):
    desc = None if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(description=desc)
    await _show_assignee_step(message, state, session)


@router.callback_query(TaskForm.waiting_description, F.data == "skip")
async def task_description_skip(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.update_data(description=None)
    await call.answer()
    await _show_assignee_step(call.message, state, session)


async def _show_assignee_step(message: Message, state: FSMContext, session: AsyncSession):
    """UX: шаг выбора исполнителя из участников проекта."""
    data = await state.get_data()
    members = await MemberRepo(session).get_members(data["project_id"])
    # Фильтруем observer — они не могут быть исполнителями
    members = [(m, u) for m, u in members if m.role != MemberRole.OBSERVER]
    await message.answer(
        "Выбери исполнителя:",
        reply_markup=assignee_kb(members, data["project_id"]),
    )
    await state.set_state(TaskForm.waiting_assignee)


@router.callback_query(TaskForm.waiting_assignee, F.data.startswith("assignee:"))
async def task_choose_assignee(call: CallbackQuery, state: FSMContext, db_user, session: AsyncSession):
    value = call.data.split(":")[1]
    if value == "self":
        assignee_id = db_user.id
    else:
        assignee_id = int(value)
    await state.update_data(assignee_id=assignee_id)
    await call.message.answer("Выбери приоритет:", reply_markup=priorities_kb())
    await state.set_state(TaskForm.waiting_priority)
    await call.answer()


@router.callback_query(TaskForm.waiting_priority, F.data.startswith("priority:"))
async def task_priority(call: CallbackQuery, state: FSMContext):
    await state.update_data(priority=call.data.split(":")[1])
    # UX: skip_kb для дедлайна
    await call.message.answer("Дедлайн (ДД.ММ.ГГГГ):", reply_markup=skip_kb())
    await state.set_state(TaskForm.waiting_due_date)
    await call.answer()


@router.message(TaskForm.waiting_due_date)
async def task_due_date(message: Message, state: FSMContext, session: AsyncSession):
    due_date = None
    if message.text.strip() != "/skip":
        try:
            due_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        except ValueError:
            await message.answer(
                "❌ Неверный формат даты.\n\n"
                "Введи <b>ДД.ММ.ГГГГ</b>, например: <b>31.12.2026</b>",
                parse_mode="HTML",
                reply_markup=skip_kb(),
            )
            return
    await state.update_data(due_date=due_date)
    if due_date:
        await message.answer("Напоминание:", reply_markup=reminder_kb())
        await state.set_state(TaskForm.waiting_reminder)
    else:
        await state.update_data(reminder="none")
        await _finalize_task(message, state, session)


@router.callback_query(TaskForm.waiting_due_date, F.data == "skip")
async def task_due_date_skip(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.update_data(due_date=None, reminder="none")
    await call.answer()
    await _finalize_task(call.message, state, session)


@router.callback_query(TaskForm.waiting_reminder, F.data.startswith("reminder:"))
async def task_reminder(call: CallbackQuery, state: FSMContext, session: AsyncSession):
    await state.update_data(reminder=call.data.split(":")[1])
    await call.answer()
    await _finalize_task(call.message, state, session)


async def _finalize_task(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()

    task_list_result = await session.execute(
        select(TaskList).where(TaskList.project_id == data["project_id"]).limit(1)
    )
    if not task_list_result.scalar_one_or_none():
        await message.answer("❌ Не найден список задач в проекте.")
        return

    task = await TaskRepo(session).create_task(
        title=data["title"],
        description=data.get("description"),
        project_id=data["project_id"],
        creator_id=data["creator_id"],
        assignee_id=data.get("assignee_id"),
        priority=data.get("priority", "normal"),
        due_date=data.get("due_date"),
        reminder=data.get("reminder", "none"),
    )

    # Уведомить исполнителя если назначен другой пользователь
    if task.assignee_id and task.assignee_id != data["creator_id"]:
        assignee_result = await session.execute(
            select(User).where(User.id == task.assignee_id)
        )
        assignee = assignee_result.scalar_one_or_none()
        if assignee:
            try:
                await message.bot.send_message(
                    chat_id=assignee.telegram_id,
                    text=(
                        f"📋 <b>Тебе назначена задача</b>\n\n"
                        f"📌 <b>{md.html.quote(task.title)}</b>\n"
                        f"👉 /task_{task.id}"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    p = PRIORITY_EMOJI.get(task.priority, "")
    due = f"\n📅 {task.due_date.strftime('%d.%m.%Y')}" if task.due_date else ""
    desc = f"\n📝 {md.html.quote(task.description)}" if task.description else ""
    await message.answer(
        f"✅ <b>Задача создана!</b>\n\n"
        f"{p} <b>{md.html.quote(task.title)}</b>{desc}{due}\n"
        f"🆔 /task_{task.id}",
        parse_mode="HTML",
        reply_markup=task_card_kb(task),
    )


# ── Просмотр задачи ───────────────────────────────────────────────────────────

@router.message(F.text.regexp(r"^/task_(\d+)$"))
async def view_task(message: Message, session: AsyncSession, db_user):
    task_id = int(message.text.split("_")[1])
    task = await TaskRepo(session).get_task(task_id)
    if not task:
        await message.answer("Задача не найдена.")
        return
    if not await _check_task_access(session, db_user, task, MemberRole.OBSERVER):
        await message.answer("❌ У тебя нет доступа к этой задаче.")
        return
    await message.answer(
        await _task_card_text(session, task), parse_mode="HTML", reply_markup=task_card_kb(task)
    )


@router.callback_query(F.data.startswith("task_view:"))
async def task_view_callback(call: CallbackQuery, session: AsyncSession, db_user):
    task_id = int(call.data.split(":")[1])
    task = await TaskRepo(session).get_task(task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    if not await _check_task_access(session, db_user, task, MemberRole.OBSERVER):
        await call.answer("❌ Нет доступа.", show_alert=True)
        return
    await call.message.edit_text(
        await _task_card_text(session, task), parse_mode="HTML", reply_markup=task_card_kb(task)
    )
    await call.answer()


# ── Смена статуса ─────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task_status:"))
async def toggle_status(call: CallbackQuery, session: AsyncSession, db_user):
    task_id = int(call.data.split(":")[1])
    task = await TaskRepo(session).get_task(task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    if not await _check_task_access(session, db_user, task, MemberRole.MEMBER):
        await call.answer("❌ Недостаточно прав.", show_alert=True)
        return
    task.status = NEXT_STATUS[task.status]
    task.completed_at = datetime.utcnow() if task.status == TaskStatus.DONE else None
    await session.commit()
    await call.message.edit_text(
        await _task_card_text(session, task), parse_mode="HTML", reply_markup=task_card_kb(task)
    )
    await call.answer(f"✅ {task.status.value}")


# ── Переназначить задачу (UX) ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task_reassign:"))
async def task_reassign_start(call: CallbackQuery, state: FSMContext, session: AsyncSession, db_user):
    task_id = int(call.data.split(":")[1])
    task = await TaskRepo(session).get_task(task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    if not await _check_task_access(session, db_user, task, MemberRole.MEMBER):
        await call.answer("❌ Недостаточно прав.", show_alert=True)
        return

    task_list = await _get_task_list(session, task.list_id)
    members = await MemberRepo(session).get_members(task_list.project_id)
    members = [(m, u) for m, u in members if m.role != MemberRole.OBSERVER]

    await state.update_data(task_id=task_id)
    await call.message.answer(
        f"Выбери нового исполнителя для задачи <b>{md.html.quote(task.title)}</b>:",
        parse_mode="HTML",
        reply_markup=assignee_kb(members, task_list.project_id),
    )
    await state.set_state(ReassignForm.waiting_assignee)
    await call.answer()


@router.callback_query(ReassignForm.waiting_assignee, F.data.startswith("assignee:"))
async def task_reassign_confirm(call: CallbackQuery, state: FSMContext, session: AsyncSession, db_user):
    data = await state.get_data()
    await state.clear()

    value = call.data.split(":")[1]
    new_assignee_id = db_user.id if value == "self" else int(value)

    task = await TaskRepo(session).get_task(data["task_id"])
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return

    old_assignee_id = task.assignee_id
    task.assignee_id = new_assignee_id
    await session.commit()

    # Уведомить нового исполнителя
    if new_assignee_id != old_assignee_id:
        assignee_result = await session.execute(
            select(User).where(User.id == new_assignee_id)
        )
        assignee = assignee_result.scalar_one_or_none()
        if assignee:
            try:
                await call.bot.send_message(
                    chat_id=assignee.telegram_id,
                    text=(
                        f"👤 <b>Тебе переназначена задача</b>\n\n"
                        f"📌 <b>{md.html.quote(task.title)}</b>\n"
                        f"👉 /task_{task.id}"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    await call.message.edit_text(
        await _task_card_text(session, task), parse_mode="HTML", reply_markup=task_card_kb(task)
    )
    await call.answer("✅ Исполнитель изменён")


# ── Удаление задачи ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("task_delete:"))
async def task_delete_ask(call: CallbackQuery):
    task_id = int(call.data.split(":")[1])
    await call.message.edit_reply_markup(reply_markup=confirm_delete_kb(task_id))
    await call.answer()


@router.callback_query(F.data.startswith("task_delete_confirm:"))
async def task_delete_confirm(call: CallbackQuery, session: AsyncSession, db_user):
    task_id = int(call.data.split(":")[1])
    task = await TaskRepo(session).get_task(task_id)
    if not task:
        await call.answer("Задача не найдена.", show_alert=True)
        return
    if task.creator_id != db_user.id:
        task_list = await _get_task_list(session, task.list_id)
        if not task_list or not await check_permission(
            session, db_user.id, task_list.project_id, MemberRole.OWNER
        ):
            await call.answer(
                "❌ Только создатель или владелец проекта может удалять задачи.",
                show_alert=True,
            )
            return
    await TaskRepo(session).delete_task(task_id)
    await call.message.edit_text("🗑 Задача удалена.")
    await call.answer()
