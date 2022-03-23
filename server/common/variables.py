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
GET_CONTACTS = 'get_contacts'
LIST_INFO = 'data_list'
REMOVE_CONTACT = 'remove'
ADD_CONTACT = 'add'
USERS_REQUEST = 'get_users'
DATA = 'bin'
PUBLIC_KEY = 'pubkey'
MESSAGE = 'message'
MESSAGE_TEXT = 'mess_text'
PUBLIC_KEY_REQUEST = 'pubkey_need'

# Настройки логгеров.
LOGGING_LEVEL = logging.DEBUG

# Папка для лог файлов внутри приложения.
LOGS_DIR = '\log\logs'

FILE_NAME_CLIENT_LOG = 'client.log'
FILE_NAME_SERVER_LOG = 'server.log'

LOGGER_NAME_CLIENT = 'client'
LOGGER_NAME_SERVER = 'server'

DEFAULT_CLIENT_MODE = 'listen'
DEFAULT_CLIENT_NAME = 'user_100'
DEFAULT_CLIENT_PASS = '1'

# Словари - ответы:
# 200
RESPONSE_200 = {RESPONSE: 200}
# 400
RESPONSE_400 = {
    RESPONSE: 400,
    ERROR: None
}
# 202
RESPONSE_202 = {RESPONSE: 202,
                LIST_INFO:None}

# 205
RESPONSE_205 = {
    RESPONSE: 205
}

# 511
RESPONSE_511 = {
    RESPONSE: 511,
    DATA: None
}