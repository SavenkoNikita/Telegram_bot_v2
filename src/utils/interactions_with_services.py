import json
import os
import logging

import dotenv
import requests
from requests.auth import HTTPBasicAuth

from src.utils.decorarors import error_handling

dotenv.load_dotenv()
dev_id = os.getenv('DEV_ID')


class Exchange_with_ERP:
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
        self.response = None

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
        json = self.response.json()
        count_day = int(json.get(os.getenv("FUNC_NAME2"), 0))
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
        """Обрабатывает вход и выход пользователя из системы ERP."""
        try:
            data = self.response.json() if self.response and self.response.content else {}
            self.logger.debug(f"Ответ JSON in_out: {data}")
            if self.response.status_code == 200:
                return [f"{item['Время']} {item['Вход']}" for item in data.get('data', [])]
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
