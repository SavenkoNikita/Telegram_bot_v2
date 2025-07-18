import logging
import os
from datetime import datetime

# import telebot
from telebot import types
from src.utils.sql import WorkWithDb
from src.utils.functions import user_data, bot

logger = logging.getLogger(__name__)

# bot_token = os.getenv('BOT_TOKEN')
# if not bot_token:
#     raise ValueError("BOT_TOKEN is missing in environment variables")
# bot = telebot.TeleBot(bot_token)

id_dev = os.getenv('DEV_ID')


def handle_swap_dej_callback(bot, call):
    user_id = call.from_user.id
    db = WorkWithDb()

    # Получаем список 7 ближайших дежурств, исключая свои
    future_dej = db.get_future_dej_list(exclude_user_id=user_id)

    if not future_dej:
        bot.send_message(user_id, "❌ Нет доступных дежурств для обмена.")
        return

    # Проверяем, есть ли у пользователя будущие дежурства
    user_next_dej = db.get_user_next_dej(user_id)
    if not user_next_dej:
        bot.send_message(user_id, "❌ У вас нет запланированных дежурств для обмена.")
        return

    # Создаем клавиатуру с доступными дежурствами
    markup = types.InlineKeyboardMarkup(row_width=1)

    for dej in future_dej:
        # Форматируем даты в дд.мм.гггг
        first_date = datetime.strptime(dej[1], '%Y-%m-%d').strftime('%d.%m.%Y')
        last_date = datetime.strptime(dej[2], '%Y-%m-%d').strftime('%d.%m.%Y')

        btn_text = f"{dej[3]} ({first_date} - {last_date})"
        markup.add(types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"swap_dej_{dej[0]}"  # dej_id
        ))

    # Добавляем информацию о своем дежурстве
    user_first_date = datetime.strptime(user_next_dej[1], '%Y-%m-%d').strftime('%d.%m.%Y')
    user_last_date = datetime.strptime(user_next_dej[2], '%Y-%m-%d').strftime('%d.%m.%Y')

    bot.send_message(
        user_id,
        f"Ваше дежурство: {user_first_date} - {user_last_date}\n\n"
        "Выберите дежурство, с которым хотите поменяться:",
        reply_markup=markup
    )

    # Добавляем кнопку отмены отдельным рядом
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="CANCEL"
    ))

    bot.send_message(
        user_id,
        "Или отмените действие:",
        reply_markup=cancel_markup
    )


def handle_confirm_swap_dej(bot, call, dej_id):
    from_user_id = call.from_user.id
    db = WorkWithDb()

    # Получаем информацию о дежурстве, с которым хотим поменяться
    target_dej = db.get_dej_by_id(dej_id)
    if not target_dej:
        bot.send_message(from_user_id, "Ошибка: дежурство не найдено.")
        return

    # Проверяем, что пользователь не пытается поменяться с самим собой
    if target_dej[4] == from_user_id:  # target_dej[4] - user_id
        bot.send_message(from_user_id, "❌ Нельзя поменяться дежурством с самим собой.")
        return

    # Получаем информацию о текущем дежурстве пользователя
    user_dej = db.get_user_next_dej(from_user_id)
    if not user_dej:
        bot.send_message(from_user_id, "У вас нет запланированных дежурств.")
        return

    # Сохраняем данные для подтверждения
    user_data[from_user_id] = {
        'swap_dej': {
            'target_dej_id': dej_id,
            'user_dej_id': user_dej[0],
            'target_user_id': target_dej[4]  # предполагаем, что в таблице есть user_id
        }
    }

    # Отправляем запрос на подтверждение второму пользователю
    target_user_id = target_dej[4]
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_swap_{from_user_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_swap_{from_user_id}")
    )

    def format_date_for_display(date_str):
        return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')

    bot.send_message(
        target_user_id,
        f"Пользователь {call.from_user.first_name} хочет поменяться с вами дежурствами:\n"
        f"Ваше дежурство: {format_date_for_display(target_dej[1])} - {format_date_for_display(target_dej[2])}\n"
        f"Его дежурство: {format_date_for_display(user_dej[1])} - {format_date_for_display(user_dej[2])}\n\n"
        f"Вы согласны?",
        reply_markup=markup
    )

    bot.send_message(
        from_user_id,
        f"Запрос на обмен дежурствами отправлен {target_dej[3]}."
    )


def process_swap_confirmation(bot, call, from_user_id, confirmed):
    target_user_id = call.from_user.id
    db = WorkWithDb()

    # Проверяем наличие данных обмена
    if from_user_id not in user_data or 'swap_dej' not in user_data[from_user_id]:
        bot.send_message(target_user_id, "❌ Ошибка: данные обмена не найдены или устарели.")
        return

    swap_data = user_data[from_user_id]['swap_dej']

    # Получаем актуальные данные о дежурствах
    target_dej = db.get_dej_by_id(swap_data['target_dej_id'])
    user_dej = db.get_dej_by_id(swap_data['user_dej_id'])

    # Проверяем, что дежурства все еще доступны
    if not target_dej or not user_dej:
        bot.send_message(from_user_id, "❌ Ошибка: одно из дежурств больше не доступно.")
        bot.send_message(target_user_id, "❌ Ошибка: дежурство больше не доступно.")
        if from_user_id in user_data:
            del user_data[from_user_id]
        return

    # Функция для форматирования дат
    def format_date_range(start, end):
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').strftime('%d.%m.%Y')
            end_date = datetime.strptime(end, '%Y-%m-%d').strftime('%d.%m.%Y')
            return f"{start_date} - {end_date}"
        except ValueError as e:
            logger.error(f"Ошибка форматирования даты: {e}")
            return f"{start} - {end}"  # Возвращаем в исходном формате, если не удалось преобразовать

    # Форматируем даты для сообщений
    target_dates = format_date_range(target_dej[1], target_dej[2])
    user_dates = format_date_range(user_dej[1], user_dej[2])

    if confirmed:
        try:
            # Меняем дежурства местами в БД
            if db.swap_dej_dates(swap_data['user_dej_id'], swap_data['target_dej_id']):
                # Успешный обмен
                success_msg = "🔄 Обмен дежурствами успешно выполнен!\n\n"
                bot.send_message(
                    from_user_id,
                    success_msg +
                    f"Ваше новое дежурство: {target_dates}\n" +
                    f"Ранее было: {user_dates}"
                )
                bot.send_message(
                    target_user_id,
                    success_msg +
                    f"Ваше новое дежурство: {user_dates}\n" +
                    f"Ранее было: {target_dates}"
                )
            else:
                # Ошибка обмена
                error_msg = "❌ Не удалось выполнить обмен дежурствами. Попробуйте позже."
                bot.send_message(from_user_id, error_msg)
                bot.send_message(target_user_id, error_msg)
        except Exception as e:
            error_msg = f"❌ Ошибка при обмене дежурствами: {str(e)}"
            if "UNIQUE constraint" in str(e):
                error_msg = ("❌ Ошибка: невозможно выполнить обмен, так как новые даты конфликтуют "
                             "с существующими дежурствами. Пожалуйста, выберите другие даты.")
            bot.send_message(from_user_id, error_msg)
            bot.send_message(target_user_id, error_msg)
            logger.error(f"Ошибка при обмене дежурствами: {e}")
    else:
        # Обмен отклонен
        bot.send_message(
            from_user_id,
            f"❌ {call.from_user.first_name} отклонил ваш запрос на обмен дежурствами."
        )
        bot.send_message(
            target_user_id,
            "❌ Вы отклонили запрос на обмен дежурствами."
        )

    # Очищаем данные обмена
    if from_user_id in user_data:
        del user_data[from_user_id]
