# 01-04 TCP vs UDP

## 개념

둘 다 L4 Transport 계층 프로토콜. **포트 번호**로 프로세스를 식별해 데이터를 전달.

| 구분 | TCP | UDP |
|------|-----|-----|
| 연결 방식 | 연결 지향 (3-way handshake) | 비연결 |
| 신뢰성 | 보장 (재전송, 순서 보장) | 없음 |
| 속도 | 상대적으로 느림 | 빠름 |
| 헤더 크기 | 20byte+ | 8byte |
| 흐름/혼잡 제어 | 있음 | 없음 |
| 용도 | 정확성이 중요한 통신 | 속도가 중요한 통신 |

---

## 동작 원리

### TCP — 신뢰성 보장 메커니즘

**① Sequence Number / ACK**
```
송신: [SEQ=1 | data_A] →
수신:                   ← [ACK=2]  "1번 받았어, 2번 줘"
송신: [SEQ=2 | data_B] →
수신:                   ← [ACK=3]
```

**② 손실 시 재전송**
```
송신: [SEQ=2 | data_B] →
수신: (패킷 손실)
송신: 타임아웃 → [SEQ=2 | data_B] 재전송
```

**③ 흐름 제어 (Flow Control)**
수신 측 버퍼 크기를 Window Size로 알려줌. 송신 측은 그 이상 보내지 않음.
```
수신: [ACK | Window=4096]  → "지금 4096byte까지 받을 수 있어"
```

**④ 혼잡 제어 (Congestion Control)**
네트워크 혼잡 감지 시 전송 속도 줄임 (Slow Start, AIMD).

### UDP — 단순 전달

연결 수립 없이 바로 전송. 수신 확인 없음. 손실되면 그냥 없어짐.
상위 계층(애플리케이션)에서 필요하면 자체 재시도 로직 구현.

### TCP 헤더 vs UDP 헤더

```
TCP 헤더 (최소 20byte)
[ Src Port(2) | Dst Port(2) | Seq(4) | Ack(4) | Flags(2) | Window(2) | Checksum(2) | Urgent(2) ]
  Flags: SYN, ACK, FIN, RST, PSH, URG

UDP 헤더 (고정 8byte)
[ Src Port(2) | Dst Port(2) | Length(2) | Checksum(2) ]
```

---

## 용도 비교

| 프로토콜 | TCP/UDP | 이유 |
|---------|---------|------|
| SSH(22), HTTPS(443) | TCP | 데이터 손실 불가 |
| HTTP(80) | TCP | 정확한 응답 필요 |
| DNS(53) | UDP | 짧은 쿼리, 안되면 재시도 |
| SNMP(161) | UDP | 단방향 빠른 폴링/트랩 |
| Syslog(514) | UDP | 단방향 이벤트 전송 |
| DHCP(67/68) | UDP | IP 없는 상태에서 연결 불가 |
| 영상 스트리밍 | UDP | 끊김보다 지연이 더 나쁨 |
| QUIC (HTTP/3) | UDP | UDP 위에 자체 신뢰성 구현 |
| TFTP | UDP | 단순 파일 전송, 빠름 |

**스위치/AP 연동 관점**
- 스위치 SSH 접속 → TCP: 명령어 손실 없어야 함
- SNMP Trap → UDP: 빠른 이벤트 알림, 일부 손실 허용
- 스위치 펌웨어 TFTP 업로드 → UDP: 단순하고 빠름
- Syslog 전송 → UDP: 대량 로그, 일부 손실보다 속도 우선

---

## 예시 코드 (Python)

```python
import socket
import threading

# TCP 서버/클라이언트 (스위치 관리 API 예시)
def tcp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 9000))
        s.listen(1)
        print("[TCP Server] 대기 중...")
        conn, addr = s.accept()
        with conn:
            print(f"[TCP Server] 연결됨: {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"[TCP Server] 수신: {data.decode()}")
                conn.sendall(b"ACK: " + data)  # 응답 보장


def tcp_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 9000))  # 3-way handshake 발생
        s.sendall(b"GET /api/switch/status")
        data = s.recv(1024)
        print(f"[TCP Client] 응답: {data.decode()}")


# UDP 서버/클라이언트 (SNMP Trap 수신 예시)
def udp_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(("127.0.0.1", 9001))
        print("[UDP Server] SNMP Trap 대기 중...")
        while True:
            data, addr = s.recvfrom(1024)
            print(f"[UDP Server] Trap 수신 from {addr}: {data.decode()}")
            # ACK 없음 — 그냥 받기만 함


def udp_client():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # 연결 수립 없이 바로 전송
        s.sendto(b"TRAP: linkDown port=3", ("127.0.0.1", 9001))
        s.sendto(b"TRAP: cpuHigh threshold=90%", ("127.0.0.1", 9001))
        print("[UDP Client] Trap 전송 완료 (응답 확인 안 함)")


# TCP vs UDP 신뢰성 직접 비교
class ReliabilityDemo:
    """TCP 재전송 메커니즘 시뮬레이션"""

    def __init__(self):
        self.sent = {}      # seq -> data
        self.acked = set()  # 수신 확인된 seq

    def send(self, seq: int, data: str, drop: bool = False):
        self.sent[seq] = data
        if drop:
            print(f"[TCP] SEQ={seq} 전송 → 손실!")
        else:
            print(f"[TCP] SEQ={seq} 전송 → 수신 성공")
            self.receive_ack(seq + 1)

    def receive_ack(self, ack: int):
        expected_seq = ack - 1
        self.acked.add(expected_seq)
        print(f"[TCP] ACK={ack} 수신 (SEQ={expected_seq} 확인됨)")

    def retransmit_if_needed(self, seq: int):
        if seq not in self.acked:
            print(f"[TCP] SEQ={seq} 타임아웃 → 재전송")
            self.send(seq, self.sent[seq])


demo = ReliabilityDemo()
demo.send(1, "data_A")
demo.send(2, "data_B", drop=True)   # 손실 시뮬레이션
demo.retransmit_if_needed(2)        # 재전송
```

---

## 면접 예상 질문

- Q: TCP와 UDP의 핵심 차이는?
  A: TCP는 연결 지향으로 3-way handshake 후 통신. 순서 보장, 손실 시 재전송, 흐름/혼잡 제어로 신뢰성 보장. UDP는 비연결로 바로 전송. 오버헤드 없어 빠르지만 신뢰성 없음.

- Q: UDP를 쓰는 이유가 있나? TCP가 더 안전하지 않나?
  A: 속도와 오버헤드가 중요할 때 UDP를 사용. DNS처럼 짧은 요청은 핸드셰이크 비용이 더 큼. 스트리밍은 재전송으로 생기는 지연이 손실보다 나쁨. SNMP Trap, Syslog처럼 일부 손실을 허용하는 단방향 알림에도 UDP가 적합.

- Q: QUIC이란?
  A: Google이 개발한 UDP 기반 전송 프로토콜. HTTP/3의 기반. UDP 위에서 자체적으로 연결 관리, 재전송, 암호화(TLS 1.3 내장)를 구현해 TCP의 신뢰성 + UDP의 속도를 결합. 핸드셰이크 횟수를 줄여 연결 지연 감소.

- Q: TCP 흐름 제어와 혼잡 제어의 차이는?
  A: 흐름 제어는 수신 측 버퍼 오버플로우 방지 (Window Size로 수신 가능 크기 통보). 혼잡 제어는 네트워크 자체의 과부하 방지 (패킷 손실 감지 시 전송 속도 감소).

- Q: SNMP가 UDP를 쓰는 이유는?
  A: SNMP Trap은 단방향 이벤트 알림으로 빠른 전달이 우선. 일부 Trap 손실은 허용 가능. TCP의 연결 수립/유지 오버헤드가 불필요. SNMP Get/Set은 요청-응답 구조지만 짧은 패킷이라 UDP로 충분하며 애플리케이션 레벨에서 타임아웃 재시도 처리.

---

## 관련 개념

- [01-05 TCP 3-way / 4-way Handshake](./01-05-tcp-handshake.md) — TCP 연결 수립/종료 상세
- [01-06 DNS](./01-06-dns.md) — UDP 기반 대표 프로토콜
- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — TCP 위에서 동작
