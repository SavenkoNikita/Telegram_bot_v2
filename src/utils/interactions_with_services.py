import logging
import os
import dotenv
import requests
from requests.auth import HTTPBasicAuth
import datetime
import http.client
import json

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
    """Обработка задач в YouGile"""

    def __init__(self):
        self.column_all_task = os.getenv("ID_COLUMN_ALL_TASK")
        self.token_yougile = os.getenv("TOKEN_YOUGILE")
        self.connect = http.client.HTTPSConnection("ru.yougile.com")
        self.headers = {
            'Content-Type': "application/json",
            'Authorization': f"Bearer {self.token_yougile}",
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/75.0.3770.142 Safari/537.36"
        }

    def post_task(self, title_task='Задача создана с помощью Python', description_text='', color='primary'):
        """Создаёт задачу с названием {title_task}(если не указать = 'Задача создана с помощью Python'),
        описанием {description_text}(если не указать = ''), и цвет {color}(по умолчанию бесцветный primary. 
        Доступны primary, gray, red, pink, yellow, green, turquoise, blue, violet), 
        в колонке {self.column_all_task}.

        Пример использования:

        title = f'Датчик «{name_sensor}» неисправен более часа'
        str_date = datetime.datetime.strftime(breakdown_date, "%d.%m.%Y %H:%M:%S")
        description = (
            f'• Дата обнаружения: {str_date}<br>'
            f'• Хост: {ip_host}<br>'
            f'• Температура: {last_value_float}<br>'
            f'• ID сенсора: {id_sensor}')
        YouGile().post_task(title_task=title, description_text=description, color='red')"""

        payload = (
            "{"
            f"\n  \"title\": \"{title_task}\","
            f"\n  \"columnId\": \"{self.column_all_task}\","
            f"\n  \"description\": \"{description_text}\","
            f"\n  \"color\": \"task-{color}\""
            "}"
        )

        # print(payload)

        self.connect.request("POST", "/api-v2/tasks", payload.encode('utf-8'), self.headers)
        # print(self.headers)

        res = self.connect.getresponse()
        data = res.read()
        response_status = res.status
        # print(data)

        if response_status == 201:
            response_text = data.decode("utf-8")
            response_dict = json.loads(response_text)
            id_task_yougile = response_dict.get('id')
            print(f'Создана задача {title_task} в YouGile')
            return id_task_yougile
        elif response_status == 429:
            return None
        else:
            print(f'Ошибка при создании задачи {title_task} в YouGile\nПодробности: {data}')
            return None

    def get_data_task(self, id_task):
        self.connect.request("GET", f"/api-v2/tasks/{id_task}", headers=self.headers)

        res = self.connect.getresponse()
        data = res.read()
        response_status = res.status
        if response_status == 200:
            response_text = data.decode("utf-8")
            response_dict = json.loads(response_text)
            return response_dict
        else:
            return None

    def delete_task(self, id_task):
        data_task = self.get_data_task(id_task)
        datetime_now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        if data_task is not None:
            id_column = data_task.get('columnId')
            status_completed = data_task.get('completed')
            title_task = data_task.get('title')

            if status_completed is False:
                payload = ('{\n  \"deleted\": true,\n  '
                           f'\"columnId\": \"{id_column}\"'
                           '}')

                self.connect.request("PUT", f"/api-v2/tasks/{id_task}", payload, self.headers)

                res = self.connect.getresponse()
                response_status = res.status
                if response_status == 200:
                    print(f'Date and time: {datetime_now}\nЗадача "{title_task}" с ID "{id_task}" удалена.\n')
