from aiogram.utils import markdown as md
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import MemberRole, User, Project
from db.repository import InviteRepo, ProjectRepo, UserRepo, MemberRepo
from keyboards.inline import projects_kb, role_select_kb, invite_method_kb
from states.forms import InviteForm, AddMemberForm
from config import settings

router = Router()


# ── /invite ───────────────────────────────────────────────────────────────────

@router.message(Command("invite"))
async def cmd_invite(message: Message, state: FSMContext, db_user, session: AsyncSession):
    projects = await ProjectRepo(session).get_owned_projects(db_user.id)
    if not projects:
        await message.answer("У тебя нет проектов с правами владельца.")
        return
    await message.answer(
        "Выбери проект:",
        reply_markup=projects_kb(projects, prefix="inv_project"),
    )
    await state.set_state(InviteForm.waiting_project)


@router.callback_query(InviteForm.waiting_project, F.data.startswith("inv_project:"))
async def invite_choose_project(call: CallbackQuery, state: FSMContext):
    project_id = int(call.data.split(":")[1])
    await state.update_data(project_id=project_id)
    await call.message.answer("Как добавить участника?", reply_markup=invite_method_kb())
    await state.set_state(InviteForm.waiting_method)
    await call.answer()


@router.callback_query(InviteForm.waiting_method, F.data.startswith("invite_method:"))
async def invite_choose_method(call: CallbackQuery, state: FSMContext):
    method = call.data.split(":")[1]
    await state.update_data(method=method)
    await call.message.answer(
        "Выбери роль для нового участника:",
        reply_markup=role_select_kb("inv_role"),
    )
    await state.set_state(InviteForm.waiting_role)
    await call.answer()


@router.callback_query(InviteForm.waiting_role, F.data.startswith("inv_role:"))
async def invite_choose_role(call: CallbackQuery, state: FSMContext, db_user, session: AsyncSession):
    role = MemberRole(call.data.split(":")[1])
    data = await state.get_data()

    if data["method"] == "link":
        await state.clear()
        invite = await InviteRepo(session).create_invite(
            project_id=data["project_id"],
            creator_id=db_user.id,
            role=role,
        )
        role_labels = {"owner": "👑 Владелец", "member": "👤 Участник", "observer": "👁 Наблюдатель"}
        link = f"https://t.me/{settings.BOT_USERNAME}?start=invite_{invite.token}"
        await call.message.answer(
            f"🔗 <b>Ссылка-приглашение</b>\n\n"
            f"Роль: {role_labels[role.value]}\n\n"
            f"<code>{link}</code>\n\n"
            f"⏳ Действует 48 часов · Одноразовая",
            parse_mode="HTML",
        )
    else:
        # username-флоу: сохраняем роль и переходим к вводу username
        await state.update_data(role=role.value)
        await state.set_state(AddMemberForm.waiting_username)
        await call.message.answer("Введи @username участника:")

    await call.answer()


# ── Ветка: добавление по @username ────────────────────────────────────────────

@router.message(AddMemberForm.waiting_username)
async def add_by_username(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    await state.clear()

    role = MemberRole(data["role"])
    user, error = await MemberRepo(session).add_by_username(
        project_id=data["project_id"],
        username=message.text.strip(),
        role=role,
    )
    if error:
        await message.answer(f"❌ {error}")
        return

    role_labels = {"owner": "👑 Владелец", "member": "👤 Участник", "observer": "👁 Наблюдатель"}
    await message.answer(
        f"✅ <b>@{md.html.quote(user.username or user.full_name)}</b> добавлен как {role_labels[role.value]}",
        parse_mode="HTML",
    )
    await message.bot.send_message(
        chat_id=user.telegram_id,
        text=(
            f"👋 Тебя добавили в проект!\n\n"
            f"Роль: <b>{role_labels[role.value]}</b>\n"
            f"Используй /projects чтобы его увидеть."
        ),
        parse_mode="HTML",
    )


# ── Deep link — принятие инвайта по ссылке ───────────────────────────────────

@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: Message, db_user, session: AsyncSession):
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("invite_"):
        return

    token = args[1].removeprefix("invite_")
    project, error = await InviteRepo(session).accept_invite(
        token=token, user_id=db_user.id
    )
    if error:
        await message.answer(f"❌ {error}")
        return

    await message.answer(
        f"✅ Ты вступил в проект <b>{md.html.quote(project.name)}</b>!\n"
        f"Используй /projects чтобы увидеть задачи.",
        parse_mode="HTML",
    )

    # Уведомить владельца
    owner = await session.get(User, project.owner_id)
    if owner and owner.telegram_id != message.from_user.id:
        await message.bot.send_message(
            chat_id=owner.telegram_id,
            text=(
                f"👤 <b>{message.from_user.full_name}</b> вступил в проект "
                f"<b>{project.name}</b>"
            ),
            parse_mode="HTML",
        )


# ── Просмотр участников ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("project_members:"))
async def show_members(call: CallbackQuery, session: AsyncSession):
    project_id = int(call.data.split(":")[1])
    members = await MemberRepo(session).get_members(project_id)

    role_icons = {"owner": "👑", "member": "👤", "observer": "👁"}
    lines = ["<b>👥 Участники проекта:</b>\n"]
    for membership, user in members:
        icon = role_icons[membership.role.value]
        name = f"@{user.username}" if user.username else user.full_name
        lines.append(f"{icon} {name} — <i>{membership.role.value}</i>")

    await call.message.answer("\n".join(lines), parse_mode="HTML")
    await call.answer()
