from datetime import datetime

from src.utils.functions import show_calendar, ask_for_name, user_data, ask_for_notification_text


def handle_calendar_callback(bot, call, calendar, calendar_callback):
    name, action, year, month, day = call.data.split(calendar_callback.sep)
    date = calendar.calendar_query_handler(bot, call, name, action, year, month, day)

    if action == "DAY":
        date = date.date()
        user_id = call.from_user.id

        if user_id not in user_data:
            user_data[user_id] = {}

        # Проверяем режим работы с календарём
        if user_data[user_id].get('calendar_mode') == 'range':
            if date < datetime.now().date():
                bot.send_message(call.message.chat.id,
                                 "Вы выбрали прошедшую дату. Пожалуйста, выберите дату снова.")
                return

            if "first_date" not in user_data[user_id]:
                user_data[user_id]["first_date"] = date
                # Запрашиваем конечную дату
                bot.send_message(
                    call.message.chat.id,
                    "Дежурство до какой даты (включительно)?",
                    reply_markup=calendar.create_calendar(
                        name=calendar_callback.prefix,
                        year=datetime.now().year,
                        month=datetime.now().month
                    )
                )
            else:
                if date < user_data[user_id]["first_date"]:
                    bot.send_message(call.message.chat.id,
                                     "Конечная дата должна быть позже начальной. Пожалуйста, выберите дату снова.")
                    return
                user_data[user_id]["last_date"] = date
                ask_for_name(call.message.chat.id)
