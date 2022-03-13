import inspect
import logging
import sys
import traceback

from common.variables import LOGGER_NAME_CLIENT, LOGGER_NAME_SERVER

if sys.argv[0].find('client') == -1:
    logger = logging.getLogger(LOGGER_NAME_SERVER)
else:
    logger = logging.getLogger(LOGGER_NAME_CLIENT)

class Log:
    """Класс-декоратор"""
    def __call__(self, func_to_log):
        def log_saver(*args, **kwargs):
            # Обертка.
            ret = func_to_log(*args, **kwargs)
            logger.debug(f'Была вызвана функция {func_to_log.__name__} c параметрами {args}, {kwargs}. '
                         f'Вызов из модуля {func_to_log.__module__}. Вызов из'
                         f' функции {traceback.format_stack()[0].strip().split()[-1]}.'
                         f'Вызов из функции {inspect.stack()[1][3]}', stacklevel=2)
            return ret
        return log_saver
