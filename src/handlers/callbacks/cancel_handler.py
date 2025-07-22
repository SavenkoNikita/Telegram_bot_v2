from src.utils.functions import user_data
import logging

logger = logging.getLogger(__name__)


def handle_cancel_callback(bot, call):
    user_id = call.from_user.id
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Операция отменена.")
    if user_id in user_data:
        del user_data[user_id]


def handle_delete_callback(bot, call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)  # Добавляем подтверждение обработки
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        bot.answer_callback_query(call.id, "Не удалось удалить сообщение")
