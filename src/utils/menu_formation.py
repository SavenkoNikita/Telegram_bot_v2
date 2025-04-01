from telebot import types
import logging

from src.utils import functions
from src.utils.functions import change_status_news


logger = logging.getLogger(__name__)

def building_func(call):
    """Временная заглушка для функций, которые еще не реализованы."""
    name_user = call.from_user.first_name
    text = f'Наберитесь терпения, {name_user}. Эта функция станет доступна позже. Следите за обновлениями!'
    logger.info(f"Вызвана заглушка функции для пользователя: {name_user}")
    return text


menu_storage = {  # Хранилище меню, подменю и функций.
    "main_menu": {
        "text": "🏠 Главное меню:",
        "buttons": {
            "button1": {
                "name": "⚙️ Основные функции",
                "access_level": "all",
                "callback": "button_main_functions"},
            "button2": {
                "name": "🔔 Управление подписками",
                "access_level": "all",
                "callback": "button_managing_subscriptions"},
            # "button3": {
            #     "name": "Настройка аккаунта",
            #     "access_level": "admin",
            #     "callback": "button_account_management"},
            "button4": {
                "name": "✨ Дополнительные функции",
                "access_level": "all",
                "callback": "button_additional_functions"},
        }
    },
    "button_main_functions": {
        "text": "⚙️ Основные функции:",
        "buttons": {
            "button": {
                "name": "Дежурства в IT",
                "access_level": "all",
                "callback": "button_menu_dej"},
            # "button1": {
            #     "name": "Узнать кто дежурный",
            #     "access_level": "all",
            #     "callback": "button_dej"},
            # "button2": {
            #     "name": "📆 Внести дежурство в календарь",
            #     "access_level": "admin",
            #     "callback": "button_ins_dej"},
            "button3": {
                "name": "Инвентаризация",
                "access_level": "admin",
                "callback": "button_invent"},
            "button4": {
                "name": "Создать уведомление",
                "access_level": "admin",
                "callback": "button_create_notif"},
            "button5": {
                "name": "📅 Остаток дней отпуска",
                "access_level": "all",
                "callback": "button_vacation"},
            "button6": {
                "name": "Создать лот",
                "access_level": "admin",
                "callback": "button_create_lot"},
            "button7": {
                "name": "⚡ Мгновенное уведомление",
                "access_level": "admin",
                "callback": "button_urgent_message"},
            "button8": {
                "name": "🏠 Главное меню",
                "access_level": "all",
                "callback": "main_menu"}
        }
    },
    "button_managing_subscriptions": {
        "text": "🔔 Управление подписками:",
        "buttons": {
            "button1": {
                "name": "Новости IT-отдела",
                "access_level": "all",
                "callback": "button_subscribe"},
            "button3": {
                "name": "Мониторинг дефростеров",
                "access_level": "admin",
                "callback": "button_defrosters"},
            "button4": {
                "name": "Мониторинг неисправных датчиков",
                "access_level": "admin",
                "callback": "button_all_sensor"},
            "button5": {
                "name": "Барахолка",
                "access_level": "all",
                "callback": "button_sub_bar"},
            # "button6": {
            #     "name": "Отписаться от барахолки",
            #     "access_level": "all",
            #     "callback": "button_unsub_bar"},
            "button7": {
                "name": "🏠 Главное меню",
                "access_level": "all",
                "callback": "main_menu"},
        }
    },
    "button_additional_functions": {
        "text": "✨ Дополнительные функции:",
        "buttons": {
            "button1": {
                "name": "✉️ Написать разработчику",
                "access_level": "all",
                "url": "t.me/nikita_it_remit"},
            "button2": {
                "name": "📲 Приложение 'Ремит сотрудник'",
                "access_level": "all",
                "callback": "button_get_app_android"},
            "button3": {
                "name": "Получить список всех пользователей",
                "access_level": "admin",
                "callback": "button_all_users"},
            "button4": {
                "name": "Дать пользователю права админа",
                "access_level": "admin",
                "callback": "button_admin"},
            "button5": {
                "name": "Лишить пользователя прав админа",
                "access_level": "admin",
                "callback": "button_user"},
            "button6": {
                "name": "🏠 Главное меню",
                "access_level": "all",
                "callback": "main_menu"},
        }
    },

    "back_to_main": {
        "name": "redirect",
        "access_level": "all",
        "callback": "main_menu"},

    "button_registration": {
        "function": functions.register,
        "name": "Зарегистрироваться",
        "callback": "button_registration"
    },

    ### Дежурный ###
    "button_menu_dej": {
        "text": "Дежурства в IT:",
        "buttons": {
            "button1": {
                "name": "Узнать кто дежурный",
                "access_level": "all",
                "callback": "button_dej"},
            "button2": {
                "name": "📆 Внести дежурство в календарь",
                "access_level": "admin",
                "callback": "button_ins_dej"},
            "button3": {
                "name": "Внести изменения",
                "access_level": "admin",
                "callback": "button_upd_dej"},
            "button4": {
                "name": "🔙 Основные функции",
                "access_level": "all",
                "callback": "button_main_functions"},
            "button5": {
                "name": "🏠 Главное меню",
                "access_level": "all",
                "callback": "main_menu"}
        }
    },
    "button_dej": {
        "text": "Узнать кто дежурный:",
        "buttons": {
            "button1": {
                "name": "Имя следующего дежурного",
                "access_level": "all",
                "callback": "button_dej_1"},
            "button2": {
                "name": "Список дежурных",
                "access_level": "all",
                "callback": "button_dej_2"},
            "button3": {
                "name": "🔙 Дежурства в IT",
                "access_level": "all",
                "callback": "button_menu_dej"},
            "button4": {
                "name": "🏠 Главное меню",
                "access_level": "all",
                "callback": "main_menu"}
        }
    },

    "button_create_notif": {
        "text": "Создать уведомление",
        "buttons": {
            "button1": {
                "name": "Для всех",
                "access_level": "admin",
                "callback": "button_notif_all"},
            "button2": {
                "name": "Для подписчиков IT-отдела",
                "access_level": "admin",
                "callback": "button_notif_it"},
            "button3": {
                "name": "Для барахолки",
                "access_level": "admin",
                "callback": "button_notif_bar"},
            "button4": {
                "name": "🔙 Основные функции",
                "access_level": "all",
                "callback": "button_main_functions"},
            "button5": {
                "name": "🏠 Главное меню",
                "access_level": "all",
                "callback": "main_menu"}
        }
    },

    "button_dej_1": {"function": functions.dej_name},
    "button_dej_2": {"function": functions.list_dej},
    "button_ins_dej": {"function": functions.fill_schedule_dej},
    ###
    "button_invent": {"function": building_func},
    "button_admin": {"function": building_func},
    "button_user": {"function": building_func},
    "button_subscribe": {"function": change_status_news},
    "button_defrosters": {"function": building_func},
    "button_all_sensor": {"function": building_func},
    # "button_log_out": {"function": building_func},
    # "button_sticker": {"function": building_func},
    # "button_feed_back": {"function": building_func},
    "button_get_app_android": {"function": functions.get_app_remit_employee},
    # "button_random": {"function": building_func},
    "button_all_users": {"function": building_func},
    "button_vacation": {"function": building_func},
    "button_create_lot": {"function": building_func},
    "button_urgent_message": {"function": building_func},
    "button_sub_bar": {"function": building_func},
    "button_notif_all": {"function": building_func},
    "button_notif_it": {"function": building_func},
    "button_notif_bar": {"function": building_func},
    "button_upd_dej": {"function": building_func}
}

new_menu_storage = {
"main_menu": {
    "title": "🏠 Главное меню:",
    "access_level": "all",
    "buttons": {
        "button_main_functions": {
            "title": "⚙️ Основные функции",
            "access_level": "all",
            "buttons": {
                "button_menu_dej": {
                    "title": "Дежурства в IT",
                    "access_level": "all",
                    "buttons": {
                        "button_dej": {
                            "title": "Узнать кто дежурный",
                            "access_level": "all",
                            "buttons": {
                                "button_dej_1": {
                                    "title": "Имя следующего дежурного",
                                    "access_level": "all",
                                    "function": functions.dej_name},
                                "button_dej_2": {
                                    "title": "Список дежурных",
                                    "access_level": "all",
                                    "function": functions.list_dej}
                            }
                        },
                        "button_ins_dej": {
                            "title": "📆 Внести дежурство в календарь",
                            "access_level": "admin",
                            "function": functions.fill_schedule_dej},
                        "button_upd_dej": {
                            "title": "Внести изменения",
                            "access_level": "admin",
                            "function": building_func}
                    }
                },
                "button_invent": {
                    "title": "Инвентаризация",
                    "access_level": "admin",
                    "function": building_func},
                "button_create_notif": {
                    "title": "Создать уведомление",
                    "access_level": "admin",
                    "function": building_func},
                "button_vacation": {
                    "title": "📅 Остаток дней отпуска",
                    "access_level": "all",
                    "function": building_func},
                "button_create_lot": {
                    "title": "Создать лот",
                    "access_level": "admin",
                    "function": building_func},
                "button_urgent_message": {
                    "title": "⚡ Мгновенное уведомление",
                    "access_level": "admin",
                    "function": building_func}
            }
        },
        "button_managing_subscriptions": {
            "title": "🔔 Управление подписками",
            "access_level": "all",
            "buttons": {
                "button_subscribe": {
                    "title": "Новости IT-отдела",
                    "access_level": "all",
                    "function": change_status_news},
                "button_defrosters": {
                    "title": "Мониторинг дефростеров",
                    "access_level": "admin",
                    "function": building_func},
                "button_all_sensor": {
                    "title": "Мониторинг неисправных датчиков",
                    "access_level": "admin",
                    "function": building_func},
                "button_sub_bar": {
                    "title": "Барахолка",
                    "access_level": "all",
                    "function": building_func}
            }
        },
        "button_additional_functions": {
            "title": "✨ Дополнительные функции",
            "access_level": "all",
            "buttons": {
                "button_send_dev": {
                    "name": "✉️ Написать разработчику",
                    "access_level": "all",
                    "url": "t.me/nikita_it_remit"},
                "button_get_app_android": {
                    "name": "📲 Приложение 'Ремит сотрудник'",
                    "access_level": "all",
                    "function": functions.get_app_remit_employee},
                "button_all_users": {
                    "name": "Получить список всех пользователей",
                    "access_level": "admin",
                    "function": building_func},
                "button_rights": {
                    "name": "Изменить права пользователя",
                    "access_level": "admin",
                    "buttons": {
                        "button_admin": {
                            "name": "Дать пользователю права админа",
                            "access_level": "admin",
                            "function": building_func},
                        "button_user": {
                            "name": "Лишить пользователя прав админа",
                            "access_level": "admin",
                            "function": building_func}
                    }}}}}}}


# Функция для создания клавиатуры на основе данных из хранилища
def create_markup(menu_key, user_access_level):
    menu = menu_storage.get(menu_key)
    if not menu or "buttons" not in menu:
        return None

    markup = types.InlineKeyboardMarkup()
    for buttons, values in menu["buttons"].items():
        name_button = values['name']
        access_level = values['access_level']

        if 'callback' in values:
            callback_data = values['callback']
            if user_access_level == 'admin':
                markup.add(types.InlineKeyboardButton(text=name_button, callback_data=callback_data))
            elif user_access_level == 'user' and access_level == 'all':
                markup.add(types.InlineKeyboardButton(text=name_button, callback_data=callback_data))

        elif 'url' in values:
            url = values['url']
            if user_access_level == 'admin':
                markup.add(types.InlineKeyboardButton(text=name_button, url=url))
            elif user_access_level == 'all':
                markup.add(types.InlineKeyboardButton(text=name_button, url=url))

    return markup
