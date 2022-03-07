"""Программа-клиент"""
import logging
import sys
from PyQt5.QtWidgets import QApplication

from common.variables import *

from client.database import ClientDatabase
from client.transport import ClientTransport
from client.main_window import ClientMainWindow
from client.start_dialog import UserNameDialog

logger = logging.getLogger(LOGGER_NAME_CLIENT)

def get_settings():
    try:
        server_address = sys.argv[1]
        server_port = int(sys.argv[2])
        client_name = sys.argv[3]

        if server_port < 1024 or server_port > 65535:
            raise ValueError('В качестве порта может быть указано только число в диапазоне от 1024 до 65535.')

    except Exception:
        server_address = DEFAULT_IP_ADDRESS
        server_port = DEFAULT_PORT
        client_name = DEFAULT_CLIENT_NAME

    return server_address, server_port, client_name


if __name__ == '__main__':

    settings = get_settings()
    server_address = settings[0]
    server_port = settings[1]
    client_name = settings[2]

    # Создаём клиентокое приложение
    client_app = QApplication(sys.argv)

    # Если имя пользователя не было указано в командной строке то запросим его
    if not client_name:
        start_dialog = UserNameDialog()
        client_app.exec_()
        # Если пользователь ввёл имя и нажал ОК, то сохраняем ведённое и удаляем объект, инааче выходим
        if start_dialog.ok_pressed:
            client_name = start_dialog.client_name.text()
            del start_dialog
        else:
            exit(0)

    # Записываем логи
    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , порт: {server_port}, имя пользователя: {client_name}')

    # Создаём объект базы данных
    database = ClientDatabase(client_name)

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientTransport(server_port, server_address, database, client_name)
    except Exception as error:
        print(error)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {client_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.transport_shutdown()
    transport.join()
