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
from pygments.lexers import markup
from telebot_calendar import Calendar, CallbackData

# Импортируем всё через единый интерфейс handlers
from src.handlers import (
    process_start_command,
    process_menu_command,
    handle_calendar_callback,
    handle_event_callback,
    handle_name_callback,
    handle_cancel_callback,
    handle_menu_callback,
    handle_delete_callback,
    handle_vacation_verify,
    handle_vacation_cancel

)
from src.utils.functions import (
    unknown_user,
    schedule_next_run,
    create_top_chart_func,
    user_data,
    save_notification_to_db,
    process_inn_input
)
from src.utils.interactions_with_services import ExchangeWithErp as ERP
from src.utils.logger_setup import setup_logger
from src.utils.sql import StatisticsManager, WorkWithDb
from src.utils.tracking_sensors import TrackingSensor

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


@bot.message_handler(commands=['start', 'menu'])
def command_handler(message):
    """Обработчик команд"""

    text_message = message.text
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    if text_message == '/start':
        data = process_start_command(user_id, first_name, last_name, username)
        hello_message = data[0]
        button = data[1]
        bot.send_message(chat_id=user_id, text=hello_message, reply_markup=button)

    elif unknown_user(message) is True:  # Если пользователь есть в БД

        if text_message == '/menu':
            data_menu = process_menu_command(user_id)
            title_menu = data_menu[0]
            menu = data_menu[1]
            bot.send_message(chat_id=user_id, text=title_menu, reply_markup=menu)
            logger.info(f"Главное меню открыто для пользователя: {username} ({user_id})")
        else:
            pass


@bot.message_handler(content_types=['text'])
def talk(message):
    user_id = message.from_user.id

    # Проверяем, ожидаем ли мы текст уведомления
    if user_id in user_data and user_data[user_id].get('waiting_for_text', False):
        text = message.text
        if save_notification_to_db(message.chat.id, text):
            # После успешного сохранения возвращаем в главное меню
            data_menu = process_menu_command(user_id)
            title_menu = data_menu[0]
            menu = data_menu[1]
            bot.send_message(chat_id=user_id, text=title_menu, reply_markup=menu)
        return

    # Добавляем обработку ИНН для верификации
    if user_id in user_data and user_data[user_id].get('waiting_for_inn', False):
        process_inn_input(message)
        return

    text_answer = 'Я пока не умею реагировать на текст. Доступные функции в /menu'
    bot.reply_to(message, text_answer)


# Обработчик callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_dispatcher(call):
    """Центральный диспетчер callback-запросов"""
    try:
        # Логируем входящий callback
        logger.debug(f"Processing callback: {call.data} from user {call.from_user.id}")

        # Обработка CANCEL и DELETE в первую очередь
        if call.data == "CANCEL":
            handle_cancel_callback(bot, call)
            return
        elif call.data == "DELETE":
            handle_delete_callback(bot, call)
            return
        elif call.data == "vacation_verify":
            handle_vacation_verify(bot, call)
            return
        elif call.data == "vacation_cancel":
            handle_vacation_cancel(bot, call)
            return

        # Статистика активности
        StatisticsManager().collect_statistical_user(user_id=call.from_user.id)

        # Маршрутизация остальных callback'ов
        if call.data.startswith(calendar_callback.prefix):
            handle_calendar_callback(bot, call, calendar, calendar_callback)
        elif call.data.startswith("name_"):
            handle_name_callback(bot, call)
        elif call.data.startswith("event_"):
            handle_event_callback(bot, call)
        else:
            handle_menu_callback(bot, call, call.data)

    except Exception as error:
        logger.error(f"Callback error: {error}", exc_info=True)
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка. Попробуйте позже.")


@bot.callback_query_handler(func=lambda call: call.data in ["vacation_verify", "vacation_cancel"])
def handle_vacation_callbacks(call):
    if call.data == "vacation_verify":
        handle_vacation_verify(bot, call)
    elif call.data == "vacation_cancel":
        handle_vacation_cancel(bot, call)


def job_every_month(func):
    """Выполняет функцию если сегодня 1-е число месяца"""

    if datetime.datetime.today().day == 1:
        func()
        return


#  Создаёт расписание с рандомным временем для выполнения регулярных задач
schedule_next_run()

schedule.every().day.at('00:00').do(schedule_next_run)
schedule.every().day.at('00:00').do(create_top_chart_func)
schedule.every().day.at('00:00').do(StatisticsManager().reset_func_stat_day)
schedule.every().day.at('00:00').do(job_every_month, StatisticsManager().reset_func_stat_month)
# Добавляем очистку старых событий раз в неделю
schedule.every().monday.at('00:30').do(lambda: WorkWithDb().clean_old_events(30))

# schedule.every().minute.do(update_data_door)
schedule.every(10).seconds.do(ERP().in_out)
schedule.every(1).minutes.do(TrackingSensor().check_all_sensors)


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
        bot.stop_polling()
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
        unique_error_id = f"Error_{int(time.time())}"
        logger.error(f"Непредвиденная ошибка [{unique_error_id}] - {e}", exc_info=e)
        error_details = (
            f"⛔️ Критическая ошибка обнаружена!\n\n"
            f"Дата и время: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"Уникальный ID ошибки: {unique_error_id}\n"
            f"Файл: {frm.filename}\n"
            f"Строка: {frm.lineno}\n"
            f"Ошибка: {str(e)}"
        )
        bot.send_message(chat_id=dev_id, text=error_details)  # Убрали parse_mode="Markdown"
        logger.debug(f"Сообщение об ошибке отправлено разработчику (DEV_ID: {dev_id}).")
        time.sleep(5)
