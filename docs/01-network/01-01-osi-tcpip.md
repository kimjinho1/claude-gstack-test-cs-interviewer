# 01-01 OSI 7계층 / TCP-IP 4계층

## 개념

**OSI 7계층** : ISO가 정의한 네트워크 통신 표준 모델. 통신을 7개의 독립적인 계층으로 분리해 각 계층이 자기 역할만 담당하게 함.

**TCP/IP 4계층** : 실제 인터넷에서 사용하는 실용 모델. OSI를 단순화한 버전.

| OSI 7계층 | TCP/IP 4계층 | 역할 | 장비/프로토콜 |
|-----------|-------------|------|--------------|
| 7. Application | Application | 앱 프로토콜 | HTTP, SNMP, SSH, DNS |
| 6. Presentation | Application | 인코딩, 암호화 | SSL/TLS, JPEG |
| 5. Session | Application | 세션 유지/관리 | NetBIOS, RPC |
| 4. Transport | Transport | 포트, 신뢰성 전송 | TCP, UDP |
| 3. Network | Internet | IP 주소, 라우팅 | IP, ICMP, 라우터, L3 스위치 |
| 2. Data Link | Network Access | MAC 주소, 프레임 | Ethernet, 스위치, AP |
| 1. Physical | Network Access | 전기/빛/전파 신호 | 케이블, RJ45, SFP, 안테나 |

---

## 동작 원리

### 캡슐화 / 역캡슐화

데이터를 보낼 때 각 계층을 내려가면서 **헤더가 추가**됨.

```
[송신]
App Data
→ L4: [TCP Header | App Data]         ← Segment
→ L3: [IP Header | TCP Header | Data]  ← Packet
→ L2: [MAC Header | IP Header | ... | FCS]  ← Frame
→ L1: 전기 신호로 변환

[수신]
L1: 신호 수신
→ L2: MAC 헤더 확인 후 제거
→ L3: IP 헤더 확인 후 제거
→ L4: TCP 헤더 확인 후 제거
→ App: 최종 데이터 수신
```

### L1 - Physical Layer

- 0과 1 비트를 **전기/빛/전파 신호**로 변환
- 스위치 포트 `link up/down` = L1 이벤트
- AP의 무선 연결 (2.4GHz / 5GHz / 6GHz) = L1
- 장비: RJ45, Cat6 케이블, SFP 광모듈, 안테나

### L2 - Data Link Layer

같은 네트워크(브로드캐스트 도메인) 안에서 **MAC 주소**로 통신.

**MAC 주소**
- 48bit, 16진수 표기 → `AA:BB:CC:DD:EE:FF`
- 앞 24bit = 제조사 OUI / 뒤 24bit = 장비 고유번호
- 같은 L2 세그먼트 안에서만 유효

**Ethernet 프레임 구조**
```
[ Dest MAC | Src MAC | EtherType | Payload | FCS ]
   6 byte    6 byte    2 byte      가변      4 byte
```
- EtherType: `0x0800` = IPv4, `0x0806` = ARP, `0x8100` = VLAN

**스위치의 L2 동작 (MAC 주소 테이블 / CAM Table)**
1. 프레임 수신 → 출발지 MAC을 포트에 매핑해 학습
2. 목적지 MAC이 테이블에 있음 → 해당 포트로만 전달 (Unicast)
3. 목적지 MAC 모름 → 모든 포트로 전달 (Flooding)
4. 목적지 `FF:FF:FF:FF:FF:FF` → 브로드캐스트, 전체 전달

```
CAM Table 예시:
포트1 → AA:BB:CC:11:22:33  (PC)
포트2 → AA:BB:CC:44:55:66  (서버)
포트3 → AA:BB:CC:77:88:99  (AP)
```

**AP의 L2 역할**
- 무선 클라이언트의 802.11 프레임을 Ethernet 프레임으로 변환 (브리징)
- 무선 클라이언트 MAC을 스위치 CAM Table에 학습시킴

**MAC Table / ARP Table은 어떻게 채워지나?**

두 테이블 모두 처음엔 비어 있음. 통신이 발생할 때 채워짐.

MAC Table (스위치): **수동 학습** — 프레임이 들어올 때 출발지 MAC을 자동 기록
```
프레임 수신 → 출발지 MAC + 포트 매핑 → CAM Table에 기록
물어보지 않음. 지나가는 프레임 보고 그냥 배움.
```

ARP Table (PC/서버): **브로드캐스트로 직접 물어봄**
```
1. PC-A: "192.168.1.20의 MAC 알려줘" → ARP Request (브로드캐스트)
2. 스위치: flooding (모르니까) + PC-A MAC 학습
3. PC-B: "내 MAC은 AA:BB:CC:44:55:66" → ARP Reply (유니캐스트)
4. 스위치: PC-B MAC 학습
5. PC-A: ARP Table에 IP→MAC 매핑 저장
```

첫 통신은 항상 브로드캐스트/flooding → 응답 오면 두 테이블 모두 채워짐 → 이후부터 유니캐스트로 직접 전달.

### L3 - Network Layer

- IP 주소로 **다른 네트워크 간** 경로 결정 (라우팅)
- 스위치의 관리 IP, 게이트웨이 설정이 L3 개념

### L4 - Transport Layer

- **포트 번호**로 프로세스 식별
- 스위치에 SSH(22), SNMP(161), HTTPS(443)로 접속하는 게 L4 레벨

---

## 예시 코드 (Python)

캡슐화 구조를 클래스로 표현:

```python
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
```

---

## 면접 예상 질문

- Q: OSI 7계층을 나눈 이유는?
  A: 통신 기능을 계층별로 분리해 각 계층이 독립적으로 동작하게 함. 특정 계층의 기술이 바뀌어도 다른 계층에 영향 없이 교체 가능. 예를 들어 L1이 이더넷에서 광케이블로 바뀌어도 L2 이상은 영향 없음.

- Q: OSI와 TCP/IP 모델의 차이는?
  A: OSI는 이론적 표준 모델(7계층), TCP/IP는 실제 인터넷 구현 모델(4계층). OSI의 5~7계층을 TCP/IP는 Application 하나로 합침. 실무에서는 TCP/IP를 사용하고 OSI는 문제 분석/설명 시 참조.

- Q: 스위치는 몇 계층 장비인가?
  A: 일반 스위치는 L2 장비로 MAC 주소 기반으로 프레임을 전달. L3 스위치는 IP 라우팅도 처리. AP는 L1(무선 신호) + L2(802.11↔Ethernet 브리징)를 처리.

- Q: 데이터 전송 시 헤더가 추가되는 과정을 설명하라.
  A: 캡슐화(Encapsulation). 송신 측에서 L7→L1으로 내려가며 각 계층의 헤더가 앞에 추가됨. 수신 측에서 L1→L7으로 올라가며 각 헤더를 제거(역캡슐화). 스위치는 L2 헤더(MAC)만 처리하고 L3 이상은 그대로 전달.

- Q: 브로드캐스트와 유니캐스트 차이는?
  A: 유니캐스트는 특정 MAC 주소를 가진 단일 장비로 전달. 브로드캐스트(FF:FF:FF:FF:FF:FF)는 같은 L2 네트워크의 모든 장비로 전달. 스위치는 브로드캐스트를 모든 포트로 flooding함.

---

## 관련 개념

- [01-02 VLAN / Trunk / Access Port](./01-02-vlan.md) — L2 네트워크 분리
- [01-03 ARP](./01-03-arp.md) — IP→MAC 주소 변환 (L2↔L3 연결)
- [01-04 TCP vs UDP](./01-04-tcp-udp.md) — L4 전송 프로토콜
