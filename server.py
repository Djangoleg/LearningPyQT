import logging
import select
import socket
import sys
import json
from threading import Thread
import time
from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, LOGGER_NAME_SERVER, MESSAGE, SENDER, MESSAGE_TEXT, DESTINATION, EXIT, \
    RESPONSE_400, RESPONSE_200
from common.utils import get_message, send_message
from descrptors import Port, Host

from log.config_server_log import server_logger
from log.decorator_log import Log
from metaclasses import ServerMaker
from server_database import ServerStorage

logger = logging.getLogger(LOGGER_NAME_SERVER)


class Server(Thread, metaclass=ServerMaker):
    listen_port = Port()
    listen_address = Host()
    server_db = ServerStorage()

    def __init__(self):
        super().__init__()

    @Log()
    def __get_settings__(self):
        '''
       Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
       Сначала обрабатываем порт:
       server.py -p 8079 -a 192.168.1.2
       :return:
       '''
        try:
            if '-p' in sys.argv:
                self.listen_port = int(sys.argv[sys.argv.index('-p') + 1])
            else:
                self.listen_port = DEFAULT_PORT
        except IndexError:
            logger.error('После параметра -\'p\' необходимо указать номер порта.')
            sys.exit(1)

        # Затем загружаем какой адрес слушать.
        try:
            if '-a' in sys.argv:
                self.listen_address = sys.argv[sys.argv.index('-a') + 1]
            else:
                self.listen_address = ''

        except IndexError:
            logger.error('После параметра \'a\'- необходимо указать адрес, который будет слушать сервер.')
            sys.exit(1)

        return (self.listen_address, self.listen_port)

    @Log()
    def process_client_message(self, message, messages_list, client, clients, names):
        """
        Обработчик сообщений от клиентов, принимает словарь - сообщение от клиента,
        проверяет корректность, отправляет словарь-ответ в случае необходимости.
        :param message:
        :param messages_list:
        :param client:
        :param clients:
        :param names:
        :return:
        """
        logger.debug(f'Разбор сообщения от клиента : {message}')
        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and \
                TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован,
            # регистрируем, иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in names.keys():
                names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.server_db.user_login(message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                clients.remove(client)
                client.close()
            return
        # Если это сообщение, то добавляем его в очередь сообщений.
        # Ответ не требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and \
                DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message:
            messages_list.append(message)
            return
        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message:
            self.server_db.user_logout(message[ACCOUNT_NAME])
            clients.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            return
        # Иначе отдаём Bad request
        else:
            response = RESPONSE_400
            response[ERROR] = 'Запрос некорректен.'
            send_message(client, response)
            return

    @Log()
    def process_message(self, message, names, listen_socks):
        """
        Функция адресной отправки сообщения определённому клиенту. Принимает словарь сообщение,
        список зарегистрированых пользователей и слушающие сокеты. Ничего не возвращает.
        :param message:
        :param names:
        :param listen_socks:
        :return:
        """
        if message[DESTINATION] in names and names[message[DESTINATION]] in listen_socks:
            send_message(names[message[DESTINATION]], message)
            logger.info(f'Отправлено сообщение пользователю {message[DESTINATION]} '
                        f'от пользователя {message[SENDER]}.')
        elif message[DESTINATION] in names and names[message[DESTINATION]] not in listen_socks:
            raise ConnectionError
        else:
            print(f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                  f'отправка сообщения невозможна.')
            logger.error(
                f'Пользователь {message[DESTINATION]} не зарегистрирован на сервере, '
                f'отправка сообщения невозможна.')

    @Log()
    def print_help(self):
        print('Поддерживаемые комманды:')
        print('users - список известных пользователей')
        print('connected - список подключенных пользователей')
        print('loghist - история входов пользователя')
        print('exit - завершение работы сервера.')
        print('help - вывод справки по поддерживаемым командам')

    @Log()
    def run(self):
        server_settings = self.__get_settings__()

        logger.info(
            f'Запущен сервер, порт для подключений: {server_settings[1]}, '
            f'адрес с которого принимаются подключения: {server_settings[0]}. '
            f'Если адрес не указан, принимаются соединения с любых адресов.')

        # Готовим сокет.
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.bind(server_settings)
        transport.settimeout(0.5)

        # Слушаем порт.
        transport.listen(MAX_CONNECTIONS)

        # Список клиентов, очередь сообщений.
        clients = []
        messages = []
        # Словарь, содержащий имена пользователей и соответствующие им сокеты.
        names = dict()

        while True:
            # Ждём подключения, если таймаут вышел, ловим исключение.
            try:
                client, client_address = transport.accept()
            except OSError:
                pass
            else:
                logger.info(f'Установлено соедение с клиентом: {client_address}')
                print(f'Установлено соедение с клиентом: {client_address}')
                clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            # Проверяем на наличие ждущих клиентов.
            try:
                if clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(clients, clients, [], 0)
            except OSError:
                pass

            # принимаем сообщения и если там есть сообщения,
            # кладём в словарь, если ошибка, исключаем клиента.
            if recv_data_lst:
                for client_with_message in recv_data_lst:
                    try:
                        client_message = get_message(client_with_message)
                        print(f'Получено сообщение от клиента: {client_message}')
                        self.process_client_message(client_message, messages, client_with_message, clients, names)
                    except:
                        logger.info(f'Клиент {client_with_message.getpeername()} '
                                    f'отключился от сервера.')
                        clients.remove(client_with_message)

            # Если есть сообщения, обрабатываем каждое.
            for i in messages:
                try:
                    self.process_message(i, names, send_data_lst)
                except Exception:
                    logger.info(f'Связь с клиентом с именем {i[DESTINATION]} была потеряна')
                    clients.remove(names[i[DESTINATION]])
                    del names[i[DESTINATION]]
            messages.clear()

    @staticmethod
    def up():
        # Стартуем сервер отдельно.
        server = Server()
        server.daemon = True
        server.start()

        # Печатаем справку:
        server.print_help()

        while True:

            command = input('Введите комманду: \n')
            if command == 'help':
                server.print_help()
            elif command == 'exit':
                break
            elif command == 'users':
                for user in sorted(server.server_db.users_list()):
                    print(f'Пользователь {user[0]}, последний вход: {user[1]}')
            elif command == 'connected':
                for user in sorted(server.server_db.active_users_list()):
                    print(
                        f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
            elif command == 'loghist':
                name = input(
                    'Введите имя пользователя для просмотра истории. Для вывода всей истории, просто нажмите Enter: ')
                for user in sorted(server.server_db.login_history(name)):
                    print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
            else:
                print('Команда не распознана.')


if __name__ == '__main__':
    Server.up()
