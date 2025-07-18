import logging
import os
import dotenv
import requests
from requests.auth import HTTPBasicAuth
import datetime
import http.client
import json

from typing import Optional, Dict

dotenv.load_dotenv()
dev_id = os.getenv('DEV_ID')


class ExchangeWithErp:
    """Получение данных из 1С"""

    def __init__(self, params):
        self.logger = logging.getLogger("ERP_Exchange_Logger")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()  # Clear existing logging handlers to avoid duplicate logs
        self.request_get = os.getenv("WAY_ERP_GET")
        self.request_post = os.getenv("WAY_ERP_POST")
        self.login = os.getenv("LOGIN_ERP")
        self.password = os.getenv("PASS_ERP")
        self.user_agent_val = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.params = params
        self.response = self.get_request()

    def get_request(self):
        """Выполняет GET-запрос к системе 1С."""
        self.logger.info(f"Отправка GET-запроса: {self.request_get}, параметры: {self.params}")
        try:
            request = requests.get(
                url=self.request_get,
                headers={'User-Agent': self.user_agent_val},
                auth=HTTPBasicAuth(self.login, self.password),
                params=self.params,
                timeout=10
            )
            self.logger.info(f"Получен ответ со статусом: {request.status_code}")
            # print(request)
            return request
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка GET-запроса: {str(e)}")
            return None

    def answer_from_ERP(self):
        """Обрабатывает ответ от 1С (ERP) и возвращает данные или ошибку."""
        try:
            self.logger.info(f"Разбор ответа от ERP: {self.response.json()}")
            data = self.response.json()
            for key, value in data.items():
                if os.getenv('EVENT_HANDLING_KEY') in key:
                    return True
                elif os.getenv('BIRD_AUTH_KEY') in key:
                    return value
            return {'error_text': 'Неизвестный ответ от ERP'}
        except Exception as e:
            self.logger.error(f"Ошибка обработки ответа: {str(e)}")
            return {'error_text': 'Ошибка обработки ответа'}

    def get_count_days(self):
        """На вход принимает user_id, запрашивает данные из 1С, и возвращает кол-во накопленных дней отпуска.
        Если пользователь не уволен, функция вернёт число, во всех остальных случаях 1С вернёт ошибку"""

        self.logger.info("Processing get_count_days response from ERP")
        json_data = self.response.json()
        count_day = int(json_data.get(os.getenv("FUNC_NAME2"), 0))
        self.logger.info(f"Count of days calculated: {count_day}")
        return count_day

    def verification(self):
        """Запрос принимает user_id и ИНН пользователя. В случае успеха, обновляет ID Telegram в 1С у пользователя с
        указанным ИНН. Либо возвращает str(ошибку)."""

        self.logger.info("Processing verification response from ERP")
        json = self.response.json()
        answer_erp = json.get(os.getenv("FUNC_NAME3"), "Error: Missing data")
        self.logger.info(f"Verification result: {answer_erp}")
        return answer_erp

    def in_out(self):
        """Обрабатывает вход и выход пользователя из системы ERP.

        :return dict(in_out)"""

        try:
            data = self.response.json()
            self.logger.debug(f"Ответ JSON in_out: {data}")
            if self.response.status_code == 200:
                for key, value in data.items():
                    # print(data.items())
                    return value
            return {'error_text': 'Некорректный ответ'}
        except Exception as e:
            self.logger.error(f"Ошибка обработки in_out: {str(e)}")
            return {'error_text': 'Ошибка обработки in_out'}

    def post_request(self):
        """Выполняет POST-запрос в систему ERP."""
        self.logger.info(f"Отправка POST-запроса: {self.request_post}, параметры: {self.params}")
        try:
            request = requests.post(
                url=self.request_post,
                headers={'User-Agent': self.user_agent_val},
                params=self.params,
                auth=HTTPBasicAuth(self.login, self.password),
                timeout=10
            )
            self.logger.info(f"POST-ответ статус: {request.status_code}")
            return request
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка POST-запроса: {str(e)}")
            return None


class WorkWithYouGile:
    """Класс для работы с API YouGile."""

    API_BASE_URL = "ru.yougile.com"
    API_TASKS_PATH = "/api-v2/tasks"
    VALID_COLORS = {'primary', 'gray', 'red', 'pink', 'yellow', 'green', 'turquoise', 'blue', 'violet'}

    def __init__(self):
        """Инициализация подключения к YouGile API."""
        self.column_all_task = os.getenv("ID_COLUMN_ALL_TASK")
        self.token_yougile = os.getenv("TOKEN_YOUGILE")

        if not all([self.column_all_task, self.token_yougile]):
            raise ValueError("Не заданы обязательные переменные окружения")

        self.headers = {
            'Content-Type': "application/json",
            'Authorization': f"Bearer {self.token_yougile}",
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36"
        }

    def _make_request(self, method: str, path: str, payload: Optional[str] = None) -> Optional[Dict]:
        """Выполняет HTTP-запрос к API.

        Args:
            method: HTTP-метод (GET, POST, PUT и т.д.)
            path: Путь API
            payload: Тело запроса (опционально)

        Returns:
            Словарь с ответом API или None в случае ошибки
        """
        conn = None
        try:
            conn = http.client.HTTPSConnection(self.API_BASE_URL)
            headers = self.headers.copy()

            # Если есть тело запроса, кодируем его в UTF-8
            body = None
            if payload is not None:
                body = payload.encode('utf-8')
                # Добавляем Content-Length, если есть тело
                headers['Content-Length'] = str(len(body))

            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()

            if response.status in (200, 201):
                return json.loads(response.read().decode('utf-8'))
            elif response.status == 429:
                print("Превышен лимит запросов")
            else:
                error_body = response.read().decode('utf-8', errors='replace')
                print(f"Ошибка API: {response.status} - {error_body}")

        except (http.client.HTTPException, json.JSONDecodeError, UnicodeError) as e:
            print(f"Ошибка при выполнении запроса: {e}")
        finally:
            if conn:
                conn.close()

        return None

    def post_task(self, title_task: str = 'Задача создана с помощью Python',
                  description_text: str = '', color: str = 'primary') -> Optional[str]:
        """Создает новую задачу в YouGile.

        Args:
            title_task: Заголовок задачи
            description_text: Описание задачи
            color: Цвет задачи (primary, gray, red и т.д.)

        Returns:
            ID созданной задачи или None в случае ошибки
        """
        if color not in self.VALID_COLORS:
            color = 'primary'

        payload = (
            "{"
            f"\n  \"title\": \"{title_task}\","
            f"\n  \"columnId\": \"{self.column_all_task}\","
            f"\n  \"description\": \"{description_text}\","
            f"\n  \"color\": \"task-{color}\""
            "}")

        response = self._make_request("POST", self.API_TASKS_PATH, payload)
        if response:
            print(f'Создана задача {title_task} в YouGile')
            return response.get('id')
        return None

    def get_data_task(self, id_task: str) -> Optional[Dict]:
        """Получает данные задачи по ID.

        Args:
            id_task: ID задачи

        Returns:
            Словарь с данными задачи или None в случае ошибки
        """
        return self._make_request("GET", f"{self.API_TASKS_PATH}/{id_task}")

    def edit_task(self, id_task: str, request_type: str) -> None:
        """Редактирует задачу (помечает как выполненную или удаленную).

        Args:
            id_task: ID задачи
            request_type: Тип изменения (complete или delete)
        """
        data_task = self.get_data_task(id_task)
        if not data_task:
            return

        title_task = data_task.get('title', '')
        datetime_now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        payload = json.dumps({
            request_type: True,
            "columnId": data_task.get('columnId')
        })

        response = self._make_request("PUT", f"{self.API_TASKS_PATH}/{id_task}", payload)
        if response:
            action = 'выполненное действие неизвестно'
            if request_type == "deleted":
                action = "удалена"
            elif request_type == "completed":
                action = "выполнена"
            print(f'Date and time: {datetime_now}\nЗадача "{title_task}" с ID "{id_task}" {action}.\n')

    def delete_task(self, id_task: str) -> None:
        """Удаляет задачу по ID.

        Args:
            id_task: ID задачи
        """
        self.edit_task(id_task, "deleted")

    def complete_task(self, id_task: str) -> None:
        """Помечает задачу как выполненную по ID.

        Args:
            id_task: ID задачи
        """
        self.edit_task(id_task, "completed")
