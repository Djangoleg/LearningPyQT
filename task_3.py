"""
3.	Написать функцию host_range_ping_tab(), возможности которой основаны на функции из примера 2.
Но в данном случае результат должен быть итоговым по всем ip-адресам, представленным в табличном формате
(использовать модуль tabulate). Таблица должна состоять из двух колонок.
"""
from ipaddress import ip_address, IPv4Address
from itertools import repeat
from tabulate import tabulate

from task_2 import host_range_ping


def host_range_ping_tab(start_address: IPv4Address, end_address: IPv4Address):
    lists = host_range_ping(start_address, end_address)
    unreachable = lists[0]
    reachable = lists[1]
    headers = ['Address', 'Status']
    reachable = list(zip(reachable, repeat('reachable')))
    unreachable = list(zip(unreachable, repeat('unreachable')))
    return tabulate(reachable + unreachable, headers, tablefmt='lineabove')


if __name__ == '__main__':
    start_addr = ip_address('192.168.0.1')
    end_addr = ip_address('192.168.0.5')
    table = host_range_ping_tab(start_addr, end_addr)
    print(table)
