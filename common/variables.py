import logging

# Порт по умолчанию для сетевого ваимодействия
DEFAULT_PORT = 7778
# IP адрес по умолчанию для подключения клиента
DEFAULT_IP_ADDRESS = '127.0.0.1'
# Максимальная очередь подключений
MAX_CONNECTIONS = 5
# Максимальная длинна сообщения в байтах
MAX_PACKAGE_LENGTH = 1024
# Кодировка проекта
ENCODING = 'utf-8'

SERVER_DATABASE = 'sqlite:///server.sqlite'

# Прококол JIM основные ключи:
ACTION = 'action'
TIME = 'time'
USER = 'user'
ACCOUNT_NAME = 'account_name'
SENDER = 'from'
DESTINATION = 'to'

# Прочие ключи, используемые в протоколе
PRESENCE = 'presence'
RESPONSE = 'response'
ERROR = 'error'
EXIT = 'exit'

# Настройки логгеров.
LOGGING_LEVEL = logging.DEBUG

# Папка для лог файлов внутри приложения.
LOGS_DIR = '\logs'

FILE_NAME_CLIENT_LOG = 'client.log'
FILE_NAME_SERVER_LOG = 'server.log'

LOGGER_NAME_CLIENT = 'client'
LOGGER_NAME_SERVER = 'server'

MESSAGE = 'message'
MESSAGE_TEXT = 'text'
DEFAULT_CLIENT_MODE = 'listen'
DEFAULT_CLIENT_NAME = 'X-MAN'

# Словари - ответы:
# 200
RESPONSE_200 = {RESPONSE: 200}
# 400
RESPONSE_400 = {
    RESPONSE: 400,
    ERROR: None
}