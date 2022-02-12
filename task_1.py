"""
1.	Написать функцию host_ping(), в которой с помощью утилиты ping будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес сетевого узла должен создаваться с помощью функции ip_address().
"""
import asyncio
from asyncio import create_subprocess_shell, subprocess
from ipaddress import ip_address
from sys import platform


def get_ip(host):
    """
    Получить адрес, если это возможно.
    :param host:
    :return:
    """
    try:
        return ip_address(host)
    except ValueError:
        return host


def get_ping_key():
    """
    Получить ключ для команды ping,
    которая устанавливает количество отправляемых пакетов.
    """
    key = '-c'
    if platform == 'win32':
        key = '/n'
    return key


async def ping_async(host, unreachable:list, reachable:list):
    """
    Проверить связь с хостом.
    """
    ping_key = get_ping_key()
    proc = await create_subprocess_shell(
        f'ping {ping_key} 2 {host}', stdout=subprocess.PIPE
    )
    await proc.communicate()
    if proc.returncode == 0:
        reachable.append(host)
    else:
        unreachable.append(host)


def host_ping(hosts: list):
    unreachable = list()
    reachable = list()
    for host in hosts:
        asyncio.run(ping_async(get_ip(host), unreachable, reachable))
    return unreachable, reachable


if __name__ == '__main__':
    hosts = ['10.3.3.3', 'mysupersite.com', '127.0.0.1', 'ya.ru', '8.8.8.8', 'mail.ru', '1.1.1.1', 'fe81::3097:69f3:2349:c5c3%9']
    lists = host_ping(hosts)
    unreachable = lists[0]
    reachable = lists[1]
    print(*[f'{host}: Узел недоступен' for host in unreachable], sep='\n')
    print(*[f'{host}: Узел доступен' for host in reachable], sep='\n')

