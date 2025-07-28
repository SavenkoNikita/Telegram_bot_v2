import logging
from telebot import types
from src.utils.sql import WorkWithDb

logger = logging.getLogger(__name__)


def handle_promote_to_admin(bot, call):
    """Обработчик для кнопки 'Дать права админа'"""
    try:
        user_id_to_promote = call.data.split('_')[-1]  # Извлекаем ID пользователя из callback_data
        db = WorkWithDb()

        if db.promote_to_admin(user_id_to_promote):
            bot.answer_callback_query(call.id, "Пользователь получил права администратора")
            update_user_management_message(bot, call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Ошибка при изменении прав")
    except Exception as e:
        logger.error(f"Error in handle_promote_to_admin: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")


def handle_demote_to_user(bot, call):
    """Обработчик для кнопки 'Лишить прав админа'"""
    try:
        user_id_to_demote = call.data.split('_')[-1]  # Извлекаем ID пользователя из callback_data
        db = WorkWithDb()

        if db.demote_to_user(user_id_to_demote):
            bot.answer_callback_query(call.id, "Пользователь лишен прав администратора")
            update_user_management_message(bot, call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Ошибка при изменении прав")
    except Exception as e:
        logger.error(f"Error in handle_demote_to_user: {e}")
        bot.answer_callback_query(call.id, "Произошла ошибка")


def update_user_management_message(bot, chat_id, message_id):
    """Обновляет сообщение со списком пользователей и кнопками управления"""
    db = WorkWithDb()
    users = db.get_user_list()

    markup = types.InlineKeyboardMarkup()

    for user in users:
        user_id, first_name, last_name, rights = user
        user_text = f"{first_name} {last_name} ({'admin' if rights == 'admin' else 'user'})"

        if rights == 'user':
            markup.add(types.InlineKeyboardButton(
                text=f"Сделать админом: {user_text}",
                callback_data=f"promote_admin_{user_id}"
            ))
        else:
            markup.add(types.InlineKeyboardButton(
                text=f"Сделать пользователем: {user_text}",
                callback_data=f"demote_user_{user_id}"
            ))

    markup.add(types.InlineKeyboardButton(
        text="Закрыть",
        callback_data="DELETE"
    ))

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Управление правами пользователей:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Error updating user management message: {e}")


def show_user_management(bot, call):
    """Показывает интерфейс управления правами пользователей"""
    try:
        db = WorkWithDb()
        users = db.get_user_list()

        markup = types.InlineKeyboardMarkup()

        for user in users:
            user_id, first_name, last_name, rights = user
            user_text = f"{first_name} {last_name} ({'admin' if rights == 'admin' else 'user'})"

            if rights == 'user':
                markup.add(types.InlineKeyboardButton(
                    text=f"Сделать админом: {user_text}",
                    callback_data=f"promote_admin_{user_id}"
                ))
            else:
                markup.add(types.InlineKeyboardButton(
                    text=f"Сделать пользователем: {user_text}",
                    callback_data=f"demote_user_{user_id}"
                ))

        markup.add(types.InlineKeyboardButton(
            text="Закрыть",
            callback_data="DELETE"
        ))

        bot.send_message(
            call.message.chat.id,
            "Управление правами пользователей:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Error in show_user_management: {e}")
        bot.send_message(call.message.chat.id, "Произошла ошибка при загрузке списка пользователей")
