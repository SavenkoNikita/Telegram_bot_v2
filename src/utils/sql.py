import datetime
import json
import logging
import os
import sqlite3
import time

from src.utils.interactions_with_services import WorkWithYouGile as YouGile


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
                              '"use_bot" TEXT DEFAULT "True"',
                              '"verify_erp" TEXT DEFAULT "False"'],
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
                              '"user_first_name" TEXT NOT NULL',
                              '"user_id" INTEGER NOT NULL'],
            'events': ['"date" TEXT NOT NULL',
                       '"text_event" TEXT NOT NULL'],
            'in_out': ['"last_checkpoint" TEXT', ],
            'sensors': ['"id_sensor" INTEGER UNIQUE',
                        '"name_sensor" TEXT',
                        '"last_value" TEXT',
                        '"ip_host" TEXT',
                        '"last_update" TEXT',
                        '"date_of_breakdown" TEXT',
                        '"id_task_yougile" TEXT UNIQUE']
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
        """Создаёт БД если отсутствует"""

        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'telegram_bot.db')
        if not os.path.exists(db_path):
            sqlite3.connect(db_path).execute("PRAGMA foreign_keys = ON;").close()
            self.logger.info(f"База данных создана: {db_path}")
        return db_path

    def create_table_if_not(self, name):
        """Создаёт таблицу с именем {name} если она описана в {self.tables}"""

        if name not in self.tables:
            self.logger.error(f"Table '{name}' does not exist in configuration. Cannot create.")
            return

        if not self.check_table_exists(name):
            columns = ", ".join(self.tables[name])
            create_query = f'CREATE TABLE {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {columns})'
            self.logger.debug(f"Выполнение запроса для создания таблицы '{name}' с колонками: {columns}")
            with self.sqlite_connection as conn:
                conn.execute(create_query)
                conn.execute("PRAGMA foreign_keys = ON;")

    def check_table_exists(self, name):
        """Проверяет наличие таблицы в базе данных"""

        self.create_db_if_not()
        time.sleep(1)

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
                    self.create_table_if_not(table)

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

        self.create_table_if_not('users')  # Ensure 'users' table exists
        self.tables['setting_users'] = ['"user_id" INTEGER REFERENCES users(user_id) ON DELETE CASCADE',
                                        '"user_first_name" TEXT',
                                        '"user_last_name" TEXT',
                                        '"news" TEXT DEFAULT "False"',
                                        '"baraholka" TEXT DEFAULT "False"',
                                        '"rights" TEXT DEFAULT "user"',
                                        '"use_bot" TEXT DEFAULT "True"']  # Adjust table definition
        self.create_table_if_not('setting_users')  # Ensure 'setting_users' table exists

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
            self.create_table_if_not('duty_schedule')

            # Получаем user_id по имени
            user_id = self.get_user_id_by_name(name_hero)
            if not user_id:
                raise ValueError(f"Пользователь {name_hero} не найден")

            insert_query = (
                'INSERT INTO duty_schedule ("first_date", "last_date", "user_first_name", "user_id") '
                'VALUES (?, ?, ?, ?)'
            )

            with self.sqlite_connection as conn:
                conn.execute(insert_query, (first_date, last_date, name_hero, user_id))
            return True
        except sqlite3.IntegrityError as e:
            self.logger.error(f"Integrity error while inserting duty schedule: {e}")
            return "Ошибка: начальная или конечная дата уже существует в таблице."

    def get_data_next_dej(self):
        """Возвращает данные следующего дежурного."""

        self.create_table_if_not('duty_schedule')

        select_query = (
            "SELECT * "
            "FROM duty_schedule "
            "WHERE last_date >= DATE('now') "
            "ORDER BY ABS(JULIANDAY(last_date) - JULIANDAY('now'))"
            "LIMIT 1")
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

        self.create_table_if_not('duty_schedule')

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
            self.create_table_if_not('events')

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
        self.create_table_if_not(name_table)

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

    def update_data_sensors(self, id_sensor, name_sensor, last_value, ip_host):
        """Обновляет или добавляет данные о сенсорах с проверкой неисправностей"""

        name_table = 'sensors'
        self.create_table_if_not(name_table)

        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            now_date = datetime.datetime.now()
            now_str = now_date.strftime("%Y-%m-%d %H:%M:%S")

            try:
                # Проверяем существование датчика и получаем текущие данные
                cursor.execute(
                    'SELECT date_of_breakdown, id_task_yougile, last_update FROM sensors WHERE name_sensor = ?',
                    (name_sensor,)
                )
                existing_data = cursor.fetchone()

                try:
                    last_value_float = float(last_value)
                    is_breakdown = last_value_float < -50 or last_value_float > 50
                except (ValueError, TypeError):
                    print(f"Некорректное значение датчика {name_sensor}: {last_value}")
                    return

                if existing_data is None:
                    # Новый датчик - просто добавляем
                    cursor.execute(
                        'INSERT INTO sensors (id_sensor, name_sensor, last_value, ip_host, last_update) '
                        'VALUES (?, ?, ?, ?, ?)',
                        (id_sensor, name_sensor, last_value_float, ip_host, now_str)
                    )
                else:
                    existing_breakdown, existing_task, last_update = existing_data

                    if is_breakdown:
                        # Обработка неисправного состояния
                        if existing_breakdown is None:
                            # Первое обнаружение неисправности
                            cursor.execute(
                                'UPDATE sensors SET '
                                'id_sensor=?, last_value=?, ip_host=?, last_update=?, date_of_breakdown=? '
                                'WHERE name_sensor=?',
                                (id_sensor, last_value_float, ip_host, now_str, now_str, name_sensor)
                            )
                            self.logger.info(f'Зафиксирована неисправность датчика {name_sensor}')
                            # print(f"Зафиксирована неисправность датчика {name_sensor}")
                        else:
                            # Неисправность продолжается
                            breakdown_date = datetime.datetime.strptime(existing_breakdown, "%Y-%m-%d %H:%M:%S")

                            if existing_task is None and (now_date - breakdown_date) >= datetime.timedelta(hours=1):
                                # Неисправность более часа - создаем задачу
                                error_message = f'Датчик «{name_sensor}» неисправен более часа'
                                str_date = breakdown_date.strftime("%d.%m.%Y %H:%M:%S")
                                description = (
                                    f'• Дата обнаружения: {str_date}<br>'
                                    f'• Хост: {ip_host}<br>'
                                    f'• Температура: {last_value_float}<br>'
                                    f'• ID сенсора: {id_sensor}')

                                # Создаем задачу в YouGile и сохраняем ID
                                task_id = YouGile().post_task(
                                    title_task=error_message,
                                    description_text=description,
                                    color='red'
                                )

                                cursor.execute(
                                    'UPDATE sensors SET '
                                    'id_sensor=?, last_value=?, ip_host=?, last_update=?, id_task_yougile=? '
                                    'WHERE name_sensor=?',
                                    (id_sensor, last_value_float, ip_host, now_str, task_id, name_sensor)
                                )
                            else:
                                # Просто обновляем основные данные
                                cursor.execute(
                                    'UPDATE sensors SET '
                                    'id_sensor=?, last_value=?, ip_host=?, last_update=? '
                                    'WHERE name_sensor=?',
                                    (id_sensor, last_value_float, ip_host, now_str, name_sensor)
                                )
                    else:
                        # Датчик в норме
                        if existing_breakdown is not None or existing_task is not None:
                            # Восстановление после неисправности
                            if existing_task is not None:
                                # Выполняем задачу в YouGile перед очисткой полей
                                try:
                                    YouGile().complete_task(id_task=existing_task)
                                    self.logger.info(
                                        f'Задача YouGile {existing_task} для датчика {name_sensor} выполнена')
                                    # print(f"Задача YouGile {existing_task} для датчика {name_sensor} выполнена")
                                except Exception as e:
                                    self.logger.info(f'Ошибка при выполнении задачи YouGile: {str(e)}')
                                    # print(f"Ошибка при выполнении задачи YouGile: {str(e)}")

                            # Очищаем поля неисправности
                            cursor.execute(
                                'UPDATE sensors SET '
                                'id_sensor=?, last_value=?, ip_host=?, last_update=?, '
                                'date_of_breakdown=NULL, id_task_yougile=NULL '
                                'WHERE name_sensor=?',
                                (id_sensor, last_value_float, ip_host, now_str, name_sensor)
                            )
                            self.logger.info(f'Датчик {name_sensor} восстановлен')
                            # print(f"Датчик {name_sensor} восстановлен")
                        else:
                            # Просто обновление данных
                            cursor.execute(
                                'UPDATE sensors SET '
                                'id_sensor=?, last_value=?, ip_host=?, last_update=? '
                                'WHERE name_sensor=?',
                                (id_sensor, last_value_float, ip_host, now_str, name_sensor)
                            )

                conn.commit()

            except sqlite3.Error as e:
                self.logger.exception(f'Ошибка базы данных при обработке датчика {name_sensor}: {str(e)}')
                # print(f"Ошибка базы данных при обработке датчика {name_sensor}: {str(e)}")
                conn.rollback()
            except Exception as e:
                self.logger.exception(f'Неожиданная ошибка при обработке датчика {name_sensor}: {str(e)}')
                # print(f"Неожиданная ошибка при обработке датчика {name_sensor}: {str(e)}")
                conn.rollback()

    def clean_old_events(self, days=30):
        """Удаляет уведомления старше указанного количества дней"""
        try:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            with self.sqlite_connection:
                self.sqlite_connection.execute(
                    'DELETE FROM events WHERE date < ?',
                    (cutoff_date,)
                )
            self.logger.info(f"Cleaned events older than {days} days")
        except Exception as e:
            self.logger.error(f"Error cleaning old events: {e}")

    def get_future_dej_list(self, exclude_user_id=None):
        """Возвращает 7 ближайших будущих дежурств, исключая дежурства указанного пользователя"""
        self.create_table_if_not('duty_schedule')

        query = """
            SELECT d.id, d.first_date, d.last_date, u.user_first_name, u.user_id 
            FROM duty_schedule d 
            JOIN users u ON d.user_id = u.user_id 
            WHERE d.last_date >= DATE('now')
            AND d.user_id != ? 
            ORDER BY d.first_date
            LIMIT 7
        """

        with self.sqlite_connection as conn:
            cursor = conn.execute(query, (exclude_user_id,))
            return cursor.fetchall()

    def get_dej_by_id(self, dej_id):
        """Возвращает дежурство по ID"""
        self.create_table_if_not('duty_schedule')

        select_query = (
            "SELECT d.id, d.first_date, d.last_date, u.user_first_name, u.user_id "
            "FROM duty_schedule d "
            "JOIN users u ON d.user_first_name = u.user_first_name "
            "WHERE d.id = ?"
        )
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query, (dej_id,))
            return cursor.fetchone()

    def get_user_next_dej(self, user_id):
        """Возвращает следующее дежурство пользователя"""
        self.create_table_if_not('duty_schedule')

        # Сначала получаем имя пользователя
        user_name = self.get_user_name(user_id)
        if not user_name:
            return None

        select_query = (
            "SELECT id, first_date, last_date, user_first_name "
            "FROM duty_schedule "
            "WHERE user_first_name = ? AND last_date >= DATE('now') "
            "ORDER BY first_date "
            "LIMIT 1"
        )
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query, (user_name,))
            result = cursor.fetchone()

            # Проверяем, что дежурство найдено
            if result and result[1] and result[2]:
                return result
            return None

    def get_user_name(self, user_id):
        """Возвращает имя пользователя по ID"""
        select_query = "SELECT user_first_name FROM users WHERE user_id = ?"
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query, (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

    def swap_dej_dates(self, dej_id1, dej_id2):
        """Меняет даты дежурств местами"""
        try:
            # Получаем оба дежурства
            dej1 = self.get_dej_by_id(dej_id1)
            dej2 = self.get_dej_by_id(dej_id2)

            if not dej1 or not dej2:
                return False

            # Меняем даты местами
            update_query = (
                "UPDATE duty_schedule "
                "SET first_date = ?, last_date = ? "
                "WHERE id = ?"
            )
            with self.sqlite_connection as conn:
                # Обновляем первое дежурство
                conn.execute(update_query, (dej2[1], dej2[2], dej_id1))
                # Обновляем второе дежурство
                conn.execute(update_query, (dej1[1], dej1[2], dej_id2))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при обмене дежурствами: {e}")
            return False

    def get_user_id_by_name(self, name):
        """Возвращает user_id по имени пользователя"""
        select_query = "SELECT user_id FROM users WHERE user_first_name = ?"
        with self.sqlite_connection as conn:
            cursor = conn.execute(select_query, (name,))
            result = cursor.fetchone()
            return result[0] if result else None

    def restore_setting_users_table(self):
        """Восстанавливает таблицу setting_users из данных таблицы users с правильными foreign key"""
        try:
            # Сначала убедимся, что таблица users существует
            if not self.check_table_exists('users'):
                self.logger.error("Таблица users не существует. Восстановление невозможно.")
                return False

            # Отключаем проверку внешних ключей временно
            with self.sqlite_connection as conn:
                conn.execute("PRAGMA foreign_keys = OFF;")

            # Удаляем старую таблицу setting_users, если она существует
            if self.check_table_exists('setting_users'):
                self.logger.info("Удаление старой таблицы setting_users...")
                with self.sqlite_connection as conn:
                    conn.execute('DROP TABLE setting_users')

            # Создаем новую таблицу setting_users с правильными foreign key
            create_query = '''
            CREATE TABLE setting_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE CASCADE,
                user_first_name TEXT,
                user_last_name TEXT,
                news TEXT DEFAULT "False",
                baraholka TEXT DEFAULT "False",
                rights TEXT DEFAULT "user",
                use_bot TEXT DEFAULT "True",
                verify_erp TEXT DEFAULT "False"
            )
            '''
            with self.sqlite_connection as conn:
                conn.execute(create_query)

            # Получаем всех пользователей из таблицы users
            select_query = 'SELECT user_id, user_first_name, user_last_name FROM users'
            with self.sqlite_connection as conn:
                cursor = conn.cursor()
                cursor.execute(select_query)
                users = cursor.fetchall()

                # Вставляем данные в setting_users для каждого пользователя
                for user in users:
                    user_id, first_name, last_name = user
                    insert_query = '''
                        INSERT INTO setting_users 
                        (user_id, user_first_name, user_last_name) 
                        VALUES (?, ?, ?)
                    '''
                    cursor.execute(insert_query, (user_id, first_name, last_name))

                # Восстанавливаем триггеры
                for trigger_name, action in [
                    ('after_user_insert_to_setting_users',
                     'INSERT INTO setting_users (user_id, user_first_name, user_last_name) '
                     'VALUES (NEW.user_id, NEW.user_first_name, NEW.user_last_name);'),
                    ('after_user_insert_to_user_statistics',
                     'INSERT INTO user_statistics (user_id) VALUES (NEW.user_id);')
                ]:
                    create_trigger_query = (f'CREATE TRIGGER IF NOT EXISTS {trigger_name} '
                                            f'AFTER INSERT ON users '
                                            f'BEGIN {action} '
                                            f'END;')
                    conn.execute(create_trigger_query)

                # Включаем проверку внешних ключей обратно
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.commit()

            self.logger.info("Таблица setting_users успешно восстановлена из таблицы users")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при восстановлении таблицы setting_users: {e}")
            # Включаем проверку внешних ключей обратно, даже если произошла ошибка
            with self.sqlite_connection as conn:
                conn.execute("PRAGMA foreign_keys = ON;")
            return False

    def get_dej_history(self):
        """Возвращает историю дежурств за последние 45 дней"""
        self.create_table_if_not('duty_schedule')

        query = """
            SELECT first_date, last_date, user_first_name 
            FROM duty_schedule 
            WHERE first_date >= DATE('now', '-45 days') 
            ORDER BY first_date ASC
        """

        with self.sqlite_connection as conn:
            cursor = conn.execute(query)
            return cursor.fetchall()

    def promote_to_admin(self, user_id):
        """Дает пользователю права администратора"""
        try:
            update_query = 'UPDATE setting_users SET rights = "admin" WHERE user_id = ?'
            with self.sqlite_connection as conn:
                conn.execute(update_query, (user_id,))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при повышении прав пользователя {user_id}: {e}")
            return False

    def demote_to_user(self, user_id):
        """Лишает пользователя прав администратора"""
        try:
            update_query = 'UPDATE setting_users SET rights = "user" WHERE user_id = ?'
            with self.sqlite_connection as conn:
                conn.execute(update_query, (user_id,))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при понижении прав пользователя {user_id}: {e}")
            return False

    def get_user_list(self, access_level=None):
        """Возвращает список пользователей с возможностью фильтрации по уровню доступа"""
        try:
            query = ('SELECT u.user_id, u.user_first_name, u.user_last_name, s.rights '
                     'FROM users u JOIN setting_users s ON u.user_id = s.user_id')
            params = ()

            if access_level:
                query += ' WHERE s.rights = ?'
                params = (access_level,)

            with self.sqlite_connection as conn:
                cursor = conn.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка пользователей: {e}")
            return []


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

    def get_top_users_stat(self, column):
        """Достаёт топ-3 самых активных пользователей за указанный период"""
        self.logger.debug(f"Fetching top-3 users for column: {column}")
        select_query = (f'SELECT u.user_first_name, us.{column} '
                        f'FROM user_statistics us '
                        f'JOIN users u ON us.user_id = u.user_id '
                        f'WHERE us.{column} > 0 '
                        f'ORDER BY us.{column} DESC '
                        f'LIMIT 3')
        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            cursor.execute(select_query)
            result = cursor.fetchall()
            self.logger.debug(f"Query executed: {select_query}. Result: {result}")
            return result or []

    def get_top_users_stat_day(self):
        """Достаёт топ-3 самых активных пользователей за день"""
        self.logger.info("Fetching top-3 users for today.")
        return self.get_top_users_stat('today')

    def get_top_users_stat_month(self):
        """Достаёт топ-3 самых активных пользователей за месяц"""
        self.logger.info("Fetching top-3 users for the month.")
        return self.get_top_users_stat('month')

    def get_top_users_stat_all_time(self):
        """Достаёт топ-3 самых активных пользователей за все время"""
        self.logger.info("Fetching top-3 users for all time.")
        return self.get_top_users_stat('all_time')

    def reset_users_stat(self, column):
        """Обнуляет счетчики активности пользователей в указанной колонке"""
        self.logger.warning(f"Resetting users statistics for column: {column}")
        update_query = f'UPDATE user_statistics SET {column} = 0'
        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            cursor.execute(update_query)
            conn.commit()
        self.logger.debug(f"Users statistics reset query executed: {update_query}")

    def reset_users_stat_day(self):
        """Обнуляет дневную статистику активности пользователей"""
        self.logger.info("Resetting daily users statistics.")
        self.reset_users_stat('today')

    def reset_users_stat_month(self):
        """Обнуляет месячную статистику активности пользователей"""
        self.logger.info("Resetting monthly users statistics.")
        self.reset_users_stat('month')

    def get_unused_functions(self, days=30):
        """Возвращает список функций, которыми не пользовались за указанный период"""
        self.logger.info(f"Fetching unused functions for last {days} days")

        query = """
            SELECT fs.name, fs.month as usage_count
            FROM function_statistics fs
            WHERE fs.month = 0
            ORDER BY fs.name
        """

        with self.sqlite_connection as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            unused = cursor.fetchall()

            # Получаем функции с низкой активностью (например, менее 5 использований)
            query_low_usage = """
                SELECT fs.name, fs.month as usage_count
                FROM function_statistics fs
                WHERE fs.month > 0 AND fs.month < 5
                ORDER BY fs.month, fs.name
            """
            cursor.execute(query_low_usage)
            low_usage = cursor.fetchall()

            return {
                'unused': unused,
                'low_usage': low_usage
            }

