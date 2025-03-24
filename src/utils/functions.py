import ast
import logging
import os
import random
from datetime import datetime

import dotenv
import requests
import schedule
import telebot
from requests.auth import HTTPBasicAuth
from telebot import types
from telebot_calendar import Calendar, CallbackData

from src.utils.decorarors import error_handling
from src.utils.interactions_with_services import Exchange_with_ERP
from src.utils.logger_setup import setup_logger
from src.utils.sql import Work_with_DB

# Инициализация бота
dotenv.load_dotenv()
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
id_dev = os.getenv('DEV_ID')

# Настройка логгера
log_file = os.getenv("LOG_FILE", "bot.log")  # Default to "bot.log" if environment variable not set
logger = setup_logger(log_file=log_file, level=logging.INFO)
logger.info("Bot initialized and logger setup completed.")
url_app = os.getenv('URL_APP_REMIT_EMPLOYEE')
login = os.getenv('LOGIN_AUTH_GET_APP_REMIT_EMPLOYEE')
passwd = os.getenv('PASS_AUTH_GET_APP_REMIT_EMPLOYEE')

# Инициализация календаря
calendar = Calendar()
calendar_callback = CallbackData("calendar", "action", "year", "month", "day")

# Глобальные переменные для хранения состояния
user_data = {}


def register(call):
    """Регистрация данных о пользователе в БД"""

    logger.info(f"Entering method: register with call: {call}")
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    last_name = call.from_user.last_name
    username = call.from_user.username

    db_instance = Work_with_DB()
    if not db_instance.check_for_existence(user_id):
        if db_instance.insert_new_user(user_id, first_name, last_name, username):
            list_rand_phrase = [
                'Регистрация выполнена успешно!',
                'Вы успешно зарегистрированы!',
                'Всё прошло успешно!',
                'Готово!'
            ]
            rand_phrase = (
                f'{random.choice(list_rand_phrase)}\nПосмотреть функционал можно в меню, слева от поля ввода '
                f'сообщения.')

            report_to_dev = (f'Зарегистрирован новый пользователь:\n'
                             f'• ID: {user_id}\n'
                             f'• Имя: {first_name}\n'
                             f'• Фамилия: {last_name}\n'
                             f'• Username:  @{username}\n')
            bot.send_message(chat_id=id_dev, text=report_to_dev)

            logger.info(f"Exiting method: register with response: {rand_phrase}")
            return rand_phrase
    else:
        list_rand_phrase = [
            f'Мы уже знакомы! В моём архиве есть карточка с именем {first_name}.',
            'Повторно зарегистрироваться не получится..',
            'Опять? Одной регистрации достаточно ;)',
            'Кажется вы забыли. Я напомню - вы уже регистрировались! :)'
        ]
        rand_phrase = (f'{random.choice(list_rand_phrase)}\nПосмотреть функционал можно в меню, слева от поля ввода '
                       f'сообщения.')

        logger.info(f"Exiting method: register with response: {rand_phrase}")
        return rand_phrase


def unknown_user(message):
    """Если пользователь неизвестен - показывает сообщение с кнопкой о необходимости регистрации.
    Иначе возвращает True"""

    user_id = message.from_user.id
    if Work_with_DB().check_for_existence(user_id) is False:
        # Инициализация клавиатуры
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text='Зарегистрироваться', callback_data='button_registration'))

        # Приветственное сообщение
        hello_message = (f'Для того чтобы пользоваться функциями бота, необходимо пройти регистрацию. '
                         f'Тем самым вы даёте согласие на хранение и обработку данных о вашем аккаунте.\n\n'
                         f'Вот что мы будем хранить:\n'
                         f'• ID: {message.from_user.id}\n'
                         f'• Имя: {message.from_user.first_name}\n'
                         f'• Фамилия: {message.from_user.last_name}\n'
                         f'• Username:  @{message.from_user.username}\n')

        bot.send_message(message.chat.id, hello_message, reply_markup=markup)
        return hello_message, markup
    else:
        return True


def dej_name(call):
    """Возвращает из БД имя следующего дежурного.
    :return str(name)"""

    user_id = call.from_user.id
    if Work_with_DB().check_for_existence(user_id) is True:
        list_next_dej = Work_with_DB().get_data_next_dej()
        # print(list_next_dej)
        if list_next_dej is not None:

            first_date = list_next_dej[0]
            first_date_datetime = datetime.strptime(first_date, '%Y-%m-%d')
            first_date_format = first_date_datetime.strftime("%d.%m.%Y")

            last_date = list_next_dej[1]
            last_date_datetime = datetime.strptime(last_date, '%Y-%m-%d')
            last_date_format = last_date_datetime.strftime("%d.%m.%Y")

            user_first_name = list_next_dej[2]

            result_text = f'В период с {first_date_format} по {last_date_format} будет дежурить {user_first_name}'
            return result_text
        else:
            result_text = f'Данных о дежурных нет'
            return result_text


def list_dej(call):
    """Возвращает из БД список дежурных.
        :return
        str(1. str_one
        2. str_two)"""

    user_id = call.from_user.id
    db_instance = Work_with_DB()
    if db_instance.check_for_existence(user_id):
        list_next_dej = db_instance.get_data_list_dej()
        if list_next_dej:
            return '\n\n'.join(
                f"{idx + 1}. В период с {datetime.strptime(item[0], '%Y-%m-%d').strftime('%d.%m.%Y')} по "
                f"{datetime.strptime(item[1], '%Y-%m-%d').strftime('%d.%m.%Y')} "
                f"будет дежурить {item[2]}"
                for idx, item in enumerate(list_next_dej)
            )
        else:
            return 'Данных о дежурных нет'


def fill_schedule_dej(call):
    """Заполняет шапку календаря, формирует клавиатуру и возвращает результат"""

    text = 'Выберите дату начала дежурства:'
    calendar_data = show_calendar(chat_id=None, title=text)
    return calendar_data


def show_calendar(chat_id=None, title=None):
    """Если в chat_id None - возвращает текст и клавиатуру в виде dict. Иначе отправляет пользователю календарь."""

    now = datetime.now()

    if chat_id is None:
        keyboard = calendar.create_calendar(name=calendar_callback.prefix, year=now.year, month=now.month)
        result = {
            'text': title,
            'keyboard': keyboard
        }

        return result
    else:
        bot.send_message(chat_id, title, reply_markup=calendar.create_calendar(name=calendar_callback.prefix,
                                                                               year=now.year,
                                                                               month=now.month))


def ask_for_name(chat_id):
    """Отправляет пользователю сообщение с inline клавиатурой для выбора имени вносимого в таблицу в БД дежурного."""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Павел", callback_data="name_Павел"))
    markup.add(types.InlineKeyboardButton("Дмитрий", callback_data="name_Дмитрий"))
    markup.add(types.InlineKeyboardButton("Никита", callback_data="name_Никита"))
    markup.add(types.InlineKeyboardButton("Алексей", callback_data="name_Алексей"))
    markup.add(types.InlineKeyboardButton("Отмена", callback_data="CANCEL"))
    bot.send_message(chat_id, "Кто будет дежурить в указанный период?", reply_markup=markup)


def finalize_event(chat_id, user_id):
    """Если выбраны обе даты и имя дежурного, записывает данные в БД и оповещает о совершенном действии."""

    if user_id not in user_data:
        bot.send_message(chat_id, "Данные для завершения события отсутствуют. Повторите попытку.")
        return
    data = user_data[user_id]
    first_date = data['first_date']
    last_date = data['last_date']
    name_hero = data['name']

    answer_db = Work_with_DB().insert_dej_in_table(first_date, last_date, name_hero)
    if answer_db is True:
        bot.send_message(chat_id,
                         f"Добавлено новое событие:\n"
                         f"В период с {first_date.strftime('%d.%m.%Y')} по {last_date.strftime('%d.%m.%Y')}"
                         f" будет дежурить {name_hero}.")  # Ensure the message is grammatically complete

        del user_data[user_id]
    else:
        bot.send_message(chat_id, answer_db)


def change_status_news(call):
    """Меняет статус подписки на новости у пользователя"""

    answer = Work_with_DB().change_user_status_news(call.from_user.id)
    return answer


def post_answer_of_event(dict_answer):
    """Возвращает JSON в ERP для регистрации события о простое."""

    key_auth = os.getenv("EVENT_HANDLING_KEY")
    value_auth = os.getenv("EVENT_HANDLING_VALUE")
    dict_answer[key_auth] = value_auth
    answer_ERP = Exchange_with_ERP(dict_answer).answer_from_ERP()
    logger.debug(f"ERP answer: {answer_ERP}")
    return answer_ERP


def notification_for(focus_group, text_message, silent=False):
    """Рассылает уведомление выбранной группе людей"""

    logger.info(
        f"Entering method: notification_for with focus_group: {focus_group}, text_message: {text_message}, silent: {silent}")
    list_id_user = Work_with_DB().get_list_users_id(focus_group)

    for user_id in list_id_user:
        try:
            bot.send_message(chat_id=user_id, text=text_message, disable_notification=silent)
        except telebot.apihelper.ApiTelegramException as e:
            # Проверяем текст ошибки
            if "bot was blocked by the user" in str(e):
                logger.warning(f"User {user_id} has blocked the bot.")
                Work_with_DB().change_user_status_use_bot(user_id)
            else:
                logger.error(f"An unexpected error occurred: {e}")
    logger.info("Exiting method: notification_for")


def notification_for_all_user(text_message):
    """Рассылает уведомление всем пользователям бота"""

    notification_for(focus_group='all', text_message=text_message)


def notification_for_subscribers(text_message):
    """Рассылает уведомление подписчикам на новости IT отдела"""

    notification_for(focus_group='news', text_message=text_message)


def notification_for_bar(text_message):
    """Рассылает уведомление подписчикам барахолки"""

    notification_for(focus_group='baraholka', text_message=text_message)


def schedule_next_run():
    """Обновляет расписание заданий"""

    def create_random_time(summary=None, name_func='?'):
        hour = '{:02d}'.format(random.randint(00, 23))

        if summary == 'first summary':
            """Формирует время <07:random(0:59)>"""
            hour = '07'
        elif summary == 'second summary':
            """Формирует время <08:random(0:59)>"""
            hour = '08'
        elif summary == 'daily summary':
            """Формирует время <random(14-17):random(0:59)>"""
            hour = '{:02d}'.format(random.randint(14, 17))
        else:
            """Если тег не указан час будет рандомным"""
            hour = hour

        minutes = '{:02d}'.format(random.randint(0, 59))
        date_str = datetime.now().strftime("%d.%m.%Y")
        time_str = f'{hour}:{minutes}'
        logger.debug(f'Function "{name_func}.tag({summary})" scheduled to execute on {date_str} at {time_str}.')
        return time_str

    logger.info(f'{datetime.now().strftime("%d.%m.%Y %H:%M:%S")} Updating task schedules:')

    list_func = [
        # {'first summary': []},
        # {'second summary': []},
        {'daily summary': [notification_of_dej_tomorrow]}
    ]

    def create_schedule(list_funcs):
        """Пересоздаёт расписание выполнения заданий по тегам на текущий день"""

        for element in list_funcs:
            for time_of_day, funcs in element.items():
                schedule.clear(time_of_day)  # Clear old time
                logger.info(f'Schedule tasks with tag "{time_of_day}" have been cleared.')
                for func in funcs:
                    (schedule.every().day.at(create_random_time(summary=time_of_day, name_func=func.__name__)).
                     do(func).
                     tag(time_of_day))

    create_schedule(list_funcs=list_func)


def notification_of_dej_tomorrow():
    """Если завтра есть дежурный, пришлёт уведомление всем подписчикам"""

    check_dej = Work_with_DB().check_dej_tomorrow()
    if check_dej is not None:
        notification_for_subscribers(check_dej)


def get_app_remit_employee(call):
    """Загружает файл из URL и передаёт APK пользователю."""

    # Выполняем GET-запрос с авторизацией
    try:
        response = requests.get(url_app, auth=HTTPBasicAuth(login, passwd), timeout=10)
        response.raise_for_status()
        bot.send_document(
            chat_id=call.from_user.id,
            data=response.content,
            filename="remit_employee.apk",
            caption=None
        )
    except requests.RequestException as e:
        bot.send_message(chat_id=call.from_user.id, text=f"Ошибка загрузки файла: {str(e)}")
        logger.error(f"Failed to download the file: {e}")


def update_data_door():
    """Актуализирует данные в БД о последней двери"""

    name = os.getenv('BIRD_AUTH_KEY')
    value = os.getenv('BIRD_AUTH_VALUE')

    status_sql = Work_with_DB().check_door()[0]
    answer_erp = Exchange_with_ERP({name: value}).in_out()
    # print(status_sql)
    # print(answer_erp)

    # Если ответ от ERP словарь
    if isinstance(answer_erp, dict):
        # Если ERP вернул ошибку
        if answer_erp.get(name) is False:
            logger.error(answer_erp.get(name))
            return answer_erp.get('textError')
    # Если ответ от ERP список
    elif isinstance(answer_erp, list):
        last_point = answer_erp[-1]
        # print(status_sql)
        # print(type(status_sql))
        # print(last_point)
        # print(type(last_point))
        if status_sql != last_point:
            Work_with_DB().update_checkpoint(last_point)
            notif_bird(last_point)


@error_handling
def notif_bird(last_point):
    """Уведомляет о чекпоинте"""

    logger.debug(f"Checkpoint notification details: {last_point}")
    list_last_point = last_point.split(' ')
    list_observ_doors = [
        'Администрация Офис 1 Этаж',
        'КПП Новое'
    ]
    list_users_str = os.getenv('LIST_OBS_BIRD')
    list_users = ast.literal_eval(list_users_str)

    direction = list_last_point[2]
    door = ' '.join(list_last_point[3:])
    text_notif = ''

    if door in list_observ_doors:
        if direction == 'Вход':
            text_notif = 'Пользователь присоединился к чату'
        elif direction == 'Выход':
            text_notif = 'Пользователь покинул чат'

    markup = types.InlineKeyboardMarkup()

    name_button = 'Ок'
    callback_data = 'DELETE'
    markup.add(types.InlineKeyboardButton(text=name_button, callback_data=callback_data))

    for user_id in list_users:
        bot.send_message(chat_id=user_id, text=text_notif, reply_markup=markup)


@error_handling
def decline_word(number, word_forms):
    logger.debug(f"Declining word for number: {number}, word forms: {word_forms}")
    """
    Функция для склонения слова в зависимости от числа.

    :param number: int, число
    :param word_forms: tuple или list, формы слова в порядке:
                       (форма для 1, форма для 2-4, форма для 5-20 и т.д.)
    :return: str, правильная форма слова
    """
    if not isinstance(word_forms, (tuple, list)) or len(word_forms) != 3:
        raise ValueError("word_forms должен быть кортежем или списком из 3 элементов")

    remainder_10 = number % 10
    remainder_100 = number % 100

    if remainder_10 == 1 and remainder_100 != 11:
        return word_forms[0]
    elif 2 <= remainder_10 <= 4 and not (12 <= remainder_100 <= 14):
        return word_forms[1]
    else:
        return word_forms[2]


@error_handling
def find_value_by_name(data, target_name, target_key):
    # Если data является словарем
    if isinstance(data, dict):
        # Проверяем, есть ли в словаре ключ 'name' и его значение равно target_name
        if data.get('callback') == target_name:
            # Если нашли, возвращаем значение target_key
            return data.get(target_key)

        # Рекурсивно проходим по всем значениям словаря
        for key, value in data.items():
            result = find_value_by_name(value, target_name, target_key)
            if result is not None:
                return result

    # Если data является списком
    elif isinstance(data, list):
        # Рекурсивно проходим по всем элементам списка
        for item in data:
            result = find_value_by_name(item, target_name, target_key)
            if result is not None:
                return result

    # Если ничего не нашли, возвращаем None
    return None


@error_handling
def formation_of_the_function_rating_text(list_from_db):
    """Принимает лист с результатами из БД и составляет из него текст с рейтингом"""

    from src.utils.menu_formation import menu_storage
    if not list_from_db:
        logger.warning('Нет данных')
        return 'Нет данных'

    menu = menu_storage
    dict_top = {
        find_value_by_name(menu, element[0], "name"): element[1] for element in list_from_db
    }

    return '\n'.join(
        f"{idx + 1} место: \"{name}\" - {count} {decline_word(count, ('запрос', 'запроса', 'запросов'))}"
        for idx, (name, count) in enumerate(dict_top.items())
    )


@error_handling
def create_top_chart_func():
    """Формирует рейтинг топ 3 самых вызываемых функций"""

    logger.info("Entering method: create_top_chart_func")
    heading = '••• ТОП ЧАРТ ФУНКЦИЙ •••\n\n'

    list_db_today = Work_with_DB().get_top_func_stat('today')
    text_top_chart_day = formation_of_the_function_rating_text(list_db_today)
    title_day = f'• топ 3 за день •\nНет данных для формирования рейтинга\n\n'
    if text_top_chart_day:
        title_day = f'• топ 3 за день •\n{text_top_chart_day}\n\n'

    list_db_month = Work_with_DB().get_top_func_stat('month')
    text_top_chart_month = formation_of_the_function_rating_text(list_db_month)
    title_month = f'• топ 3 за месяц •\nНет данных для формирования рейтинга\n\n'
    if text_top_chart_month:
        title_month = f'• топ 3 за месяц •\n{text_top_chart_month}\n\n'

    list_db_all_time = Work_with_DB().get_top_func_stat('all_time')
    text_top_chart_all_time = formation_of_the_function_rating_text(list_db_all_time)
    title_all_time = f'• топ 3 за всё время •\nНет данных для формирования рейтинга'
    if text_top_chart_all_time:
        title_all_time = f'• топ 3 за всё время •\n{text_top_chart_all_time}'

    text_all_rating = '\n\n'.join([heading, title_day, title_month, title_all_time])

    bot.send_message(chat_id=id_dev, text=text_all_rating)
    logger.info("Exiting method: create_top_chart_func")
