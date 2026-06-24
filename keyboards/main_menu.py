from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📁 Проекты"), KeyboardButton(text="✅ Мои задачи")],
            [KeyboardButton(text="➕ Создать задачу"), KeyboardButton(text="🔎 Поиск")],
            [KeyboardButton(text="🔍 Фильтр задач"), KeyboardButton(text="📥 Экспорт CSV")],
        ],
        resize_keyboard=True,
    )
