from telebot import types


def process_start_command(user_id, first_name, last_name, username):
    """Формирует приветственное сообщение с кнопкой регистрации и возвращает их.

    :return hello_message, markup"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Зарегистрироваться', callback_data='button_registration'))

    hello_message = (f'Добро пожаловать {first_name}!\n\n'
                     f'Это бот IT отдела. Для полного списка команд используйте меню.\n\n'
                     f'Необходимо пройти регистрацию, предоставив согласие на обработку данных:\n'
                     f'• ID: {user_id}\n'
                     f'• Имя: {first_name}\n'
                     f'• Фамилия: {last_name}\n'
                     f'• Username: @{username}\n')

    return hello_message, markup
