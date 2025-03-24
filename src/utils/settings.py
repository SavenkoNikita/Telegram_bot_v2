import os
from dotenv import load_dotenv
import logging

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    DATABASE_URL = os.getenv('DATABASE_URL')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


logger = logging.getLogger("ConfigLogger")
if not logger.hasHandlers():
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': ProductionConfig
}

# Log the active configuration
logger.info(f"Active configuration loaded: {config['default'].__name__}")
