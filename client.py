"""Программа-клиент"""
import logging
import sys
import json
import socket
import threading
import time
from os import system

from common.variables import ACTION, PRESENCE, TIME, USER, ACCOUNT_NAME, \
    RESPONSE, ERROR, DEFAULT_IP_ADDRESS, DEFAULT_PORT, LOGGER_NAME_CLIENT, DEFAULT_CLIENT_MODE, SENDER, MESSAGE_TEXT, \
    MESSAGE, DEFAULT_CLIENT_NAME, DESTINATION, EXIT
from common.utils import get_message, send_message

from  log.config_client_log import client_logger
from log.decorator_log import Log
from metaclasses import ClientMaker

logger = logging.getLogger(LOGGER_NAME_CLIENT)

class Client(metaclass=ClientMaker):

    @Log()
    def __init__(self):
        '''
        Инициализация параметров коммандной строки
        client.py 192.168.1.2 8079
        '''
        try:
            server_address = sys.argv[1]
            server_port = int(sys.argv[2])
            client_name = sys.argv[3]
            system("title " + client_name)

            if server_port < 1024 or server_port > 65535:
                raise ValueError('В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')

            self.client_settings = (server_address, server_port)
            self.client_name = client_name

        except Exception as e:
            self.client_settings = (DEFAULT_IP_ADDRESS, DEFAULT_PORT)
            self.client_mode = DEFAULT_CLIENT_MODE
            self.client_name = DEFAULT_CLIENT_NAME
    @Log()
    def get_transport(self):
        # Инициализация сокета и обмен
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect(self.client_settings)

        return transport

    @Log()
    def message_from_server(self, sock, client_name):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            try:
                message = get_message(sock)
                if ACTION in message and message[ACTION] == MESSAGE and \
                        SENDER in message and DESTINATION in message \
                        and MESSAGE_TEXT in message and message[DESTINATION] == client_name:
                    print(f'\nПолучено сообщение от пользователя {message[SENDER]}:'
                          f'\n{message[MESSAGE_TEXT]}')
                    logger.info(f'Получено сообщение от пользователя {message[SENDER]}:'
                                f'\n{message[MESSAGE_TEXT]}')
                else:
                    logger.error(f'Получено некорректное сообщение с сервера: {message}')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                logger.critical(f'Потеряно соединение с сервером.')
                break

    @Log()
    def create_message(self, sock):
        """
        Функция запрашивает кому отправить сообщение и само сообщение,
        и отправляет полученные данные на сервер
        :param sock:
        :param account_name:
        :return:
        """
        to_user = input('Введите получателя сообщения: ')
        message = input('Введите сообщение для отправки: ')
        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.client_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(sock, message_dict)
            logger.info(f'Отправлено сообщение для пользователя {to_user}')
        except:
            logger.critical('Потеряно соединение с сервером.')
            sys.exit(1)

    def print_help(self):
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')

    @Log()
    def create_exit_message(self):
        """Функция создаёт словарь с сообщением о выходе"""
        return {
            ACTION: EXIT,
            TIME: time.time(),
            ACCOUNT_NAME: self.client_name
        }

    @Log()
    def user_interactive(self, sock):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        self.print_help()
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                self.create_message(sock)
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                send_message(sock, self.create_exit_message())
                print('Завершение соединения.')
                logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')

    @Log()
    def create_presence(self):
        '''
        Функция генерирует запрос о присутствии клиента
        :param account_name:
        :return:
        '''
        # {'action': 'presence', 'time': 1573760672.167031, 'user': {'account_name': 'Guest'}}
        out = {
            ACTION: PRESENCE,
            TIME: time.time(),
            USER: {
                ACCOUNT_NAME: self.client_name
            }
        }
        return out

    @Log()
    def process_answer(self, message):
        '''
        Функция разбирает ответ сервера
        :param message:
        :return:
        '''
        if RESPONSE in message:
            if message[RESPONSE] == 200:
                return '200 : OK'
            return f'400 : {message[ERROR]}'
        raise ValueError

    @Log()
    def start(self):

        print('Консольный месседжер. Клиентский модуль.')

        # Если имя пользователя не было задано, необходимо запросить пользователя.
        if not self.client_name:
            self.client_name = input('Введите имя пользователя: ')

        logger.info(
            f'Запущен клиент с парамертами: адрес сервера: {self.client_settings[0]}, '
            f'порт: {self.client_settings[1]}, имя пользователя: {self.client_name}')

        try:
            transport = self.get_transport()
            message_to_server = self.create_presence()
            send_message(transport, message_to_server)
            answer = self.process_answer(get_message(transport))
            logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером.')

        except (ValueError, json.JSONDecodeError):
            logger.error('Не удалось декодировать сообщение сервера.')
            sys.exit(1)

        # Если соединение с сервером установлено корректно,
        # запускаем клиенский процесс приёма сообщний
        receiver = threading.Thread(target=self.message_from_server, args=(transport, self.client_name,))
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = threading.Thread(target=self.user_interactive, args=(transport,))
        user_interface.daemon = True
        user_interface.start()
        logger.debug('Запущены процессы')

        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break

if __name__ == '__main__':
    client = Client()
    client.start()

