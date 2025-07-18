import datetime

from src.utils.functions import show_calendar, ask_for_name, user_data, ask_for_notification_text


def handle_calendar_callback(bot, call, calendar, calendar_callback):
    name, action, year, month, day = call.data.split(calendar_callback.sep)
    date = calendar.calendar_query_handler(bot, call, name, action, year, month, day)

    if action == "DAY":
        date = date.date()
        user_id = call.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {'calendar_mode': 'range'}

        calendar_mode = user_data[user_id].get('calendar_mode', 'range')
        notification_mode = user_data[user_id].get('notification_mode', False)

        if notification_mode:
            user_data[user_id]["selected_date"] = date
            ask_for_notification_text(call.message.chat.id, date)
            return

        if calendar_mode == 'range':
            if date < datetime.datetime.now().date():
                bot.send_message(call.message.chat.id,
                                 "Вы выбрали прошедшую дату. Пожалуйста, выберите дату снова.")
                return

            if "first_date" not in user_data[user_id]:
                user_data[user_id]["first_date"] = date
                show_calendar(chat_id=call.message.chat.id,
                              title="Дежурство до какой даты (включительно)?",
                              select_range=True)
            else:
                if date < user_data[user_id]["first_date"]:
                    bot.send_message(call.message.chat.id,
                                     "Конечная дата должна быть позже начальной. Пожалуйста, выберите дату снова.")
                    return
                user_data[user_id]["last_date"] = date
                ask_for_name(call.message.chat.id)
        else:
            user_data[user_id]["selected_date"] = date
            if 'date_handler' in user_data[user_id]:
                user_data[user_id]['date_handler'](call.message.chat.id, date)
            else:
                bot.send_message(call.message.chat.id, f"Выбрана дата: {date.strftime('%d.%m.%Y')}")
            del user_data[user_id]

    elif action == "CANCEL":
        user_id = call.from_user.id
        bot.send_message(call.message.chat.id, "Операция отменена.")
        if user_id in user_data:
            del user_data[user_id]
