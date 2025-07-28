from src.utils.functions import user_data, bot


def handle_vacation_verify(bot, call):
    """Обработчик для кнопки верификации отпуска"""
    user_id = call.from_user.id
    bot.send_message(user_id, "Пожалуйста, введите ваш 12-значный ИНН:")
    user_data[user_id] = {'waiting_for_inn': True}


def handle_vacation_cancel(bot, call):
    """Обработчик для отмены верификации отпуска"""
    user_id = call.from_user.id
    bot.send_message(user_id, "Верификация отменена. Вы можете пройти её позже.")
    if user_id in user_data:
        del user_data[user_id]
