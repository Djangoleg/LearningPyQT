import configparser
import logging
import os
import sys
from common.variables import LOGGER_NAME_SERVER, DEFAULT_PORT
from log.config_server_log import server_logger
from log.decorator_log import Log
from server.core import MessageProcessor
from server.database import ServerStorage
from server.main_window import MainWindow

from PyQt5.QtWidgets import QApplication, QMessageBox, qApp
from PyQt5.QtCore import Qt

logger = logging.getLogger(LOGGER_NAME_SERVER)


class Server:
    """Класс сервер."""

    @Log()
    def _make_config(self):
        """Создание конфига."""
        self.config = configparser.ConfigParser()
        # dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.getcwd()
        self.config.read(f"{dir_path}/{'server.ini'}")
        # Если конфиг файл загружен правильно, запускаемся, иначе конфиг по
        # умолчанию.
        if 'SETTINGS' in self.config:
            return self.config
        else:
            self.config.add_section('SETTINGS')
            self.config.set('SETTINGS', 'Default_port', str(DEFAULT_PORT))
            self.config.set('SETTINGS', 'Listen_Address', '')
            self.config.set('SETTINGS', 'Database_path', '')
            self.config.set('SETTINGS', 'Database_file', 'server_database.db3')

    def __init__(self):
        self._make_config()

        if self.config['SETTINGS']['Default_port']:
            self.port = int(self.config['SETTINGS']['Default_port'])
        else:
            self.port = DEFAULT_PORT

        if self.config['SETTINGS']['Listen_Address']:
            self.address = self.config['SETTINGS']['Listen_Address']
        else:
            self.address = ''

        if '--no_gui' in sys.argv:
            self.gui_flag = False
        else:
            self.gui_flag = True

        self.database = ServerStorage(
            os.path.join(
                self.config['SETTINGS']['Database_path'],
                self.config['SETTINGS']['Database_file']))

    @Log()
    def start(self):
        """Старт сервера."""

        # Создание экземпляра класса - сервера и его запуск:
        server = MessageProcessor(self.address, self.port, self.database)
        server.daemon = True
        server.start()

        # Если  указан параметр без GUI то запускаем простенький обработчик
        # консольного ввода.
        if not self.gui_flag:
            while True:
                command = input('Введите exit для завершения работы сервера.')
                if command == 'exit':
                    # Если выход, то завршаем основной цикл сервера.
                    server.running = False
                    server.join()
                    break

        # Если не указан запуск без GUI, то запускаем GUI:
        else:
            # Создаём графическое окуружение для сервера:
            server_app = QApplication(sys.argv)
            server_app.setAttribute(Qt.AA_DisableWindowContextHelpButton)
            main_window = MainWindow(self.database, server, self.config)

            # Запускаем GUI
            server_app.exec_()

            # По закрытию окон останавливаем обработчик сообщений.
            server.running = False


if __name__ == '__main__':
    server = Server()
    server.start()
