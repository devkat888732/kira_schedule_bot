from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import datetime

API_TOKEN = 'ВАШ_ТОКЕН'

bot = Bot(token=8520139035:AAGIDs_BwkIOxcOxQSxrudX1htQ1kw4x06I)
dp = Dispatcher(bot)

# Хранилище сообщений {дата: set([сообщения])}
storage = {}

@dp.message_handler()
async def handle_message(message: types.Message):
    user_text = message.text
    # Сохраняем текст во временный контекст пользователя
    dp.current_state(user=message.from_user.id).update_data(last_text=user_text)
    # Предлагаем выбрать дату через клавиатуру
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    today = datetime.date.today()
    for i in range(7):
        date_btn = KeyboardButton((today + datetime.timedelta(days=i)).strftime('%d.%m.%Y'))
        markup.add(date_btn)
    await message.answer('На какую дату сохранить?', reply_markup=markup)

@dp.message_handler(lambda msg: valid_date(msg.text))
async def handle_date(message: types.Message):
    selected_date = message.text
    data = await dp.current_state(user=message.from_user.id).get_data()
    last_text = data.get('last_text')
    if selected_date not in storage:
        storage[selected_date] = set()
    storage[selected_date].add(last_text)
    await message.answer(f'Сохранено на {selected_date}?')

@dp.message_handler(commands=['список'])
async def handle_list(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for date in storage.keys():
        markup.add(KeyboardButton(date))
    await message.answer('Выбери дату:', reply_markup=markup)

@dp.message_handler(commands=['все'])
async def handle_all_list(message: types.Message):
    all_items = set()
    for items in storage.values():
        all_items.update(items)
    await message.answer('Все записи:\n' + '\n'.join(all_items))

@dp.message_handler(lambda msg: msg.text in storage.keys())
async def handle_show_date_list(message: types.Message):
    selected_date = message.text
    items = storage.get(selected_date, [])
    await message.answer(f'Записи на {selected_date}:\n' + '\n'.join(items))


def valid_date(text):
    try:
        datetime.datetime.strptime(text, '%d.%m.%Y')
        return True
    except:
        return False

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)