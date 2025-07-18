from src.utils.functions import user_data


def handle_cancel_callback(bot, call):
    user_id = call.from_user.id
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "Операция отменена.")
    if user_id in user_data:
        del user_data[user_id]


def handle_delete_callback(bot, call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
