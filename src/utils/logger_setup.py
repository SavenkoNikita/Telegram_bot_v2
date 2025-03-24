import logging
from logging.handlers import RotatingFileHandler


def setup_logger(log_file: str = "bot.log", level: int = logging.INFO):
    """
    Настраивает и возвращает логгер приложения.
    
    :param log_file: Имя файла, куда будут записываться логи.
    :param level: Уровень логирования.
    :return: Настроенный объект логгера.
    """
    logger = logging.getLogger("TelegramBotLogger")
    logger.setLevel(level)

    # Удаление существующих хендлеров, чтобы избежать дублирования
    if logger.hasHandlers():
        logger.handlers.clear()

    # Формат сообщения логов
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
    )

    # Консольный хендлер (вывод в консоль)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый хендлер (ротация логов до 5MB, хранение до 3 бэкапов)
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Логируем успешную настройку
    logger.info("Логгер успешно настроен")

    return logger
