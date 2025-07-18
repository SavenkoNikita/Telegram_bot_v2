import logging
from src.utils.functions import post_answer_of_event

logger = logging.getLogger(__name__)


def handle_event_callback(bot, call):
    user_id = call.from_user.id
    data = call.data.split('_')
    event_id = data[1]
    entered_type = data[2]
    logger.debug(f"Entered type received: {entered_type}")
    text_message = call.message.text

    name_entered_button = ''

    dict_button = call.message.json.get('reply_markup', {}).get('inline_keyboard', [])
    for list_buttons in dict_button:
        for buttons in list_buttons:
            name_button = buttons.get('text')
            callback = buttons.get('callback_data')
            if entered_type in callback:
                logger.debug(f"Entered type ({entered_type}) matched in callback ({callback})")
                name_entered_button = name_button

    response_data = {
        "event_id": event_id,
        "entered_type": name_entered_button
    }

    result = f'{text_message}\n{name_entered_button}'
    answer_erp = post_answer_of_event(response_data)
    logger.debug(f"ERP response received: {answer_erp}")

    if answer_erp is True:
        bot.edit_message_text(chat_id=user_id, message_id=call.message.message_id, text=result)
    else:
        bot.answer_callback_query(call.id, "Ошибка: не удалось отправить данные в 1С. Попробуйте позже.")
