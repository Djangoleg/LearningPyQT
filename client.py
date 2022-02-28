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
    MESSAGE, DEFAULT_CLIENT_NAME, DESTINATION, EXIT, GET_CONTACTS, LIST_INFO, REMOVE_CONTACT, ADD_CONTACT, USERS_REQUEST
from common.utils import get_message, send_message

from  log.config_client_log import client_logger
from log.decorator_log import Log
from metaclasses import ClientMaker
from client_database import ClientDatabase

logger = logging.getLogger(LOGGER_NAME_CLIENT)

# Объект блокировки сокета и работы с базой данных
sock_lock_send = threading.Lock()
database_lock_send = threading.Lock()

sock_lock_get = threading.Lock()
database_lock_get = threading.Lock()


class Client(metaclass=ClientMaker):

    @Log()
    def __init__(self):
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


    def contacts_list_request(self, sock, name):
        """
        Функция запрос контакт листа.
        :param sock:
        :param name:
        :return:
        """
        logger.debug(f'Запрос контакт листа для пользователся {name}')
        req = {
            ACTION: GET_CONTACTS,
            TIME: time.time(),
            USER: name
        }
        logger.debug(f'Сформирован запрос {req}')
        send_message(sock, req)
        ans = get_message(sock)
        logger.debug(f'Получен ответ {ans}')
        if RESPONSE in ans and ans[RESPONSE] == 202:
            return ans[LIST_INFO]
        else:
            raise Exception

    # Функция добавления пользователя в контакт лист
    def add_contact(self, sock, contact):
        logger.debug(f'Создание контакта {contact}')
        req = {
            ACTION: ADD_CONTACT,
            TIME: time.time(),
            USER: self.client_name,
            ACCOUNT_NAME: contact
        }
        send_message(sock, req)
        # ans = get_message(sock)
        # if RESPONSE in ans and ans[RESPONSE] == 200:
        #     pass
        # else:
        #     raise Exception('Ошибка создания контакта')
        # print('Удачное создание контакта.')

    # Функция запроса списка известных пользователей
    def user_list_request(self, sock, username):
        logger.debug(f'Запрос списка известных пользователей {username}')
        req = {
            ACTION: USERS_REQUEST,
            TIME: time.time(),
            ACCOUNT_NAME: username
        }
        send_message(sock, req)
        ans = get_message(sock)
        if RESPONSE in ans and ans[RESPONSE] == 202:
            return ans[LIST_INFO]
        else:
            raise Exception

    # Функция удаления пользователя из контакт листа
    def remove_contact(self, sock, username, contact):
        logger.debug(f'Создание контакта {contact}')
        req = {
            ACTION: REMOVE_CONTACT,
            TIME: time.time(),
            USER: username,
            ACCOUNT_NAME: contact
        }
        send_message(sock, req)
        ans = get_message(sock)
        if RESPONSE in ans and ans[RESPONSE] == 200:
            pass
        else:
            raise Exception('Ошибка удаления клиента')
        print('Удачное удаление')

    # Функция инициализатор базы данных. Запускается при запуске, загружает данные в базу с сервера.
    def database_load(self, sock, username):
        # Загружаем список известных пользователей
        try:
            users_list = self.user_list_request(sock, username)
        except Exception:
            logger.error('Ошибка запроса списка известных пользователей.')
        else:
            self.database.add_users(users_list)

        # Загружаем список контактов
        try:
            contacts_list = self.contacts_list_request(sock, username)
        except Exception:
            logger.error('Ошибка запроса списка контактов.')
        else:
            for contact in contacts_list:
                self.database.add_contact(contact)

    @Log()
    def get_transport(self):
        # Инициализация сокета и обмен
        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        transport.connect(self.client_settings)

        return transport

    @Log()
    def message_from_server(self, sock):
        """Функция - обработчик сообщений других пользователей, поступающих с сервера"""
        while True:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # если не сделать тут задержку, то второй поток может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with sock_lock_get:
                try:
                    message = get_message(sock)

                except OSError as err:
                    if err.errno:
                        logger.critical(f'Системная ошибка.')
                        break
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError, ConnectionResetError):
                    logger.critical(f'Потеряно соединение с сервером.')
                    break
                # Принято некорректное сообщение
                except json.JSONDecodeError:
                    logger.error(f'Не удалось декодировать полученное сообщение.')
                # Если пакет корретно получен выводим в консоль и записываем в базу.
                else:
                    if ACTION in message and message[ACTION] == MESSAGE and SENDER in message and DESTINATION in message \
                            and MESSAGE_TEXT in message and message[DESTINATION] == self.client_name:
                        print(f'\nПолучено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')
                        # Захватываем работу с базой данных и сохраняем в неё сообщение
                        with database_lock_get:
                            try:
                                self.database.save_message(message[SENDER], self.client_name, message[MESSAGE_TEXT])
                            except:
                                logger.error('Ошибка взаимодействия с базой данных')

                        logger.info(f'Получено сообщение от пользователя {message[SENDER]}:\n{message[MESSAGE_TEXT]}')

                    # else:
                    #     logger.error(f'Получено некорректное сообщение с сервера: {message}')

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

        # Проверим, что получатель существует
        with database_lock_send:
            if not self.database.check_user(to_user):
                logger.error(f'Попытка отправить сообщение незарегистрированому получателю: {to_user}')
                return

        message_dict = {
            ACTION: MESSAGE,
            SENDER: self.client_name,
            DESTINATION: to_user,
            TIME: time.time(),
            MESSAGE_TEXT: message
        }
        logger.debug(f'Сформирован словарь сообщения: {message_dict}')

        # Сохраняем сообщения для истории
        with database_lock_send:
            self.database.save_message(self.client_name, to_user, message)

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with sock_lock_send:
            try:
                send_message(sock, message_dict)
                logger.info(f'Отправлено сообщение для пользователя {to_user}')
            except:
                logger.critical('Потеряно соединение с сервером.')
                sys.exit(1)

    @Log()
    def print_help(self):
        """
        Функция выводящяя справку по использованию.
        :return:
        """
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('history - история сообщений')
        print('contacts - список контактов')
        print('edit - редактирование списка контактов')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')


    def print_history(self):
        """
        # Функция выводящяя историю сообщений
        :return:
        """
        ask = input('Показать входящие сообщения - in, исходящие - out, все - просто Enter: ')
        with database_lock_get:
            if ask == 'in':
                history_list = self.database.get_history(to_who=self.client_name)
                for message in history_list:
                    print(f'\nСообщение от пользователя: {message[0]} от {message[3]}:\n{message[2]}')
            elif ask == 'out':
                history_list = self.database.get_history(from_who=self.client_name)
                for message in history_list:
                    print(f'\nСообщение пользователю: {message[1]} от {message[3]}:\n{message[2]}')
            else:
                history_list = self.database.get_history()
                for message in history_list:
                    print(
                        f'\nСообщение от пользователя: {message[0]}, пользователю {message[1]} от {message[3]}\n{message[2]}')


    def edit_contacts(self, sock):
        """
        Функция изменеия контактов.
        :return:
        """
        ans = input('Для удаления введите del, для добавления add: ')
        if ans == 'del':
            edit = input('Введите имя удаляемного контакта: ')
            with database_lock_send:
                if self.database.check_contact(edit):
                    self.database.del_contact(edit)
                else:
                    logger.error('Попытка удаления несуществующего контакта.')
        elif ans == 'add':
            # Проверка на возможность такого контакта
            edit = input('Введите имя создаваемого контакта: ')
            if self.database.check_user(edit):
                with database_lock_send:
                    self.database.add_contact(edit)
                with sock_lock_send:
                    try:
                        self.add_contact(sock, edit)
                    except Exception:
                        logger.error('Не удалось отправить информацию на сервер.')


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
            # Если отправка сообщения - соответствующий метод
            if command == 'message':
                self.create_message(sock)

            # Вывод помощи
            elif command == 'help':
                self.print_help()

            # Выход. Отправляем сообщение серверу о выходе.
            elif command == 'exit':
                # with sock_lock:
                try:
                    send_message(sock, self.create_exit_message())
                except:
                    pass
                print('Завершение соединения.')
                logger.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break

            # Список контактов
            elif command == 'contacts':
                with database_lock_send:
                    contacts_list = self.database.get_contacts()
                for contact in contacts_list:
                    print(contact)

            # Редактирование контактов
            elif command == 'edit':
                self.edit_contacts(sock)

            # история сообщений.
            elif command == 'history':
                self.print_history()

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

            # Инициализация БД.
            self.database = ClientDatabase(self.client_name)
            self.database_load(transport, self.client_name)

            logger.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
            print(f'Установлено соединение с сервером.')

        except (ValueError, json.JSONDecodeError):
            logger.error('Не удалось декодировать сообщение сервера.')
            sys.exit(1)

        # Если соединение с сервером установлено корректно,
        # запускаем клиенский процесс приёма сообщний
        receiver = threading.Thread(target=self.message_from_server, args=(transport,))
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

