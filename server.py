import logging
import select
import socket
import sys
import json
import time

from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, LOGGER_NAME_SERVER, MESSAGE, SENDER, MESSAGE_TEXT, DESTINATION, EXIT, \
    RESPONSE_400, RESPONSE_200
from common.utils import get_message, send_message
from descrptors import Port

from  log.config_server_log import server_logger
from log.decorator_log import Log
from metaclasses import ServerMaker

logger = logging.getLogger(LOGGER_NAME_SERVER)

class Server(metaclass=ServerMaker):
    listen_port = Port()

    @Log()
    def __get_settings(self):
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
                listen_address = sys.argv[sys.argv.index('-a') + 1]
            else:
                listen_address = ''

        except IndexError:
            logger.error('После параметра \'a\'- необходимо указать адрес, который будет слушать сервер.')
            sys.exit(1)

        return (listen_address, self.listen_port)

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
    def start(self):

        server_settings = self.__get_settings()

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


if __name__ == '__main__':
    server = Server()
    server.start()
