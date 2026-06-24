from aiogram.fsm.state import State, StatesGroup


class ProjectForm(StatesGroup):
    waiting_name = State()


class TaskForm(StatesGroup):
    waiting_project = State()
    waiting_title = State()
    waiting_description = State()
    waiting_assignee = State()   # UX: выбор исполнителя
    waiting_priority = State()
    waiting_due_date = State()
    waiting_reminder = State()


class ReassignForm(StatesGroup):        # UX: переназначение задачи
    waiting_assignee = State()


class InviteForm(StatesGroup):
    waiting_project = State()
    waiting_method = State()
    waiting_role = State()


class AddMemberForm(StatesGroup):
    waiting_project = State()
    waiting_username = State()
    waiting_role = State()


class FilterForm(StatesGroup):
    waiting_project = State()
    waiting_filters = State()


class SearchForm(StatesGroup):
    waiting_query = State()


class ExportForm(StatesGroup):
    waiting_project = State()
