"""
2.	Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
from ipaddress import ip_address, IPv4Address

from task_1 import host_ping


def host_range_ping(start_address:IPv4Address, end_address:IPv4Address):
    hosts = [start_address + i for i in range(int(end_address) - int(start_address) + 1)]
    return host_ping(hosts)

if __name__ == '__main__':
    start_addr = ip_address('10.3.3.1')
    end_addr = ip_address('10.3.3.5')
    lists = host_range_ping(start_addr, end_addr)
    unreachable = lists[0]
    reachable = lists[1]
    print(*[f'{host}: Узел недоступен' for host in unreachable], sep='\n')
    print(*[f'{host}: Узел доступен' for host in reachable], sep='\n')