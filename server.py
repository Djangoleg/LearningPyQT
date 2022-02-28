import configparser
import logging
import os
import select
import socket
import sys
import json
import threading
from threading import Thread
import time
from common.variables import ACTION, ACCOUNT_NAME, RESPONSE, MAX_CONNECTIONS, \
    PRESENCE, TIME, USER, ERROR, DEFAULT_PORT, LOGGER_NAME_SERVER, MESSAGE, SENDER, MESSAGE_TEXT, DESTINATION, EXIT, \
    RESPONSE_400, RESPONSE_200, LIST_INFO, REMOVE_CONTACT, RESPONSE_202, GET_CONTACTS, ADD_CONTACT, USERS_REQUEST
from common.utils import get_message, send_message
from descrptors import Port, Host

from log.config_server_log import server_logger
from log.decorator_log import Log
from metaclasses import ServerMaker
from server_database import ServerStorage

from PyQt5.QtWidgets import QApplication, QMessageBox, qApp
from PyQt5.QtCore import QTimer, QCoreApplication
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem

logger = logging.getLogger(LOGGER_NAME_SERVER)
# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
flag_lock = threading.Lock()
daemon_kill = False


class Server(Thread, metaclass=ServerMaker):
    listen_port = Port()
    listen_address = Host()

    def __init__(self, database:ServerStorage):
        self.server_db = database
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
        global new_connection
        logger.debug(f'Разбор сообщения от клиента : {message}')

        # Если это сообщение о присутствии, принимаем и отвечаем
        if ACTION in message and message[ACTION] == PRESENCE and TIME in message and USER in message:
            # Если такой пользователь ещё не зарегистрирован, регистрируем,
            # иначе отправляем ответ и завершаем соединение.
            if message[USER][ACCOUNT_NAME] not in names.keys():
                names[message[USER][ACCOUNT_NAME]] = client
                client_ip, client_port = client.getpeername()
                self.server_db.user_login(
                    message[USER][ACCOUNT_NAME], client_ip, client_port)
                send_message(client, RESPONSE_200)
                with flag_lock:  # add_new
                    new_connection = True
            else:
                response = RESPONSE_400
                response[ERROR] = 'Имя пользователя уже занято.'
                send_message(client, response)
                clients.remove(client)
                client.close()
            return

        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не
        # требуется.
        elif ACTION in message and message[ACTION] == MESSAGE and DESTINATION in message and TIME in message \
                and SENDER in message and MESSAGE_TEXT in message and names[message[SENDER]] == client:
            messages_list.append(message)
            self.server_db.process_message(
                message[SENDER], message[DESTINATION])
            return

        # Если клиент выходит
        elif ACTION in message and message[ACTION] == EXIT and ACCOUNT_NAME in message \
                and names[message[ACCOUNT_NAME]] == client:
            self.server_db.user_logout(message[ACCOUNT_NAME])
            logger.info(
                f'Клиент {message[ACCOUNT_NAME]} корректно отключился от сервера.')
            clients.remove(names[message[ACCOUNT_NAME]])
            names[message[ACCOUNT_NAME]].close()
            del names[message[ACCOUNT_NAME]]
            with flag_lock:  # add_new
                new_connection = True
            return

        # Если это запрос контакт-листа
        elif ACTION in message and message[ACTION] == GET_CONTACTS and USER in message and \
                names[message[USER]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = self.server_db.get_contacts(message[USER])
            send_message(client, response)  # add_new

        # Если это добавление контакта
        elif ACTION in message and message[ACTION] == ADD_CONTACT and ACCOUNT_NAME in message and USER in message \
                and names[message[USER]] == client:
            self.server_db.add_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)  # add_new

        # Если это удаление контакта
        elif ACTION in message and message[ACTION] == REMOVE_CONTACT and ACCOUNT_NAME in message and USER in message \
                and names[message[USER]] == client:
            self.server_db.remove_contact(message[USER], message[ACCOUNT_NAME])
            send_message(client, RESPONSE_200)  # add_new

        # Если это запрос известных пользователей
        elif ACTION in message and message[ACTION] == USERS_REQUEST and ACCOUNT_NAME in message \
                and names[message[ACCOUNT_NAME]] == client:
            response = RESPONSE_202
            response[LIST_INFO] = [user[0]
                                   for user in self.server_db.users_list()]
            send_message(client, response)  # add_new

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
    def run(self):
        global daemon_kill
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

            if daemon_kill:
                break


    @staticmethod
    def up(config, database):
        # Стартуем сервер отдельно.
        server = Server(database)
        server.daemon = True
        server.start()
        ServerGui(config, database)


class ServerGui:

    def __init__(self, config:configparser.ConfigParser, database:ServerStorage):

        self.server_db = database
        self.config = config

        # Создаём графическое окуружение для сервера:
        server_app = QApplication(sys.argv)  # создаем приложение
        self.main_window = MainWindow()
        # ЗАПУСК РАБОТАЕТ ПАРАЛЕЛЬНО СЕРВЕРА(К ОКНУ)
        # ГЛАВНОМ ПОТОКЕ ЗАПУСКАЕМ НАШ GUI - ГРАФИЧЕСКИЙ ИНТЕРФЕС ПОЛЬЗОВАТЕЛЯ

        # Инициализируем параметры в окна Главное окно
        self.main_window.statusBar().showMessage('Server Working')  # подвал
        self.main_window.active_clients_table.setModel(
            gui_create_model(self.server_db))  # заполняем таблицу основного окна делаем разметку и заполянем ее
        self.main_window.active_clients_table.resizeColumnsToContents()
        self.main_window.active_clients_table.resizeRowsToContents()

        # Таймер, обновляющий список клиентов 1 раз в секунду
        timer = QTimer()
        timer.timeout.connect(self.list_update)
        timer.start(1000)

        # Связываем кнопки с процедурами
        self.main_window.exitAction.triggered.connect(self.quit_app)
        self.main_window.refresh_button.triggered.connect(self.list_update)
        self.main_window.show_history_button.triggered.connect(self.show_statistics)
        self.main_window.config_btn.triggered.connect(self.server_config)

        # Запускаем GUI
        server_app.exec_()

    def quit_app(self):
        global daemon_kill
        daemon_kill = True
        sys.exit()

    # Функция обновляющяя список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update(self):
        global new_connection
        if new_connection:
            self.main_window.active_clients_table.setModel(
                gui_create_model(self.server_db))
            self.main_window.active_clients_table.resizeColumnsToContents()
            self.main_window.active_clients_table.resizeRowsToContents()
            with flag_lock:
                new_connection = False

    # Функция создающяя окно со статистикой клиентов
    def show_statistics(self):
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(self.server_db))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        # stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config(self):
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(self.config['SETTINGS']['Database_path'])
        config_window.db_file.insert(self.config['SETTINGS']['Database_file'])
        config_window.port.insert(self.config['SETTINGS']['Default_port'])
        config_window.ip.insert(self.config['SETTINGS']['Listen_Address'])
        config_window.save_btn.clicked.connect(self.save_server_config)

    # Функция сохранения настроек
    def save_server_config(self):
        global config_window
        message = QMessageBox()
        self.config['SETTINGS']['Database_path'] = config_window.db_path.text()
        self.config['SETTINGS']['Database_file'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            self.config['SETTINGS']['Listen_Address'] = config_window.ip.text()
            if 1023 < port < 65536:
                self.config['SETTINGS']['Default_port'] = str(port)
                print(port)
                with open('server.ini', 'w') as conf:
                    self.config.write(conf)
                    message.information(
                        config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

if __name__ == '__main__':
    # Загрузка файла конфигурации сервера
    dir_path = os.path.dirname(os.path.realpath(__file__))
    config = configparser.ConfigParser()
    config.read(f"{dir_path}/{'server.ini'}")
    database = ServerStorage(os.path.join(config['SETTINGS']['Database_path'], config['SETTINGS']['Database_file']))

    Server.up(config, database)
    ServerGui(config, database)


