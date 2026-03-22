# 01-05 TCP 3-way / 4-way Handshake

## 개념

TCP는 데이터 전송 전 **연결 수립**, 전송 후 **연결 종료** 절차를 거침.
신뢰성 있는 통신을 위해 양측이 서로의 Sequence Number를 교환하고 상태를 동기화.

---

## 동작 원리

### 3-way Handshake — 연결 수립

```
Client                            Server
  │                                  │
  │──── SYN (SEQ=100) ──────────────▶│  "연결할게, 내 초기 SEQ는 100"
  │                                  │
  │◀─── SYN-ACK (SEQ=200, ACK=101) ──│  "OK, 내 SEQ는 200 / 너 101번 줘"
  │                                  │
  │──── ACK (ACK=201) ──────────────▶│  "확인, 너 201번 줄게"
  │                                  │
  │           연결 수립 완료            │
  │         (데이터 전송 가능)          │
```

**각 패킷 역할**

| 패킷 | Flag | 의미 |
|------|------|------|
| 1번 | SYN | 연결 요청. 클라이언트 ISN(Initial Sequence Number) 전달 |
| 2번 | SYN-ACK | 수락 + 서버 ISN 전달 + 클라이언트 SEQ 확인(ACK) |
| 3번 | ACK | 서버 SEQ 확인. 이후 데이터 전송 시작 |

**ISN(Initial Sequence Number)을 랜덤으로 하는 이유**
- 예측 가능한 SEQ는 공격자가 위조 패킷 삽입 가능 (TCP 시퀀스 예측 공격)
- 랜덤 ISN으로 이전 연결의 지연 패킷과 구분

### 4-way Handshake — 연결 종료

연결은 단방향이 아님. 클라이언트→서버, 서버→클라이언트 **각각 독립적으로 종료**.
그래서 FIN이 2번 필요 → 4번 교환.

```
Client                            Server
  │                                  │
  │──── FIN ───────────────────────▶│  "나 보낼 거 다 보냈어, 끊을게"
  │                                  │
  │◀─── ACK ────────────────────────│  "알겠어. 근데 나 아직 보낼 거 있어"
  │                                  │  (서버가 남은 데이터 전송 중...)
  │◀─── FIN ────────────────────────│  "나도 다 보냈어, 끊을게"
  │                                  │
  │──── ACK ───────────────────────▶│  "확인"
  │                                  │
  │       TIME_WAIT (약 2분 대기)      │
  │           연결 완전 종료            │
```

**서버가 ACK 보낸 후 즉시 FIN 안 보내는 이유**
클라이언트 FIN 받았어도 서버가 아직 보내야 할 데이터가 남아있을 수 있음.
이 사이 구간을 **Half-Close** 상태라고 함.

### TIME_WAIT

Client가 마지막 ACK 전송 후 **바로 소켓을 닫지 않고 일정 시간 대기**.

```
기본값: 2 * MSL (Maximum Segment Lifetime) = 보통 2분
```

**이유 1: 마지막 ACK 유실 대비**
```
Client ──ACK──▶ (유실)
Server: ACK 못 받음 → FIN 재전송
Client: TIME_WAIT 중이므로 FIN 다시 받고 ACK 재전송 가능
Client가 이미 소켓 닫았다면 → RST 응답 → 서버 오류
```

**이유 2: 지연 패킷 혼입 방지**
```
이전 연결의 패킷이 네트워크에 떠돌다가
같은 포트로 새 연결이 생기면 섞일 수 있음
TIME_WAIT 동안 같은 포트 재사용 안 함
```

### TCP 상태 머신 요약

```
CLOSED → SYN_SENT → ESTABLISHED → FIN_WAIT_1 → FIN_WAIT_2 → TIME_WAIT → CLOSED
                  (서버 측)
CLOSED → LISTEN → SYN_RECEIVED → ESTABLISHED → CLOSE_WAIT → LAST_ACK → CLOSED
```

---

## 실사용 예시

**스위치 SSH 접속**
```
내 PC(Client) ──SYN──▶ 스위치:22 (Server)
               ◀─SYN-ACK──
              ──ACK──▶
              [3-way 완료 → SSH 프로토콜 협상 시작]
              [명령어 입력/응답]
              ──FIN──▶
              ◀─ACK──
              ◀─FIN──
              ──ACK──▶ [TIME_WAIT]
```

**스위치 관리 웹 (HTTPS)**
```
TCP 3-way handshake
→ TLS handshake (인증서 교환, 암호화 키 협상)
→ HTTP 요청/응답
→ TCP 4-way handshake
```

**SYN Flooding 공격**
```
공격자: SYN만 수백만 개 전송 (ACK 안 보냄)
서버: SYN_RECEIVED 상태로 연결 대기 큐 꽉 참
정상 클라이언트: 연결 못 함 → DoS
대응: SYN Cookie (큐 없이 SEQ에 상태 인코딩)
```

---

## 예시 코드 (Python)

```python
import socket
import threading
import time
from enum import Enum


class TcpState(Enum):
    CLOSED = "CLOSED"
    LISTEN = "LISTEN"
    SYN_SENT = "SYN_SENT"
    SYN_RECEIVED = "SYN_RECEIVED"
    ESTABLISHED = "ESTABLISHED"
    FIN_WAIT_1 = "FIN_WAIT_1"
    FIN_WAIT_2 = "FIN_WAIT_2"
    CLOSE_WAIT = "CLOSE_WAIT"
    LAST_ACK = "LAST_ACK"
    TIME_WAIT = "TIME_WAIT"


class TcpHandshakeSimulator:
    """TCP 3-way / 4-way Handshake 시뮬레이터"""

    def __init__(self, name: str):
        self.name = name
        self.state = TcpState.CLOSED
        self.seq = 0
        self.ack = 0

    def _log(self, msg: str):
        print(f"[{self.name}][{self.state.value}] {msg}")

    # ── 3-way Handshake ──────────────────────────────

    def connect(self, server: "TcpHandshakeSimulator"):
        """Client: 연결 시작"""
        import random
        self.seq = random.randint(100, 999)  # 랜덤 ISN
        self.state = TcpState.SYN_SENT
        self._log(f"SYN 전송 → SEQ={self.seq}")
        server._recv_syn(self.seq, self)

    def _recv_syn(self, client_seq: int, client: "TcpHandshakeSimulator"):
        """Server: SYN 수신"""
        import random
        self.state = TcpState.SYN_RECEIVED
        self.seq = random.randint(100, 999)  # 서버 ISN
        self.ack = client_seq + 1
        self._log(f"SYN 수신. SYN-ACK 전송 → SEQ={self.seq}, ACK={self.ack}")
        client._recv_syn_ack(self.seq, self.ack, self)

    def _recv_syn_ack(self, server_seq: int, server_ack: int, server: "TcpHandshakeSimulator"):
        """Client: SYN-ACK 수신"""
        self.ack = server_seq + 1
        self.state = TcpState.ESTABLISHED
        self._log(f"SYN-ACK 수신. ACK 전송 → ACK={self.ack}")
        server._recv_ack_established()

    def _recv_ack_established(self):
        """Server: ACK 수신 → ESTABLISHED"""
        self.state = TcpState.ESTABLISHED
        self._log("ACK 수신. 연결 수립 완료 ✓")

    # ── 4-way Handshake ──────────────────────────────

    def close(self, peer: "TcpHandshakeSimulator"):
        """Client: 연결 종료 시작"""
        self.state = TcpState.FIN_WAIT_1
        self._log("FIN 전송")
        peer._recv_fin(self)

    def _recv_fin(self, peer: "TcpHandshakeSimulator"):
        """Server: FIN 수신"""
        self.state = TcpState.CLOSE_WAIT
        self._log("FIN 수신. ACK 전송")
        peer._recv_ack_fin_wait()

        # 서버 데이터 전송 완료 후 FIN
        self._log("남은 데이터 전송 완료. FIN 전송")
        self.state = TcpState.LAST_ACK
        peer._recv_fin_from_server(self)

    def _recv_ack_fin_wait(self):
        """Client: ACK 수신 → FIN_WAIT_2"""
        self.state = TcpState.FIN_WAIT_2
        self._log("ACK 수신. 서버 FIN 대기 중...")

    def _recv_fin_from_server(self, server: "TcpHandshakeSimulator"):
        """Client: 서버 FIN 수신 → TIME_WAIT"""
        self.state = TcpState.TIME_WAIT
        self._log("서버 FIN 수신. ACK 전송. TIME_WAIT 진입")
        server._recv_final_ack()

        # TIME_WAIT 후 CLOSED (실제로는 2분, 여기선 즉시)
        self.state = TcpState.CLOSED
        self._log("TIME_WAIT 완료. CLOSED")

    def _recv_final_ack(self):
        """Server: 마지막 ACK 수신"""
        self.state = TcpState.CLOSED
        self._log("최종 ACK 수신. CLOSED ✓")


# 시뮬레이션 실행
print("=== TCP 3-way Handshake ===")
client = TcpHandshakeSimulator("Client")
server = TcpHandshakeSimulator("Server")
server.state = TcpState.LISTEN

client.connect(server)

print("\n=== TCP 4-way Handshake ===")
client.close(server)
```

---

## 면접 예상 질문

- Q: 3-way handshake가 필요한 이유는?
  A: 양측이 서로의 초기 Sequence Number를 교환하고 수신 능력을 확인하기 위해. 2-way로는 서버→클라이언트 방향 수신 능력을 클라이언트가 확인할 수 없음.

- Q: 4-way handshake에서 ACK 후 즉시 FIN 안 보내는 이유는?
  A: 클라이언트 FIN을 받았어도 서버가 아직 보낼 데이터가 남아있을 수 있기 때문. 이 구간을 Half-Close라고 하며, 서버가 전송을 마친 후 별도로 FIN을 전송.

- Q: TIME_WAIT의 목적은?
  A: 두 가지. 첫째, 마지막 ACK 유실 시 서버가 FIN을 재전송하면 받아서 ACK 재전송 가능. 둘째, 이전 연결의 지연 패킷이 같은 포트의 새 연결에 섞이는 것 방지.

- Q: SYN Flooding 공격이란?
  A: 공격자가 SYN만 대량 전송하고 ACK를 보내지 않아 서버의 연결 대기 큐를 꽉 채우는 DoS 공격. 대응으로 SYN Cookie를 사용해 큐 없이 SEQ에 연결 상태를 인코딩.

- Q: ISN을 랜덤으로 설정하는 이유는?
  A: SEQ가 예측 가능하면 공격자가 위조 패킷을 삽입할 수 있음 (TCP Sequence Prediction Attack). 랜덤 ISN으로 예측을 방지하고, 이전 연결의 지연 패킷과 구분.

---

## 관련 개념

- [01-04 TCP vs UDP](./01-04-tcp-udp.md) — TCP 신뢰성 메커니즘 전반
- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — TCP 위에서 동작, TLS handshake 추가
