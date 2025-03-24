import asyncio
import datetime
import inspect
import json
import logging
import os
import threading
import time

import dotenv
import requests
import schedule
import telebot
from telebot import types
from telebot_calendar import Calendar, CallbackData

import src.utils.menu_formation as menu_form
from src.utils.decorarors import registration_of_keystrokes
from src.utils.functions import unknown_user, user_data, show_calendar, ask_for_name, finalize_event, \
    post_answer_of_event, schedule_next_run, update_data_door, create_top_chart_func
from src.utils.logger_setup import setup_logger
from src.utils.sql import Work_with_DB

dotenv.load_dotenv()
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    raise ValueError("BOT_TOKEN is missing in environment variables")
bot = telebot.TeleBot(bot_token)
dev_id = os.getenv('DEV_ID')

# Инициализация календаря
calendar = Calendar()
calendar_callback = CallbackData("calendar", "action", "year", "month", "day")

logger = setup_logger(log_file="bot.log", level=logging.INFO)

# Add a single console handler if no handlers are present
if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def answer_bot(message, text_answer, keyboard=None, format_text='no'):
    """Отправка текста и клавиатуры пользователю"""

    user_id = message.forward_from.id if message.forward_from else message.from_user.id
    count_text_message = len(text_answer) * 0.01
    logger.debug(f"Расчёт времени набора текста: {count_text_message} секунд")

    bot.send_chat_action(chat_id=user_id, action='typing')
    time.sleep(count_text_message)

    if keyboard is None:
        bot.reply_to(message=message, text=text_answer, parse_mode='MarkdownV2' if format_text != 'no' else None)
    else:
        bot.send_message(chat_id=user_id, text=text_answer, reply_markup=keyboard)

    logger.info(f'Текст отправлен пользователю: "{text_answer}"')


@bot.message_handler(commands=['start'])
def start_command(message):
    """Отправка приветственного сообщения и создание кнопки регистрации"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Зарегистрироваться', callback_data='button_registration'))

    hello_message = (f'Добро пожаловать {message.from_user.first_name}!\n\n'
                     f'Это бот IT отдела. Для полного списка команд используйте меню.\n\n'
                     f'Необходимо пройти регистрацию, предоставив согласие на обработку данных:\n'
                     f'• ID: {message.from_user.id}\n'
                     f'• Имя: {message.from_user.first_name}\n'
                     f'• Фамилия: {message.from_user.last_name}\n'
                     f'• Username: @{message.from_user.username}\n')

    bot.send_message(message.chat.id, hello_message, reply_markup=markup)
    logger.info(f"Сообщение приветствия отправлено: {message.from_user.first_name} (ID: {message.from_user.id})")


# Обработчик команды /menu
@bot.message_handler(commands=['menu'])
def send_welcome(message):
    """Обработка команды /menu и открытие главного меню"""

    user_id = message.from_user.id
    answer = unknown_user(message)

    if answer is True:
        user_access_level = Work_with_DB().check_access_level_user(user_id=user_id)
        markup = menu_form.create_markup("main_menu", user_access_level)
        if markup:
            bot.send_message(user_id, menu_form.menu_storage["main_menu"]["text"], reply_markup=markup)
            logger.info(f"Главное меню открыто для пользователя: {user_id}")
    else:
        bot.send_message(user_id, text=answer[0], reply_markup=answer[1])
        logger.warning(f"Доступ к меню ограничен для пользователя: {user_id}")


@bot.message_handler(content_types=['text'])
def talk(message):
    text_answer = 'Я пока не умею реагировать на текст. Доступные функции в /menu'
    bot.reply_to(message, text_answer)


# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
@registration_of_keystrokes
def callback_inline(call):
    """Обработчик Inline-запросов"""

    menu_key = call.data
    menu = menu_form.menu_storage.get(menu_key)

    if call.from_user and hasattr(call.from_user, 'id'):
        user_id = call.from_user.id
    else:
        logger.error(f"Unable to determine user ID from call: {call}")
        bot.answer_callback_query(call.id, "Ошибка: данные пользователя не обнаружены.")
        return

    # Счётчик активности пользователя
    Work_with_DB().collect_statistical_user(user_id=user_id)

    # КАЛЕНДАРЬ
    if call.data.startswith(calendar_callback.prefix):
        name, action, year, month, day = call.data.split(calendar_callback.sep)
        date = calendar.calendar_query_handler(bot, call, name, action, year, month, day)

        if action == "DAY":
            date = date.date()
            user_id = call.from_user.id
            if user_id not in user_data:
                user_data[user_id] = {}

            if "first_date" not in user_data[user_id]:
                if date < datetime.datetime.now().date():
                    bot.send_message(call.message.chat.id,
                                     "Вы выбрали прошедшую дату. Пожалуйста, выберите дату снова.")
                    return
                user_data[user_id]["first_date"] = date
                show_calendar(chat_id=call.message.chat.id, title="Дежурство до какой даты (включительно)?")
            else:
                if date < user_data[user_id]["first_date"]:
                    bot.send_message(call.message.chat.id,
                                     "Конечная дата должна быть позже начальной. Пожалуйста, выберите дату снова.")
                    return
                user_data[user_id]["last_date"] = date
                ask_for_name(call.message.chat.id)

        elif action == "CANCEL":
            user_id = call.from_user.id
            bot.send_message(call.message.chat.id, "Операция отменена.")
            if user_id in user_data:
                del user_data[user_id]

    # Обработка выбора имени
    elif call.data.startswith("name_"):
        user_id = call.from_user.id
        name = call.data.split("_")[1]
        user_data[user_id]["name"] = name
        bot.delete_message(call.message.chat.id, call.message.message_id)
        finalize_event(call.message.chat.id, user_id)
    elif call.data == "CANCEL":
        user_id = call.from_user.id
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Операция отменена.")
        if user_id in user_data:
            del user_data[user_id]
    elif call.data == "DELETE":
        user_id = call.from_user.id
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data.startswith("event_"):
        user_id = call.from_user.id
        data = call.data.split('_')
        event_id = data[1]  # Извлекаем идентификатор события
        entered_type = data[2]  # Извлекаем выбранный тип простоя
        logger.debug(f"Entered type received: {entered_type}")
        text_message = call.message.text

        name_entered_button = ''

        dict_button = call.message.json.get('reply_markup', {}).get('inline_keyboard', [])
        for list_buttons in dict_button:
            for buttons in list_buttons:
                name_button = buttons[0].get('text')
                callback = buttons[0].get('callback_data')
                if entered_type in callback:
                    logger.debug(f"Entered type ({entered_type}) matched in callback ({callback})")
                    name_entered_button = name_button

        # Создаем словарь с данными
        response_data = {
            "event_id": event_id,
            "entered_type": name_entered_button
        }

        result = f'{text_message}\n{name_entered_button}'
        answer_erp = post_answer_of_event(response_data)
        logger.debug(f"ERP response received: {answer_erp}")
        # Если отправка response_data в 1С успешна, то выполнить следующий шаг
        if answer_erp is True:
            bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=result)
            return
        # Иначе выполнить:
        else:
            bot.answer_callback_query(call.id, "Ошибка: не удалось отправить данные в 1С. Попробуйте позже.")
            return

    ###

    # Если меню нет вернёт ошибку
    if not menu:
        bot.answer_callback_query(call.id, "Ошибка: меню не найдено.")
        return

    # Если это подменю с функцией
    if "function" in menu:
        try:
            result = menu["function"](call)
        except Exception as error:
            logger.exception(f"Error executing menu function {menu_key}: {error}")
            bot.send_message(user_id, "Произошла ошибка при выполнении команды. Попробуйте снова.")
            return
        if isinstance(result, dict):
            text = result.get('text')
            keyboard = result.get('keyboard')
            bot.send_message(user_id, text=text, reply_markup=keyboard)
        else:
            bot.send_message(user_id, result)
        # Счётчик выполнения функций для сбора статистики
        Work_with_DB().collect_statistical_func(name_func=menu_key)
    # Если это переход на другое меню
    elif "redirect" in menu:
        user_access_level = Work_with_DB().check_access_level_user(user_id=user_id)
        new_menu_key = menu["redirect"]
        markup = menu_form.create_markup(new_menu_key, user_access_level)
        if markup:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_form.menu_storage[new_menu_key]["text"],
                reply_markup=markup
            )
    # Если это обычное меню
    elif "buttons" in menu:
        user_access_level = Work_with_DB().check_access_level_user(user_id=user_id)
        markup = menu_form.create_markup(menu_key, user_access_level)
        if markup:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu["text"],
                reply_markup=markup
            )


def job_every_month():
    if datetime.datetime.today().day != 1:
        Work_with_DB().reset_func_stat('month')
        return


#  Создаёт расписание с рандомным временем для выполнения регулярных задач
schedule_next_run()

schedule.every().day.at('00:00').do(schedule_next_run)
schedule.every().day.at('00:00').do(create_top_chart_func)
schedule.every().day.at('00:00').do(Work_with_DB().reset_func_stat, 'today')
schedule.every().day.at('00:00').do(job_every_month)

schedule.every().minute.do(update_data_door)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Запуск планировщика в отдельном потоке
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.daemon = True  # Поток завершится, если основной поток завершится
scheduler_thread.start()

while True:
    try:
        logger.debug("Запуск основного цикла бота...")
        bot.polling(none_stop=True)
    except KeyboardInterrupt:
        shutdown_message = "Бот остановлен вручную (KeyboardInterrupt)."
        logger.info(shutdown_message)
        bot.send_message(chat_id=dev_id, text=shutdown_message)
        break
    except (requests.exceptions.ReadTimeout, requests.ConnectionError) as req_error:
        logger.info(f"Сетевая ошибка обнаружена: {req_error}. Планируем повтор...")
        time.sleep(5 if isinstance(req_error, requests.exceptions.ReadTimeout) else 60)
    except asyncio.exceptions.TimeoutError as timeout_error:
        logger.error(f"Ошибка: время ожидания истекло: {timeout_error}. Повтор через 10 секунд.")
        time.sleep(10)
    except telebot.apihelper.ApiTelegramException as error_telegram:
        logger.error(f"Ошибка API Telegram {error_telegram}. Уведомление отправлено разработчику.")
        bot.send_message(chat_id=dev_id, text=f"Критическая ошибка: {error_telegram}")
        time.sleep(5)
    except json.JSONDecodeError as json_error:
        logger.error(f"Ошибка обработки JSON: {json_error}. Проверьте переданные данные.")
        bot.send_message(chat_id=dev_id,
                         text="Ошибка обработки данных JSON. Пожалуйста, проверьте корректность данных.",
                         parse_mode="Markdown")
        time.sleep(5)
    except telebot.apihelper.ApiException as api_error:
        logger.error(f"Исключение API Telegram: {api_error}. Повтор через 5 секунд.")
        bot.send_message(chat_id=dev_id, text="Телеграм API не отвечает. Повторение через несколько секунд.",
                         parse_mode="Markdown")
        time.sleep(5)
    except Exception as e:
        frm = inspect.trace()[-1]
        unique_error_id = f"Error_{int(time.time())}"  # Generate a unique ID for the error
        logger.error(f"Непредвиденная ошибка [{unique_error_id}] - {e}", exc_info=e)
        error_details = (
            f"⛔️ *Критическая ошибка обнаружена!* ⛔️\n\n"
            f"*Дата и время:* {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"*Уникальный ID ошибки:* {unique_error_id}\n"
            f"*Файл:* {frm.filename}\n"
            f"*Строка:* {frm.lineno}\n"
            f"*Ошибка:* `{e}`"
        )
        bot.send_message(chat_id=dev_id, text=error_details, parse_mode="Markdown")
        logger.debug(f"Сообщение об ошибке отправлено разработчику (DEV_ID: {dev_id}).")
        time.sleep(5)
