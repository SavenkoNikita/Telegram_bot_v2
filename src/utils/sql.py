import datetime
import logging
import os
import sqlite3


class WorkWithDb:
    """Класс для обмена с базой данных"""

    logger = logging.getLogger("Work_with_DB")

    def __init__(self):
        self.db_path = self.create_db_if_not()
        self.sqlite_connection = sqlite3.connect(self.db_path,
                                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        # self.sqlite_connection.execute("PRAGMA foreign_keys = ON;")
        # self.cursor = self.sqlite_connection.cursor()
        self.tables = {
            'users': ['"user_id" INTEGER NOT NULL UNIQUE',
                      '"user_first_name" TEXT',
                      '"user_last_name" TEXT',
                      '"username" TEXT',
                      '"date_registration" TEXT'],
            'setting_users': ['"user_id" INTEGER REFERENCES users(user_id) ON UPDATE CASCADE',
                              '"user_first_name" TEXT REFERENCES users(user_first_name) ON UPDATE CASCADE',
                              '"user_last_name" TEXT REFERENCES users(user_last_name) ON UPDATE CASCADE',
                              '"news" TEXT DEFAULT "False"',
                              '"baraholka" TEXT DEFAULT "False"',
                              '"rights" TEXT DEFAULT "user"',
                              '"use_bot" TEXT DEFAULT "True"'],
            'user_statistics': ['"user_id" INTEGER REFERENCES users(user_id) ON UPDATE CASCADE',
                                '"today" INTEGER DEFAULT 0',
                                '"month" INTEGER DEFAULT 0',
                                '"all_time" INTEGER DEFAULT 0'],
            'function_statistics': ['"name" TEXT NOT NULL UNIQUE',
                                    '"today" INTEGER DEFAULT 0',
                                    '"month" INTEGER DEFAULT 0',
                                    '"all_time" INTEGER DEFAULT 0'],
            'duty_schedule': ['"first_date" TEXT NOT NULL UNIQUE',
                              '"last_date" TEXT NOT NULL UNIQUE',
                              '"user_first_name" TEXT NOT NULL'],
            'events': ['"date" TEXT NOT NULL',
                       '"text_event" TEXT NOT NULL'],
            'in_out': ['"last_checkpoint" TEXT', ]
        }
        # self.is_connected = self.sqlite_connection is not None

    def __enter__(self):
        """Метод, который выполняется при входе в контекстный менеджер.
        Устанавливает соединение с базой данных и открывает курсор.
        
        Использование:
        with WorkWithDb() as db:
            # Работа с базой данных через объект db
        """
        self.logger.info("Соединение с базой данных установлено.")
        self.sqlite_connection = sqlite3.connect(self.db_path,
                                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        return self.sqlite_connection

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
        """
        Метод вызывается при выходе из контекстного менеджера. 
        
        Если во время работы в контекстном менеджере возникает ошибка, то выполняется откат транзакции (rollback).
        В противном случае все изменения фиксируются (commit). В любом случае соединение с базой данных закрывается.
        
        Использование:
        with WorkWithDb() as db:
            # Выполнение операций с объектом db
            # Например, вызов методов для работы с базой данных
        
        Если в блоке `with` возникает исключение, коммит не будет выполнен, а изменения будут отменены.
        """
        try:
            if exc_type or exc_val or exc_tb:
                self.logger.error(f"Откат транзакции из-за ошибки: {exc_val}")
                self.sqlite_connection.rollback()
            else:
                self.logger.debug("Committing transaction and closing database connection.")
                self.sqlite_connection.commit()
        finally:
            self.close_connection()

    def close_connection(self):
        """Закрывает соединение с базой данных.
        
        Данный метод завершает текущее соединение с базой данных SQLite. 
        Он вызывается автоматически при завершении работы объекта (например, при выходе 
        из контекстного менеджера `with`). Если закрытие соединения происходит с ошибкой, 
        то делается запись об ошибке в журнал логирования.
        
        Использование:
        with WorkWithDb() as db:
            # Работа с базой данных через объект db
            pass
        # При завершении блока `with` метод close_connection автоматически закроет соединение.
        """
        try:
            if self.sqlite_connection:
                self.sqlite_connection.close()
                self.logger.info("Соединение с базой данных закрыто.")
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при закрытии соединения: {e}")

    def create_db_if_not(self):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'telegram_bot.db')
        if not os.path.exists(db_path):
            sqlite3.connect(db_path).execute("PRAGMA foreign_keys = ON;").close()
            self.logger.info(f"База данных создана: {db_path}")
        return db_path

    def create_table(self, name):
        if name not in self.tables:
            self.logger.error(f"Table '{name}' does not exist in configuration. Cannot create.")
            return

        if not self.check_table_exists(name):
            columns = ", ".join(self.tables[name])
            create_query = f'CREATE TABLE {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})'
            self.logger.debug(f"Executing query to create table '{name}' with columns: {columns}")
            with self.sqlite_connection as conn:
                conn.execute(create_query)
                conn.execute("PRAGMA foreign_keys = ON;")

    def check_table_exists(self, name):
        """Проверяет наличие таблицы в базе данных."""
        query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            cursor.execute(query, (name,))
            return cursor.fetchone() is not None

    def check_for_existence(self, user_id):
        """Проверяет наличие пользователя в таблице users."""

        table_name = 'users'
        # Проверяем существование таблицы 'users'
        if not self.check_table_exists(table_name):
            self.logger.info(f"Таблица '{table_name}' не найдена. Создаю таблицу и недостающие таблицы.")
            for table in self.tables:
                if not self.check_table_exists(table):
                    self.create_table(table)

            for trigger_name, action in [
                ('after_user_insert_to_setting_users',
                 'INSERT INTO setting_users (user_id, user_first_name, user_last_name) '
                 'VALUES (NEW.user_id, NEW.user_first_name, NEW.user_last_name);'),
                ('after_user_insert_to_user_statistics',
                 'INSERT INTO user_statistics (user_id) VALUES (NEW.user_id);')
            ]:
                create_trigger_query = (f'CREATE TRIGGER IF NOT EXISTS {trigger_name} '
                                        f'AFTER INSERT ON {table_name}'
                                        f'BEGIN {action}'
                                        f'END;')
                with self.sqlite_connection as conn:
                    conn.execute(create_trigger_query)
            return False

        # Проверяем наличие записи с переданным user_id
        select_query = f'SELECT 1 FROM {table_name} WHERE user_id = ?'
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query, (user_id,))
            return cursor.fetchone() is not None

    def insert_new_user(self, user_id, first_name, last_name, username):
        """Добавляет нового пользователя в таблицу users."""

        self.create_table('users')  # Ensure 'users' table exists
        self.tables['setting_users'] = ['"user_id" INTEGER REFERENCES users(user_id) ON DELETE CASCADE',
                                        '"user_first_name" TEXT',
                                        '"user_last_name" TEXT',
                                        '"news" TEXT DEFAULT "False"',
                                        '"baraholka" TEXT DEFAULT "False"',
                                        '"rights" TEXT DEFAULT "user"',
                                        '"use_bot" TEXT DEFAULT "True"']  # Adjust table definition
        self.create_table('setting_users')  # Ensure 'setting_users' table exists

        if not self.check_for_existence(user_id):
            insert_query = ('INSERT INTO users (user_id, user_first_name, user_last_name, username, date_registration) '
                            'VALUES (?, ?, ?, ?, ?)')
            with self.sqlite_connection as conn:
                conn.execute(insert_query,
                             (user_id, first_name, last_name, username,
                              datetime.datetime.now().strftime("%d.%m.%Y")))
                return True
        return False

    def insert_dej_in_table(self, first_date, last_date, name_hero):
        """Добавляет дежурного в таблицу duty_schedule."""

        try:
            self.create_table('duty_schedule')

            insert_query = (
                'INSERT INTO duty_schedule ("first_date", "last_date", "user_first_name") '
                'VALUES (?, ?, ?)'
            )
            with self.sqlite_connection as conn:
                conn.execute(insert_query, (first_date, last_date, name_hero))
            self.logger.info(f"Запись о дежурном добавлена: {first_date}, {last_date}, {name_hero}.")
            return True
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error while inserting duty schedule: {e}")
        text_error = "Ошибка: начальная или конечная дата уже существует в таблице."
        return text_error

    def get_data_next_dej(self):
        """Возвращает данные следующего дежурного."""

        self.create_table('duty_schedule')

        select_query = (f"SELECT * "
                        f"FROM duty_schedule "
                        f"WHERE first_date >= DATE('now') "
                        f"ORDER BY ABS(JULIANDAY(first_date) - JULIANDAY('now'))"
                        f"LIMIT 1")
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            # Проверяем, есть ли результат
            result = cursor.fetchone()

        if result is not None:
            first_date = result[1]
            last_date = result[2]
            name_hero = result[3]

            list_data = [first_date, last_date, name_hero]
            self.logger.info(f"Следующее дежурство найдено: {list_data}.")
            return list_data

    def get_data_list_dej(self):
        """Возвращает ближайшие 10 дежурств."""

        self.create_table('duty_schedule')

        select_query = (f"SELECT * "
                        f"FROM duty_schedule "
                        f"WHERE first_date >= DATE('now') "
                        f"ORDER BY ABS(JULIANDAY(first_date) - JULIANDAY('now')) "
                        f"LIMIT 10")
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            result = cursor.fetchall()
        self.logger.debug("Attempting to fetch the list of the next 10 duty records.")
        data_list = [[row[1], row[2], row[3]] for row in result]

        self.logger.info(f"Получен список ближайших дежурств: {data_list}. Total records retrieved: {len(data_list)}")
        return data_list

    def check_access_level_user(self, user_id):
        """По user_id находит и возвращает права пользователя."""

        table_name = 'setting_users'
        # Проверяем существование таблицы 'setting_users'
        if self.check_table_exists(table_name):
            select_query = f'SELECT rights FROM "{table_name}" WHERE user_id="{user_id}"'
            with self.sqlite_connection as conn:
                cursor = conn.execute(select_query)
                result = cursor.fetchone()
            if result:
                self.logger.info(f"Права доступа для пользователя {user_id} получены: {result[0]}.")
                return result[0]
        return None

    def get_list_users_id(self, focus_group='all'):
        """Находит в базе данных все user_id запрашиваемой группы и возвращает их списком. Если ничего не надёт,
            вернёт пустой список."""

        select_query = ''

        if focus_group == 'all':
            select_query = 'SELECT user_id FROM setting_users WHERE use_bot="True"'
        elif focus_group == 'news':
            select_query = 'SELECT user_id FROM setting_users WHERE news="True" AND use_bot="True"'
        elif focus_group == 'baraholka':
            select_query = 'SELECT user_id FROM setting_users WHERE baraholka="True" AND use_bot="True"'

        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            result = cursor.fetchall()

        return [user_id[0] for user_id in result] if result else []

    def change_user_settings(self, column_name, set_status, user_id):
        """Изменяет статус пользователя user_id в setting_users. Устанавливает set_status в column_name"""

        update_query = (f'UPDATE setting_users '
                        f'SET "{column_name}" = "{set_status}" '
                        f'WHERE user_id = "{user_id}"')
        with self.sqlite_connection as conn:
            conn.execute(update_query)

    def change_user_status_news(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке news"""

        select_query = f'SELECT news FROM setting_users WHERE user_id="{user_id}"'
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            status = cursor.fetchone()[0]

        if status == 'True':
            self.change_user_settings(column_name='news', set_status='False', user_id=user_id)
            text_answer = f'Вы больше не будете получать уведомления о новостях IT-отдела'
            self.logger.info(f"Пользователь {user_id} отписался от уведомлений о новостях ИТ-отдела.")
            return text_answer
        elif status == 'False':
            self.change_user_settings(column_name='news', set_status='True', user_id=user_id)
            text_answer = f'Вы успешно подписались на новости IT-отдела'
            return text_answer

    def change_user_status_bar(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке baraholka"""

        select_query = f'SELECT baraholka FROM setting_users WHERE user_id="{user_id}"'
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            status = cursor.fetchone()[0]

        if status == 'True':
            self.change_user_settings(column_name='baraholka', set_status='False', user_id=user_id)
        elif status == 'False':
            self.change_user_settings(column_name='baraholka', set_status='True', user_id=user_id)

    def change_user_status_use_bot(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке use_bot"""

        select_query = f'SELECT use_bot FROM setting_users WHERE user_id="{user_id}"'
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            status = cursor.fetchone()[0]

        if status == 'True':
            self.change_user_settings(column_name='use_bot', set_status='False', user_id=user_id)
        elif status == 'False':
            self.change_user_settings(column_name='use_bot', set_status='True', user_id=user_id)

    def change_user_right(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке rights"""

        select_query = f'SELECT rights FROM setting_users WHERE user_id="{user_id}"'
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            status = cursor.fetchone()[0]

        if status == 'user':
            self.change_user_settings(column_name='rights', set_status='admin', user_id=user_id)
        elif status == 'admin':
            self.change_user_settings(column_name='rights', set_status='user', user_id=user_id)

    def check_user_status(self, column, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке news"""

        select_query = f'SELECT "{column}" FROM setting_users WHERE user_id="{user_id}"'
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            status = cursor.fetchone()[0]

        return status

    def check_dej_tomorrow(self):
        """Достаёт ближайшую дату из таблицы duty_schedule, если эта дата завтра, возвращает текст события,
        иначе вернёт False"""

        select_query = ('SELECT * '
                        'FROM duty_schedule '
                        'WHERE first_date = DATE("now", "+1 day") '
                        'ORDER BY first_date '
                        'LIMIT 1;')
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            result = cursor.fetchone()

        if result:
            list_data = self.get_data_next_dej()

            first_date = list_data[0]
            first_date_datetime = datetime.datetime.strptime(first_date, '%Y-%m-%d')
            first_date_format = first_date_datetime.strftime("%d.%m.%Y")

            last_date = list_data[1]
            last_date_datetime = datetime.datetime.strptime(last_date, '%Y-%m-%d')
            last_date_format = last_date_datetime.strftime("%d.%m.%Y")

            user_first_name = list_data[2]

            result_text = f'В период с {first_date_format} по {last_date_format} будет дежурить {user_first_name}'
            return result_text
        else:
            print('Завтра дежурных нет')
            return None

    def check_event_today(self):
        """Проверяет есть ли сегодня события и уведомляет всех пользователей"""

        if self.check_table_exists('events') is False:
            self.create_table('events')

        select_query = ('SELECT * '
                        'FROM events '
                        'WHERE DATE(date) = DATE("now");')
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            result = cursor.fetchall()

        if len(result) > 0:
            self.logger.debug(f"Today's events: {result}")
        else:
            self.logger.info('На сегодня событий нет')

    def check_door(self):
        """Достаёт из БД последний чекпоинт"""

        name_table = 'in_out'
        self.create_table(name_table)

        select_query = (f'SELECT last_checkpoint '
                        f'FROM {name_table}')
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query)
            result = cursor.fetchone()
        if result is not None:
            return result
        else:
            return None

    def update_checkpoint(self, checkpoint):
        """Актуализирует данные о дверях в БД"""

        self.logger.debug(f"Attempting to update checkpoint: {checkpoint}")
        update_query = f"UPDATE in_out SET last_checkpoint = '{checkpoint}' WHERE id = 1"
        # print(update_query)
        with self.sqlite_connection as conn:
            conn.execute(update_query)
        self.logger.info(f"Checkpoint successfully updated: {checkpoint}")

        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            if cursor.rowcount == 0:  # If no rows are updated
                self.logger.debug("No existing checkpoint found. Inserting a new checkpoint.")
                insert_query = "INSERT INTO in_out (last_checkpoint) VALUES (?)"
                # with self.db_path as conn:
                conn.execute(insert_query, (checkpoint,))
        self.logger.info(f"Checkpoint successfully updated/inserted: {checkpoint}")


# class ConnectionManager:
#     """Класс для управления соединением с базой данных"""
#
#     def __init__(self):
#         self.db = WorkWithDb()
#
#     def __enter__(self):
#         """Метод, который выполняется при входе в контекстный менеджер.
#         Устанавливает соединение с базой данных и открывает курсор.
#
#         Использование:
#         with ConnectionManager() as db:
#             # Работа с базой данных через объект db
#         """
#         self.db = WorkWithDb()
#         self.db.__enter__()
#         return self.db
#
#     def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> bool:
#         """
#         Метод вызывается при выходе из контекстного менеджера.
#
#         Если во время работы в контекстном менеджере возникает ошибка, то выполняется откат транзакции (rollback).
#         В противном случае все изменения фиксируются (commit). В любом случае соединение с базой данных закрывается.
#
#         Использование:
#         with ConnectionManager() as db:
#             # Выполнение операций с объектом db
#             # Например, вызов методов для работы с базой данных
#
#         Если в блоке `with` возникает исключение, коммит не будет выполнен, а изменения будут отменены.
#         """
#         self.db.__exit__(exc_type, exc_val, exc_tb)
#         self.db.close_connection()
#         self.db = None
#         return True


class StatisticsManager:
    """Класс для работы со статистикой пользователей и функций"""

    def __init__(self):
        self.db = WorkWithDb()
        self.sqlite_connection = self.db
        self.logger = logging.getLogger('StatisticsManager')

    def get_top_func_stat(self, column):
        """Достаёт топ-3 самых вызываемых функций за column"""
        self.logger.debug(f"Fetching top-3 functions for column: {column}")
        select_query = (f'SELECT name, {column} '
                        f'FROM function_statistics '
                        f'WHERE {column} > 0 '
                        f'ORDER BY {column} DESC '
                        f'LIMIT 3')
        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            cursor.execute(select_query)
            result = cursor.fetchall()
            self.logger.debug(f"Query executed: {select_query}. Result: {result}")
            return result or []

    def get_top_func_stat_day(self):
        """Достаёт топ-3 самых вызываемых функций за день"""
        self.logger.info("Fetching top-3 functions for today.")
        return self.get_top_func_stat('today')

    def get_top_func_stat_month(self):
        """Достаёт топ-3 самых вызываемых функций за месяц"""
        self.logger.info("Fetching top-3 functions for the month.")
        return self.get_top_func_stat('month')

    def get_top_func_stat_all_time(self):
        """Достаёт топ-3 самых вызываемых функций за все время"""
        self.logger.info("Fetching top-3 functions for all time.")
        return self.get_top_func_stat('all_time')

    def reset_func_stat(self, column):
        """Обнуляет счетчики активности вызываемых функций в колонке column."""
        self.logger.warning(f"Resetting function statistics for column: {column}")
        update_query = f'UPDATE function_statistics SET {column} = 0'
        with self.sqlite_connection as conn:  # Fixing the connection usage
            cursor = conn.cursor()  # Creating a cursor for the connection
            cursor.execute(update_query)
            conn.commit()  # Ensuring the changes are committed
        self.logger.debug(f"Statistics reset query executed: {update_query}")

    def reset_func_stat_day(self):
        """Обнуляет счетчики активности вызываемых функций за день"""
        self.logger.info("Resetting daily function statistics.")
        self.reset_func_stat('today')

    def reset_func_stat_month(self):
        """Обнуляет счетчики активности вызываемых функций за месяц"""
        self.logger.info("Resetting monthly function statistics.")
        self.reset_func_stat('month')

    # def reset_func_stat_all_time(self):
    #     """Обнуляет счетчики активности вызываемых функций за все время"""
    #     self.logger.info("Resetting all-time function statistics.")
    #     self.reset_func_stat('all_time')

    def collect_statistical_user(self, user_id):
        """Увеличивает статистику пользователя."""
        self.logger.info(f"Incrementing statistics for user_id: {user_id}")
        update_query = ('UPDATE user_statistics '
                        'SET today = today + 1, month = month + 1, all_time = all_time + 1 '
                        'WHERE user_id = ?')
        with self.sqlite_connection as conn:  # Using correct connection handling
            cursor = conn.cursor()  # Creating a cursor for the connection
            cursor.execute(update_query, (user_id,))
            conn.commit()  # Ensuring the changes are committed
            self.logger.debug(f"Statistics updated for user_id: {user_id}")

    def collect_statistical_func(self, name_func):
        """Подсчитывает сколько раз была вызвана функция."""
        self.logger.info(f"Incrementing function call count for: {name_func}")
        insert_query = ('INSERT INTO function_statistics (name, today, month, all_time) '
                        'VALUES (?, 1, 1, 1) '
                        'ON CONFLICT(name) '
                        'DO UPDATE SET today = today + 1, month = month + 1, all_time = all_time + 1;')
        with self.sqlite_connection as conn:  # Using correct connection handling
            cursor = conn.cursor()  # Creating a cursor for the connection
            cursor.execute(insert_query, (name_func,))
            conn.commit()  # Ensuring the changes are committed
            self.logger.debug(f"Function statistics updated for: {name_func}")
