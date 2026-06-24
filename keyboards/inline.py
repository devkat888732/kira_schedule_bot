from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db.models import Task, TaskStatus, TaskPriority

PRIORITY_EMOJI = {
    TaskPriority.LOW: "🔵",
    TaskPriority.NORMAL: "🟡",
    TaskPriority.HIGH: "🟠",
    TaskPriority.URGENT: "🔴",
}

STATUS_EMOJI = {
    TaskStatus.TODO: "⬜",
    TaskStatus.IN_PROGRESS: "🔄",
    TaskStatus.REVIEW: "👀",
    TaskStatus.DONE: "✅",
}

NEXT_STATUS_LABEL = {
    TaskStatus.TODO: "🔄 In Progress",
    TaskStatus.IN_PROGRESS: "👀 Review",
    TaskStatus.REVIEW: "✅ Done",
    TaskStatus.DONE: "⬜ Todo",
}


def task_card_kb(task: Task) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Статус → {NEXT_STATUS_LABEL[task.status]}",
            callback_data=f"task_status:{task.id}",
        )],
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task_delete:{task.id}"),
            InlineKeyboardButton(text="👁 Подробнее", callback_data=f"task_view:{task.id}"),
        ],
    ])


def projects_kb(projects: list, prefix: str = "project") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"📁 {p.name}", callback_data=f"{prefix}:{p.id}")]
        for p in projects
    ]
    if prefix == "project":
        rows.append([InlineKeyboardButton(text="➕ Новый проект", callback_data="project:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def priorities_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=f"{PRIORITY_EMOJI[p]} {p.value.capitalize()}",
            callback_data=f"priority:{p.value}",
        )
        for p in TaskPriority
    ]])


def reminder_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏰ За 1 час", callback_data="reminder:1h"),
            InlineKeyboardButton(text="📅 За 1 день", callback_data="reminder:24h"),
        ],
        [
            InlineKeyboardButton(text="🔔 Оба", callback_data="reminder:both"),
            InlineKeyboardButton(text="🔕 Без напоминания", callback_data="reminder:none"),
        ],
    ])


def confirm_delete_kb(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"task_delete_confirm:{task_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"task_view:{task_id}"),
    ]])


def invite_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔗 Ссылка", callback_data="invite_method:link"),
        InlineKeyboardButton(text="👤 @username", callback_data="invite_method:username"),
    ]])


def role_select_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👑 Владелец", callback_data=f"{prefix}:owner"),
            InlineKeyboardButton(text="👤 Участник", callback_data=f"{prefix}:member"),
        ],
        [InlineKeyboardButton(text="👁 Наблюдатель", callback_data=f"{prefix}:observer")],
    ])


STATUS_LABELS = {
    "todo": "⬜ Todo", "in_progress": "🔄 In Progress",
    "review": "👀 Review", "done": "✅ Done",
}
PRIORITY_LABELS = {
    "low": "🔵 Low", "normal": "🟡 Normal",
    "high": "🟠 High", "urgent": "🔴 Urgent",
}


def filter_kb(active_filters: dict = None) -> InlineKeyboardMarkup:
    af = active_filters or {}
    rows = []
    rows.append([InlineKeyboardButton(text="— Статус —", callback_data="noop")])
    statuses = list(STATUS_LABELS.items())
    for i in range(0, len(statuses), 2):
        row = []
        for val, label in statuses[i:i+2]:
            tick = "✓ " if af.get("status") == val else ""
            row.append(InlineKeyboardButton(
                text=f"{tick}{label}", callback_data=f"filter_status:{val}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton(text="— Приоритет —", callback_data="noop")])
    priorities = list(PRIORITY_LABELS.items())
    for i in range(0, len(priorities), 2):
        row = []
        for val, label in priorities[i:i+2]:
            tick = "✓ " if af.get("priority") == val else ""
            row.append(InlineKeyboardButton(
                text=f"{tick}{label}", callback_data=f"filter_priority:{val}"
            ))
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="✅ Применить", callback_data="filter_apply"),
        InlineKeyboardButton(text="🔄 Сбросить", callback_data="filter_reset"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def skip_kb() -> InlineKeyboardMarkup:
    """UX: заменяет /skip — кнопка «⏭ Пропустить» на мобильном."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip"),
    ]])


def assignee_kb(members: list, project_id: int) -> InlineKeyboardMarkup:
    """UX: список участников проекта для выбора исполнителя."""
    rows = []
    role_icons = {"owner": "👑", "member": "👤", "observer": "👁"}
    for membership, user in members:
        icon = role_icons.get(membership.role.value, "👤")
        name = f"@{user.username}" if user.username else user.full_name
        rows.append([InlineKeyboardButton(
            text=f"{icon} {name}",
            callback_data=f"assignee:{user.id}",
        )])
    rows.append([InlineKeyboardButton(
        text="👤 Назначить на себя",
        callback_data="assignee:self",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def task_card_kb(task: Task) -> InlineKeyboardMarkup:  # noqa: F811
    """Переопределяем с кнопкой Переназначить (UX)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"Статус → {NEXT_STATUS_LABEL[task.status]}",
            callback_data=f"task_status:{task.id}",
        )],
        [
            InlineKeyboardButton(text="👤 Переназначить", callback_data=f"task_reassign:{task.id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"task_delete:{task.id}"),
        ],
        [InlineKeyboardButton(text="👁 Подробнее", callback_data=f"task_view:{task.id}")],
    ])
