class Frame:
    """L2 - Ethernet Frame"""
    def __init__(self, src_mac, dst_mac, payload):
        self.src_mac = src_mac
        self.dst_mac = dst_mac
        self.payload = payload  # Packet

    def __repr__(self):
        return f"[Frame] {self.src_mac} → {self.dst_mac} | {self.payload}"


class Packet:
    """L3 - IP Packet"""
    def __init__(self, src_ip, dst_ip, payload):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.payload = payload  # Segment

    def __repr__(self):
        return f"[Packet] {self.src_ip} → {self.dst_ip} | {self.payload}"


class Segment:
    """L4 - TCP/UDP Segment"""
    def __init__(self, src_port, dst_port, data):
        self.src_port = src_port
        self.dst_port = dst_port
        self.data = data

    def __repr__(self):
        return f"[Segment] :{self.src_port} → :{self.dst_port} | {self.data}"


# 캡슐화 시뮬레이션
data = "GET /api/switches HTTP/1.1"
segment = Segment(src_port=54321, dst_port=80, data=data)
packet = Packet(src_ip="192.168.1.10", dst_ip="192.168.1.1", payload=segment)
frame = Frame(src_mac="AA:BB:CC:11:22:33", dst_mac="AA:BB:CC:44:55:66", payload=packet)

print(frame)
# [Frame] AA:BB:CC:11:22:33 → AA:BB:CC:44:55:66 | [Packet] 192.168.1.10 → 192.168.1.1 | ...


# 스위치 CAM Table 시뮬레이션
class Switch:
    def __init__(self, name):
        self.name = name
        self.cam_table = {}  # mac -> port
        self.ports = {}      # port -> list of connected macs

    def receive_frame(self, in_port, frame):
        # MAC 학습
        self.cam_table[frame.src_mac] = in_port

        # 전달 결정
        if frame.dst_mac == "FF:FF:FF:FF:FF:FF":
            print(f"[{self.name}] Broadcast → flood all ports")
        elif frame.dst_mac in self.cam_table:
            out_port = self.cam_table[frame.dst_mac]
            print(f"[{self.name}] Unicast → port {out_port}")
        else:
            print(f"[{self.name}] Unknown MAC → flood all ports")


sw = Switch("SW-CORE-01")
f1 = Frame("AA:BB:CC:11:22:33", "AA:BB:CC:44:55:66", "data")
sw.receive_frame(in_port=1, frame=f1)  # 학습 후 flood (모름)
sw.receive_frame(in_port=2, frame=Frame("AA:BB:CC:44:55:66", "AA:BB:CC:11:22:33", "reply"))
# 이제 포트1이 학습됨
f2 = Frame("AA:BB:CC:44:55:66", "AA:BB:CC:11:22:33", "data2")
sw.receive_frame(in_port=2, frame=f2)  # Unicast → port 1
