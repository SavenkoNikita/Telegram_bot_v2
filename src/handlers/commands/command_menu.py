from src.utils import menu_formation
from src.utils.sql import WorkWithDb


def process_menu_command(user_id):
    """Возвращает клавиатуру с главным меню

    :return title_menu, markup"""

    user_access_level = WorkWithDb().check_access_level_user(user_id=user_id)
    title_menu = menu_formation.menu_storage["main_menu"]["text"]
    markup = menu_formation.create_markup(menu_key="main_menu", user_access_level=user_access_level)

    return title_menu, markup
