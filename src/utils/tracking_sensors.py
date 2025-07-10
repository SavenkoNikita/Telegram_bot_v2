import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional

import dotenv

from src.utils.sql import WorkWithDb as DB

dotenv.load_dotenv()


class TrackingSensor:
    """Мониторинг неисправных датчиков"""

    def __init__(self):
        # Добавляем проверку на наличие переменной окружения
        ip_list = os.getenv('LIST_IP_CONTROLLERS', '')
        self.list_ip_controllers = [ip.strip() for ip in ip_list.split(',') if ip.strip()]

    def _parse_xml_data(self, ip_host: str) -> Optional[Dict]:
        """Парсинг XML данных с контроллера"""
        try:
            url = f'http://{ip_host}/values.xml'
            with urllib.request.urlopen(url, timeout=10) as web_file:  # Добавляем таймаут
                root_node = ET.parse(web_file).getroot()

                device_name = root_node.find('Agent/DeviceName')
                if device_name is None:
                    return None

                sensor_data = {
                    'device_name': device_name.text,
                    'sensors': []
                }

                for entry in root_node.findall('SenSet/Entry'):
                    sensor = {
                        'name': entry.findtext('Name'),
                        'id': entry.findtext('ID'),
                        'value': entry.findtext('Value'),
                        'min': entry.findtext('Min'),
                        'max': entry.findtext('Max'),
                        'sen_id': entry.findtext('SenId'),
                        'hyst': entry.findtext('Hyst')
                    }
                    # Добавляем проверку на None для критичных полей
                    if sensor['name'] and sensor['id'] and sensor['value']:
                        sensor_data['sensors'].append(sensor)

                # print(sensor_data)
                return sensor_data

        except urllib.error.URLError as e:
            print(f'Нет соединения с {ip_host}: {e}')
            return None
        except ET.ParseError as e:
            print(f'Ошибка парсинга XML с {ip_host}: {e}')
            return None
        except Exception as e:
            print(f'Неизвестная ошибка при обработке {ip_host}: {e}')
            return None

    # def get_data(self) -> List[List[str]]:
    #     """Получить список датчиков с их значениями"""
    #     sensors_with_an_error = []
    #
    #     for ip_host in self.list_ip_controllers:
    #         data = self._parse_xml_data(ip_host)
    #         if not data or not data.get('sensors'):
    #             continue
    #
    #         for sensor in data['sensors']:
    #             if sensor.get('name') and sensor.get('value'):
    #                 sensors_with_an_error.append([
    #                     sensor['name'],
    #                     sensor['value']
    #                 ])
    #
    #     return sensors_with_an_error

    # def get_all_data(self) -> List[Dict]:
    #     """Получить полные данные со всех контроллеров"""
    #     all_data = []
    #
    #     for ip_host in self.list_ip_controllers:
    #         data = self._parse_xml_data(ip_host)
    #         if not data or not data.get('sensors'):
    #             continue
    #
    #         device_data = {
    #             data['device_name']: {
    #                 sensor['name']: {
    #                     'ID': sensor['id'],
    #                     'Value': sensor['value'],
    #                     'Min': sensor['min'],
    #                     'Max': sensor['max'],
    #                     'SenId': sensor['sen_id'],
    #                     'Hyst': sensor['hyst']
    #                 } for sensor in data['sensors'] if sensor.get('name')
    #             }
    #         }
    #         all_data.append(device_data)
    #
    #     return all_data

    # def check_all_sensors(self):
    #     """Проверить все датчики и обновить их статус в БД"""
    #
    #     for ip in self.list_ip_controllers:
    #         dict_data_host = self._parse_xml_data(ip)
    #         if not dict_data_host or not dict_data_host.get('sensors'):
    #             continue
    #
    #         # Исправляем ошибку: было dict_data_host.get('sensors')[0]
    #         for sensor in dict_data_host['sensors']:
    #             try:
    #                 id_sensor = sensor.get('id')
    #                 name_sensor = sensor.get('name')
    #                 last_value = float(sensor.get('value')) if sensor.get('value') else None
    #                 ip_host = ip
    #
    #                 if id_sensor and name_sensor and last_value is not None:
    #                     DB().update_data_sensors(
    #                         id_sensor=id_sensor,
    #                         name_sensor=name_sensor,
    #                         last_value=last_value,
    #                         ip_host=ip_host
    #                     )
    #             except Exception as e:
    #                 print(f"Ошибка при обработке датчика {sensor.get('name')} с {ip}: {e}")

    # def check_all_sensors(self):
    #     """Проверить все датчики и обновить их статус в БД"""
    #     for ip in self.list_ip_controllers:
    #         dict_data_host = self._parse_xml_data(ip)
    #         if not dict_data_host or not dict_data_host.get('sensors'):
    #             continue
    #
    #         for sensor in dict_data_host['sensors']:
    #             try:
    #                 id_sensor = sensor.get('id')
    #                 name_sensor = sensor.get('name')
    #                 value = sensor.get('value')
    #                 ip_host = ip
    #
    #                 if not all([id_sensor, name_sensor, value]):
    #                     continue
    #
    #                 # Очистка и валидация данных перед записью в БД
    #                 clean_name = name_sensor.strip().replace('"', '')  # Удаляем кавычки
    #                 clean_value = float(value) if value.replace('.', '', 1).isdigit() else None
    #
    #                 if clean_value is None:
    #                     print(f"Некорректное значение датчика {clean_name}: {value}")
    #                     continue
    #
    #                 DB().update_data_sensors(
    #                     id_sensor=int(id_sensor),
    #                     name_sensor=clean_name,
    #                     last_value=clean_value,
    #                     ip_host=ip_host
    #                 )
    #
    #             except ValueError as e:
    #                 print(f"Ошибка преобразования данных датчика {sensor.get('name')} с {ip}: {e}")
    #             except Exception as e:
    #                 print(f"Ошибка при обработке датчика {sensor.get('name')} с {ip}: {e}")

    def check_all_sensors(self):
        """Проверить все датчики и обновить их статус в БД"""
        for ip in self.list_ip_controllers:
            dict_data_host = self._parse_xml_data(ip)
            if not dict_data_host or not dict_data_host.get('sensors'):
                continue

            for sensor in dict_data_host['sensors']:
                try:
                    id_sensor = sensor.get('id')
                    name_sensor = sensor.get('name')
                    value = sensor.get('value')
                    ip_host = ip

                    if not all([id_sensor, name_sensor, value]):
                        continue

                    # Очистка имени датчика (удаляем лишние пробелы и кавычки)
                    clean_name = name_sensor.strip().replace('"', '').replace("'", "")

                    # Улучшенная проверка числового значения
                    try:
                        clean_value = float(value)
                    except ValueError:
                        print(f"Некорректное значение датчика {clean_name}: {value}")
                        continue

                    # Проверяем ID сенсора
                    try:
                        sensor_id = int(id_sensor)
                    except ValueError:
                        print(f"Некорректный ID датчика {clean_name}: {id_sensor}")
                        continue

                    DB().update_data_sensors(
                        id_sensor=sensor_id,
                        name_sensor=clean_name,
                        last_value=clean_value,
                        ip_host=ip_host
                    )

                except Exception as e:
                    print(f"Ошибка при обработке датчика {sensor.get('name', 'unknown')} с {ip}: {str(e)}")
