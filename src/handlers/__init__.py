from .commands.command_start import process_start_command
from .commands.command_menu import process_menu_command
from ..utils.functions import create_instant_notification
from .callbacks import (
    handle_calendar_callback,
    handle_event_callback,
    handle_name_callback,
    handle_cancel_callback,
    handle_delete_callback,
    handle_menu_callback,
    handle_swap_dej_callback,
    handle_vacation_verify,
    handle_vacation_cancel
)
import logging

logger = logging.getLogger(__name__)

# Явно указываем какие объекты будут доступны при импорте из этого пакета
__all__ = [
    'process_start_command',
    'process_menu_command',
    'handle_calendar_callback',
    'handle_event_callback',
    'handle_name_callback',
    'handle_cancel_callback',
    'handle_delete_callback',
    'handle_menu_callback',
    'handle_swap_dej_callback',
    'handle_vacation_verify',
    'handle_vacation_cancel',
    'create_instant_notification',
]


# Инициализационный код пакета (если требуется)
def init_handlers():
    """Функция инициализации обработчиков с логированием"""
    logger.info("Initializing handlers package")


def get_handler(callback_type):
    """Фабрика обработчиков callback-запросов"""
    handlers = {
        'calendar': handle_calendar_callback,
        'name': handle_name_callback,
        'event': handle_event_callback,
        'cancel': handle_cancel_callback,
        'delete': handle_delete_callback,
        'menu': handle_menu_callback
    }
    return handlers.get(callback_type)


# Вызываем инициализацию при импорте пакета
init_handlers()
