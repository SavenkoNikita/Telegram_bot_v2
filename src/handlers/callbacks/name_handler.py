from src.utils.functions import finalize_event, user_data


def handle_name_callback(bot, call):
    user_id = call.from_user.id
    name = call.data.split("_")[1]
    user_data[user_id]["name"] = name
    bot.delete_message(call.message.chat.id, call.message.message_id)
    finalize_event(call.message.chat.id, user_id)
