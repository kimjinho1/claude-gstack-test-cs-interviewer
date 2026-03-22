import time
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ArpEntry:
    ip: str
    mac: str
    created_at: float = field(default_factory=time.time)
    ttl: int = 120  # seconds

    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class ArpTable:
    """호스트의 ARP 테이블"""
    def __init__(self):
        self._table: dict[str, ArpEntry] = {}

    def lookup(self, ip: str) -> Optional[str]:
        entry = self._table.get(ip)
        if entry and not entry.is_expired():
            return entry.mac
        if entry:
            del self._table[ip]  # 만료 항목 제거
        return None

    def learn(self, ip: str, mac: str):
        self._table[ip] = ArpEntry(ip=ip, mac=mac)
        print(f"[ARP] 학습: {ip} → {mac}")

    def show(self):
        print("\n[ARP Table]")
        for ip, entry in self._table.items():
            status = "expired" if entry.is_expired() else "valid"
            print(f"  {ip:15} → {entry.mac}  ({status})")


class Host:
    """네트워크 호스트 (PC, 서버 등)"""
    def __init__(self, ip: str, mac: str, gateway_ip: str, subnet: str):
        self.ip = ip
        self.mac = mac
        self.gateway_ip = gateway_ip
        self.subnet_prefix = subnet  # e.g. "192.168.1."
        self.arp_table = ArpTable()

    def _is_same_subnet(self, dst_ip: str) -> bool:
        return dst_ip.startswith(self.subnet_prefix)

    def send(self, dst_ip: str, data: str, network: "Network"):
        # 같은 서브넷이면 직접, 아니면 게이트웨이 경유
        next_hop_ip = dst_ip if self._is_same_subnet(dst_ip) else self.gateway_ip

        dst_mac = self.arp_table.lookup(next_hop_ip)
        if not dst_mac:
            print(f"[{self.ip}] ARP Request: {next_hop_ip}의 MAC은?")
            dst_mac = network.arp_request(self, next_hop_ip)
            if not dst_mac:
                print(f"[{self.ip}] ARP 실패 → 전송 불가")
                return
            self.arp_table.learn(next_hop_ip, dst_mac)

        print(f"[{self.ip}] 전송: dst_ip={dst_ip}, dst_mac={dst_mac}, data={data}")


class Network:
    """네트워크 시뮬레이터"""
    def __init__(self):
        self.hosts: dict[str, Host] = {}

    def add_host(self, host: Host):
        self.hosts[host.ip] = host

    def arp_request(self, requester: Host, target_ip: str) -> Optional[str]:
        """브로드캐스트 ARP Request 시뮬레이션"""
        target = self.hosts.get(target_ip)
        if target:
            print(f"[{target.ip}] ARP Reply: 내 MAC은 {target.mac}")
            # 응답 호스트도 requester MAC 학습 (ARP Reply에 포함)
            target.arp_table.learn(requester.ip, requester.mac)
            return target.mac
        return None


# 시뮬레이션
net = Network()
pc_a = Host("192.168.1.10", "AA:BB:CC:11:22:33", gateway_ip="192.168.1.1", subnet="192.168.1.")
pc_b = Host("192.168.1.20", "AA:BB:CC:44:55:66", gateway_ip="192.168.1.1", subnet="192.168.1.")
gw   = Host("192.168.1.1",  "AA:BB:CC:00:00:01", gateway_ip="192.168.1.1", subnet="192.168.1.")

net.add_host(pc_a)
net.add_host(pc_b)
net.add_host(gw)

print("=== 첫 번째 통신 (ARP 발생) ===")
pc_a.send("192.168.1.20", "Hello", net)

print("\n=== 두 번째 통신 (ARP 캐시 활용) ===")
pc_a.send("192.168.1.20", "World", net)

print("\n=== 다른 서브넷 통신 (게이트웨이 경유) ===")
pc_a.send("10.0.0.5", "External", net)
# → 게이트웨이 MAC ARP 조회 후 전송

pc_a.arp_table.show()