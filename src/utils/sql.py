import datetime
import logging
import os
import sqlite3


class Work_with_DB:
    """Класс для обмена с базой данных"""

    logger = logging.getLogger("Work_with_DB")

    def __init__(self):
        self.db_path = self.create_db_if_not()
        self.sqlite_connection = sqlite3.connect(self.db_path,
                                                 detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.sqlite_connection.execute("PRAGMA foreign_keys = 1")
        self.cursor = None
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
        self.is_connected = self.sqlite_connection is not None

    def __enter__(self):
        self.logger.info("Соединение с базой данных установлено.")
        self.initialize_connection()
        self.cursor = self.sqlite_connection.cursor()
        return self

    def __exit__(self, exc_type: type, exc_val: BaseException, exc_tb: object) -> None:
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
        """Закрывает соединение с базой данных."""
        try:
            if self.sqlite_connection:
                self.sqlite_connection.close()
                self.logger.info("Соединение с базой данных закрыто.")
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при закрытии соединения: {e}")
        finally:
            self.cursor = None

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
            query = f'CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})'
            self.execute_query(query)
            self.logger.info(f'Таблица "{name}" успешно создана с колонками: {columns}')

    def check_table_exists(self, name):
        """Проверяет наличие таблицы в базе данных."""
        query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
        self.cursor = self.cursor or self.sqlite_connection.cursor()
        self.cursor.execute(query, (name,))
        return self.cursor.fetchone() is not None
        """Проверяет наличие таблицы в базе данных."""

        query = "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?"
        if self.cursor is None:
            self.cursor = self.sqlite_connection.cursor()
        self.cursor.execute(query, (name,))
        result = self.cursor.fetchone()
        return result is not None

    def check_for_existence(self, user_id):
        """Проверяет наличие пользователя в таблице users."""

        table_name = 'users'
        # Проверяем существование таблицы 'users'
        if self.check_table_exists(table_name) is True:
            query = f'SELECT 1 FROM {table_name} WHERE user_id = ?'
            self.logger.info(f"Проверка существования пользователя {user_id} в таблице '{table_name}'.")
            return self.fetchone(query, (user_id,)) is not None
        else:
            missing_tables = [table for table in self.tables.keys() if not self.check_table_exists(table)]
            if missing_tables:
                self.logger.info(f"Создаю отсутствующие таблицы: {', '.join(missing_tables)}")
            for table in missing_tables:
                self.create_table(table)

            for trigger_name, action in [
                ('after_user_insert_to_setting_users',
                 'INSERT INTO setting_users (user_id, user_first_name, user_last_name) '
                 'VALUES (NEW.user_id, NEW.user_first_name, NEW.user_last_name);'),
                ('after_user_insert_to_user_statistics',
                 'INSERT INTO user_statistics (user_id) VALUES (NEW.user_id);')
            ]:
                self.execute_query(f"""
                    CREATE TRIGGER IF NOT EXISTS {trigger_name}
                    AFTER INSERT ON {table_name}
                    BEGIN
                        {action}
                    END;
                """)

            self.sqlite_connection.commit()
            return False

    def insert_new_user(self, user_id, first_name, last_name, username):
        """Добавляет нового пользователя в таблицу users."""

        if not self.check_for_existence(user_id):
            query = ('INSERT INTO users (user_id, user_first_name, user_last_name, username, date_registration) '
                     'VALUES (?, ?, ?, ?, ?)')
            self.execute_query(query,
                               (user_id, first_name, last_name, username, datetime.datetime.now().strftime("%d.%m.%Y")))
            return True
        return False

    def collect_statistical_user(self, user_id):
        """Увеличивает статистику пользователя."""

        query = ('UPDATE user_statistics '
                 'SET today = today + 1, month = month + 1, all_time = all_time + 1 '
                 'WHERE user_id = ?')
        self.logger.info(f"Обновление статистики для пользователя {user_id}.")
        self.execute_query(query, (user_id,))

    def collect_statistical_func(self, name_func):
        """Подсчитывает сколько раз была вызвана функция."""
        query = ('INSERT INTO function_statistics (name, today, month, all_time) '
                 'VALUES (?, 1, 1, 1) '
                 'ON CONFLICT(name) DO UPDATE SET today = today + 1, month = month + 1, all_time = all_time + 1;')
        self.logger.debug(f"Incrementing function call statistics for function '{name_func}'.")
        self.execute_query(query, (name_func,))

    def insert_dej_in_table(self, first_date, last_date, name_hero):
        """Добавляет дежурного в таблицу duty_schedule."""

        try:
            self.create_table('duty_schedule')

            insert_query = (
                'INSERT INTO duty_schedule ("first_date", "last_date", "user_first_name") '
                'VALUES (?, ?, ?)'
            )
            self.cursor.execute(insert_query, (first_date, last_date, name_hero))

            self.sqlite_connection.commit()
            self.logger.info(f"Запись о дежурном добавлена: {first_date}, {last_date}, {name_hero}.")
            return True
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error while inserting duty schedule: {e}")
        text_error = ("Ошибка: начальная или конечная дата уже существует в таблице.")
        return text_error

    def get_data_next_dej(self):
        """Возвращает данные следующего дежурного."""

        self.create_table('duty_schedule')

        select_query = (f"SELECT * "
                        f"FROM duty_schedule "
                        f"WHERE first_date >= DATE('now') "
                        f"ORDER BY ABS(JULIANDAY(first_date) - JULIANDAY('now'))"
                        f"LIMIT 1")
        self.cursor.execute(select_query)
        # Проверяем, есть ли результат
        result = self.cursor.fetchone()
        # print(result)
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
        self.cursor.execute(select_query)
        result = self.cursor.fetchall()
        data_list = [[row[1], row[2], row[3]] for row in result]

        # print(data_list)
        self.logger.info(f"Получен список ближайших дежурств: {data_list}.")
        return data_list

    def check_access_level_user(self, user_id):
        """По user_id находит и возвращает права пользователя."""

        table_name = 'setting_users'
        # Проверяем существование таблицы 'setting_users'
        if self.check_table_exists(table_name):
            self.cursor.execute(f'SELECT rights FROM "{table_name}" WHERE user_id="{user_id}"')
            result = self.cursor.fetchone()
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

        self.cursor.execute(select_query)
        result = self.cursor.fetchall()

        return [user_id[0] for user_id in result] if result else []

    def change_user_settings(self, column_name, set_status, user_id):
        """Изменяет статус пользователя user_id в setting_users. Устанавливает set_status в column_name"""

        update_query = (f'UPDATE setting_users '
                        f'SET "{column_name}" = "{set_status}" '
                        f'WHERE user_id = "{user_id}"')
        self.cursor.execute(update_query)
        self.sqlite_connection.commit()

    def change_user_status_news(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке news"""

        select_query = f'SELECT news FROM setting_users WHERE user_id="{user_id}"'
        if not hasattr(self, 'cursor') or self.cursor is None:
            self.cursor = self.sqlite_connection.cursor()
        self.cursor.execute(select_query)
        status = self.cursor.fetchone()[0]

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
        self.cursor.execute(select_query)
        status = self.cursor.fetchone()[0]

        if status == 'True':
            self.change_user_settings(column_name='baraholka', set_status='False', user_id=user_id)
        elif status == 'False':
            self.change_user_settings(column_name='baraholka', set_status='True', user_id=user_id)

    def change_user_status_use_bot(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке use_bot"""

        select_query = f'SELECT use_bot FROM setting_users WHERE user_id="{user_id}"'
        self.cursor.execute(select_query)
        status = self.cursor.fetchone()[0]

        if status == 'True':
            self.change_user_settings(column_name='use_bot', set_status='False', user_id=user_id)
        elif status == 'False':
            self.change_user_settings(column_name='use_bot', set_status='True', user_id=user_id)

    def change_user_right(self, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке rights"""

        select_query = f'SELECT rights FROM setting_users WHERE user_id="{user_id}"'
        self.cursor.execute(select_query)
        status = self.cursor.fetchone()[0]

        if status == 'user':
            self.change_user_settings(column_name='rights', set_status='admin', user_id=user_id)
        elif status == 'admin':
            self.change_user_settings(column_name='rights', set_status='user', user_id=user_id)

    def check_user_status(self, column, user_id):
        """Изменяет статус пользователя user_id в setting_users.
        Устанавливает противоположный статус в колонке news"""

        select_query = f'SELECT "{column}" FROM setting_users WHERE user_id="{user_id}"'
        self.cursor.execute(select_query)
        status = self.cursor.fetchone()[0]

        return status

    # @error_handling
    def check_dej_tomorrow(self):
        """Достаёт ближайшую дату из таблицы duty_schedule, если эта дата завтра, возвращает текст события,
        иначе вернёт False"""

        select_query = ('SELECT * '
                        'FROM duty_schedule '
                        'WHERE first_date = DATE("now", "+1 day") '
                        'ORDER BY first_date '
                        'LIMIT 1;')
        if not hasattr(self, 'cursor') or self.cursor is None:
            self.cursor = self.sqlite_connection.cursor()
        self.cursor.execute(select_query)
        result = self.cursor.fetchone()
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
        self.cursor.execute(select_query)
        result = self.cursor.fetchall()
        # print(result)

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
        self.cursor.execute(select_query)
        result = self.cursor.fetchone()
        if result is not None:
            return result
        else:
            return None

    def update_checkpoint(self, checkpoint):
        """Актуализирует данные о дверях в БД"""

        try:
            query = "UPDATE in_out SET last_checkpoint = ? WHERE id = 1"
            self.cursor.execute(query, (checkpoint,))
            if self.cursor.rowcount == 0:  # If no rows are updated
                query = "INSERT INTO in_out (last_checkpoint) VALUES (?)"
                self.cursor.execute(query, (checkpoint,))
            self.sqlite_connection.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update checkpoint: {e}")
            self.sqlite_connection.rollback()

    def get_top_func_stat(self, column):
        """Достаёт топ-3 самых вызываемых функций за день"""

        select_query = (f'SELECT name, {column} '
                        f'FROM function_statistics '
                        f'WHERE {column} > 0 '
                        f'ORDER BY {column} DESC '
                        f'LIMIT 3')
        self.cursor.execute(select_query)
        result = self.cursor.fetchall()
        if result:
            return result

    def reset_func_stat(self, column):
        """Обнуляет счетчики активности вызываемых функций в колонке column"""

        update_query = (f'UPDATE function_statistics '
                        f'SET {column} = 0')
        self.cursor.execute(update_query)
        self.sqlite_connection.commit()
        self.logger.info(f"Сброшена статистика функций для столбца '{column}'.")

    def execute_query(self, query, params=None):

        """Executes a given SQL query with optional parameters."""
        try:
            if not hasattr(self, 'sqlite_connection') or not self.sqlite_connection:
                self.initialize_connection()
            if not hasattr(self, 'cursor') or not self.cursor:
                self.cursor = self.sqlite_connection.cursor()

            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            self.sqlite_connection.commit()
            self.logger.debug(f"Query executed successfully: {query} with params: {params}")
        except sqlite3.Error as e:
            self.logger.error(f"Error occurred while executing query: {query} with params: {params}. Error: {e}")
            self.sqlite_connection.rollback()
            raise

    def fetchone(self, query, param):
        try:
            if not self.cursor:
                self.logger.error("Cannot fetch data as the cursor is not initialized.")
                raise sqlite3.OperationalError("Cursor not initialized.")

            self.cursor.execute(query, param)
            result = self.cursor.fetchone()
            self.logger.debug(f"Fetch one query executed. Query: {query}, Parameters: {param}")
            return result
        except sqlite3.Error as error:
            self.logger.error(f"Failed to execute fetchone query. Error: {error}")
            raise

    def fetchall(self, query, param=None):
        """Executes a SELECT query and fetches all rows of the result."""
        try:
            if not self.is_connected or not self.cursor:
                self.initialize_connection()
                self.cursor = self.sqlite_connection.cursor()

            if param:
                self.cursor.execute(query, param)
            else:
                self.cursor.execute(query)

            result = self.cursor.fetchall()
            self.logger.debug(f"Query executed successfully: {query} with param: {param}. Result: {result}")
            return result
        except sqlite3.Error as e:
            self.logger.error(f"Error occurred while executing query: {query} with param: {param}. Error: {e}")
            raise
