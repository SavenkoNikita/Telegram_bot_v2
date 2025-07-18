import logging
import src.utils.menu_formation as menu_form
from src.utils.sql import WorkWithDb, StatisticsManager

logger = logging.getLogger(__name__)


def handle_menu_callback(bot, call, menu_key):
    user_id = call.from_user.id
    menu = menu_form.menu_storage.get(menu_key)

    if not menu:
        bot.answer_callback_query(call.id, "Ошибка: меню не найдено.")
        return

    if "function" in menu:
        try:
            StatisticsManager().collect_statistical_func(name_func=menu_key)
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
    elif "redirect" in menu:
        user_access_level = WorkWithDb().check_access_level_user(user_id=user_id)
        new_menu_key = menu["redirect"]
        markup = menu_form.create_markup(new_menu_key, user_access_level)
        if markup:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu_form.menu_storage[new_menu_key]["text"],
                reply_markup=markup
            )
    elif "buttons" in menu:
        user_access_level = WorkWithDb().check_access_level_user(user_id=user_id)
        markup = menu_form.create_markup(menu_key, user_access_level)
        if markup:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=menu["text"],
                reply_markup=markup
            )
