import logging
from datetime import datetime

from src.utils.sql import WorkWithDb

logger = logging.getLogger(__name__)


def handle_dej_history_callback(bot, call):
    """Обработчик для получения истории дежурств"""
    try:
        db = WorkWithDb()
        history = db.get_dej_history()

        if not history:
            bot.send_message(call.message.chat.id, "История дежурств за последние 45 дней не найдена.")
            return

        result = ["История дежурств за последние 45 дней:\n"]
        for item in history:
            first_date = datetime.strptime(item[0], '%Y-%m-%d').strftime('%d.%m.%Y')
            last_date = datetime.strptime(item[1], '%Y-%m-%d').strftime('%d.%m.%Y')
            name = item[2]
            result.append(f"{first_date} - {last_date}: {name}")

        # Разбиваем сообщение на части, если оно слишком длинное
        message = "\n".join(result)
        for i in range(0, len(message), 4000):
            bot.send_message(call.message.chat.id, message[i:i + 4000])

    except Exception as e:
        logger.error(f"Error in dej history handler: {e}")
        bot.send_message(call.message.chat.id, "Произошла ошибка при получении истории дежурств.")
