import datetime
import inspect
import logging
import os
import dotenv
import telebot
from src.utils.logger_setup import setup_logger


def get_env_variable(key):
    """Fetch environment variable and raise exception if not set."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Environment variable '{key}' is not set.")
    return value


dotenv.load_dotenv()
bot = telebot.TeleBot(get_env_variable('BOT_TOKEN'))
dev_id = get_env_variable('DEV_ID')

logger = setup_logger(log_file="bot.log", level=logging.INFO)


def registration_of_keystrokes(func):
    """Log details of user interactions with Telegram bot."""

    def wrapper(callback, *args, **kwargs):
        datetime_now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        user = callback.from_user
        full_name_user = ' '.join(filter(None, [user.first_name, user.last_name, user.username]))

        logger.log(logging.DEBUG,
                   "Date and time: %s | Function: %s() | User: %s (ID: %s) pressed button: %s",
                   datetime_now,
                   func.__name__,
                   full_name_user,
                   user.id,
                   callback.data
                   )

        return func(callback, *args, **kwargs)

    return wrapper


def error_handling(func):
    """Send error details to developer and log them."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            frm = inspect.trace()[-1]
            file_name, line_error = frm[1], frm[2]

            error_message = (
                f"Date and time: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"Function: {func.__name__}()\n"
                f"File: {file_name}\n"
                f"Line: {line_error}\n"
                f"Error: {e}"
            )
            logger.error(error_message)
            bot.send_message(chat_id=dev_id, text=error_message)

    return wrapper
