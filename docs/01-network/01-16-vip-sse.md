# 01-16 VIP / SSE

## 개념

**VIP(Virtual IP)**: 물리 서버가 아닌 서비스에 부여되는 가상 IP. 특정 서버에 종속되지 않아 장애 시 다른 서버로 이전 가능.

**SSE(Server-Sent Events)**: 서버가 클라이언트에게 HTTP를 통해 단방향으로 지속적으로 이벤트를 푸시하는 프로토콜.

---

## VIP — 동작 원리

### VRRP / HSRP (라우터/게이트웨이 HA)

```
VRRP (Virtual Router Redundancy Protocol — 표준):
  Master 라우터: VIP(192.168.1.1) 보유 + VRRP Advertisement 주기적 전송
  Backup 라우터: Advertisement 수신 모니터링

  Master 장애:
    Backup이 Advertisement 못 받음 → Dead Interval 초과
    → Backup이 Master로 승격 → VIP 인수
    → ARP 갱신(Gratuitous ARP)으로 스위치 MAC 테이블 업데이트
    → 트래픽 절체 (통상 3초 이내)

  클라이언트: 게이트웨이 IP = VIP → 물리 장비 교체 몰라도 됨

HSRP (Cisco 독자 규격):
  Active/Standby 개념 (VRRP의 Master/Backup)
  Hello 3초, Dead 10초 (기본값)
  VRRP와 유사하나 표준 아님
```

**VRRP 절체 흐름**:
```
정상:
  Client → VIP(192.168.1.1) → Master(192.168.1.2) → 인터넷
                                    ↑
                     Backup(192.168.1.3) 대기

장애:
  Master 다운 → Backup이 VIP 인수 → Gratuitous ARP 브로드캐스트
  Client: "192.168.1.1의 MAC이 변경됨" → 새 경로로 전송
```

### Keepalived (Linux 서버 HA)

```
서버 레벨 VIP 관리 — VRRP 프로토콜 사용

서버 A (Master):  VIP = 10.0.0.100 보유
서버 B (Backup):  서버 A 모니터링

서버 A 장애 감지:
  B가 VIP 10.0.0.100을 자신의 NIC에 추가
  → Gratuitous ARP 전송
  → 클라이언트/LB는 동일 VIP로 계속 접근

활용:
  Nginx / HAProxy 앞에 Keepalived → Active-Standby 구성
  DB(MySQL/Redis) HA → VIP로 Primary 추상화
```

### 로드밸런서의 VIP

```
L4/L7 LB의 Virtual Server IP:
  Client → VIP:443 → LB → Real Server 1, 2, 3 분산

  클라이언트는 VIP만 알면 됨 (Real Server 변경/추가 투명)
  DNS에는 VIP 등록

Anycast VIP (CDN / DNS):
  동일 IP를 여러 지역 서버가 공유
  BGP 라우팅으로 가장 가까운 서버로 자동 연결
```

---

## SSE — 동작 원리

### HTTP 기반 단방향 스트리밍

```
일반 HTTP:         Client →요청→ Server →응답→ (연결 종료)
WebSocket:         Client ←→ Server (양방향 지속 연결)
SSE:               Client →요청→ Server →이벤트... 이벤트...→ (서버 주도 단방향)

SSE 연결:
  GET /events HTTP/1.1
  Accept: text/event-stream

SSE 응답 헤더:
  Content-Type: text/event-stream
  Cache-Control: no-cache
  Connection: keep-alive

SSE 이벤트 형식:
  data: {"status": "up", "port": "Gi0/1"}\n
  \n
  id: 42\n
  event: port-down\n
  data: {"device": "sw-core-01", "port": "Gi0/2"}\n
  \n

  필드:
    data:   이벤트 데이터 (여러 줄 가능)
    id:     Last-Event-ID — 재연결 시 이어받기
    event:  이벤트 타입 (기본값 "message")
    retry:  재연결 대기 시간(ms)
```

### SSE vs WebSocket

| 항목 | SSE | WebSocket |
|------|-----|-----------|
| 방향 | 서버→클라이언트 단방향 | 양방향 |
| 프로토콜 | HTTP/1.1, HTTP/2 | ws:// (별도 프로토콜) |
| 재연결 | 자동 (브라우저 내장) | 직접 구현 필요 |
| 프록시/방화벽 | HTTP 그대로 통과 | 일부 차단 |
| 멀티플렉싱 | HTTP/2로 1개 연결에 다중 스트림 | 커넥션당 1개 |
| 용도 | 알림, 로그 스트리밍, 주식 시세 | 채팅, 게임, 공동 편집 |

### 재연결 메커니즘

```
브라우저(EventSource) 자동 재연결:
  연결 끊김 → 3초 후(retry 값) 자동 재시도
  재연결 시 Last-Event-ID 헤더 전송
  → 서버가 놓친 이벤트부터 재전송 가능

Last-Event-ID 활용:
  서버: 각 이벤트에 id: <sequence> 부여
  클라이언트 재연결 요청:
    GET /events
    Last-Event-ID: 41
  서버: id 42부터 밀린 이벤트 재전송
```

---

## 예시 코드 (Python)

```python
import socket
import struct
import time
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable


# ── VRRP Gratuitous ARP 시뮬레이션 ───────────────────

class VRRPSimulator:
    """
    VRRP Master/Backup 절체 시뮬레이션
    실제 VRRP는 멀티캐스트(224.0.0.18) 사용
    """

    def __init__(self, vip: str, master_ip: str, backup_ip: str):
        self.vip       = vip
        self.master_ip = master_ip
        self.backup_ip = backup_ip
        self.state     = "Master"    # Master | Backup
        self.priority  = 100         # Master: 100, Backup: 90
        self._running  = True
        self._advert_interval = 1    # Advertisement 주기(초)
        self._dead_interval   = 3    # Dead 판단 기준(초)
        self._last_advert     = time.time()

    def master_loop(self):
        """Master: Advertisement 전송 시뮬레이션"""
        print(f"  [Master {self.master_ip}] VIP={self.vip} 보유, Advertisement 전송 중")
        for tick in range(5):
            time.sleep(self._advert_interval)
            print(f"  [Master] Advertisement #{tick+1} 전송 (priority={self.priority})")
        print(f"  [Master] 장애 발생! Advertisement 중단")

    def backup_loop(self, on_failover: Callable):
        """Backup: Advertisement 모니터링, 미수신 시 절체"""
        print(f"  [Backup {self.backup_ip}] 대기 중 (priority=90)")
        last_seen = time.time()

        while self._running:
            time.sleep(0.5)
            elapsed = time.time() - last_seen

            if elapsed >= self._dead_interval:
                self.state = "Master"
                print(f"\n  [Backup→Master] Dead Interval {elapsed:.1f}초 초과!")
                print(f"  [Backup→Master] VIP {self.vip} 인수")
                print(f"  [Backup→Master] Gratuitous ARP 전송")
                print(f"    ARP: {self.vip} is at <Backup MAC> (브로드캐스트)")
                on_failover(self.vip, self.backup_ip)
                self._running = False
                return

            # 실제로는 멀티캐스트 Advertisement 수신 체크
            # 여기서는 master_loop 실행 중인 5초 동안만 "수신" 시뮬레이션
            if elapsed < 5:
                last_seen = time.time()

    def simulate(self):
        results = []

        def on_failover(vip, new_master):
            results.append({
                "event": "failover",
                "vip": vip,
                "new_master": new_master,
                "time": time.strftime("%H:%M:%S")
            })

        t_master = threading.Thread(target=self.master_loop)
        t_backup = threading.Thread(target=self.backup_loop, args=(on_failover,))

        t_master.start()
        t_backup.start()
        t_master.join()
        self._running = False   # backup loop 종료 트리거
        t_backup.join(timeout=5)

        return results


# ── SSE 서버 구현 ─────────────────────────────────────

class SSEHandler(BaseHTTPRequestHandler):
    """
    SSE 서버: 네트워크 장비 상태 변경 이벤트 스트리밍
    GET /events → text/event-stream
    """
    # 클래스 레벨 이벤트 큐 (전체 클라이언트 공유)
    _clients: list = []
    _clients_lock = threading.Lock()
    _event_id = 0

    def log_message(self, format, *args):
        pass  # 로그 억제

    def do_GET(self):
        if self.path == "/events":
            self._handle_sse()
        elif self.path == "/send":
            self._handle_send()
        else:
            self.send_error(404)

    def _handle_sse(self):
        """SSE 연결 처리"""
        last_event_id = self.headers.get("Last-Event-ID", "0")

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # 초기 연결 확인 이벤트
        self._send_event(
            data=json.dumps({"type": "connected", "last_id": last_event_id}),
            event="connect"
        )

        # 클라이언트 등록
        queue = []
        with SSEHandler._clients_lock:
            SSEHandler._clients.append(queue)

        try:
            while True:
                if queue:
                    event_data = queue.pop(0)
                    self._send_event(**event_data)
                else:
                    # Heartbeat (연결 유지)
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with SSEHandler._clients_lock:
                SSEHandler._clients.remove(queue)

    def _send_event(self, data: str, event: str = "message",
                    event_id: int = None):
        """SSE 이벤트 형식으로 전송"""
        SSEHandler._event_id += 1
        eid = event_id or SSEHandler._event_id

        msg = (f"id: {eid}\n"
               f"event: {event}\n"
               f"data: {data}\n\n")
        self.wfile.write(msg.encode())
        self.wfile.flush()

    def _handle_send(self):
        """이벤트 발행 엔드포인트 (테스트용)"""
        self.send_response(200)
        self.end_headers()


def broadcast_event(event_type: str, data: dict):
    """모든 SSE 클라이언트에게 이벤트 브로드캐스트"""
    SSEHandler._event_id += 1
    event = {
        "data": json.dumps(data),
        "event": event_type,
        "event_id": SSEHandler._event_id
    }
    with SSEHandler._clients_lock:
        for client_queue in SSEHandler._clients:
            client_queue.append(event)


# ── SSE 클라이언트 (Python) ───────────────────────────

class SSEClient:
    """SSE 스트림을 구독하는 클라이언트"""

    def __init__(self, host: str, port: int, path: str = "/events"):
        self.host = host
        self.port = port
        self.path = path
        self.last_event_id = None
        self.events_received = []

    def connect(self, timeout: float = 3.0):
        """SSE 연결 및 이벤트 수신"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)

        try:
            sock.connect((self.host, self.port))

            # HTTP 요청
            headers = [
                f"GET {self.path} HTTP/1.1",
                f"Host: {self.host}:{self.port}",
                "Accept: text/event-stream",
                "Cache-Control: no-cache",
            ]
            if self.last_event_id:
                headers.append(f"Last-Event-ID: {self.last_event_id}")
            headers.append("\r\n")
            sock.send("\r\n".join(headers).encode())

            # 응답 파싱
            buffer = ""
            current_event = {}

            while True:
                try:
                    data = sock.recv(4096).decode("utf-8", errors="ignore")
                    if not data:
                        break
                    buffer += data

                    while "\n\n" in buffer:
                        chunk, buffer = buffer.split("\n\n", 1)
                        event = self._parse_event(chunk)
                        if event:
                            self.events_received.append(event)
                            if "id" in event:
                                self.last_event_id = event["id"]
                except socket.timeout:
                    break
        finally:
            sock.close()

    def _parse_event(self, raw: str) -> dict:
        """SSE 이벤트 파싱"""
        if raw.startswith(":") or "HTTP/" in raw:
            return None   # heartbeat 또는 HTTP 헤더
        event = {}
        for line in raw.strip().splitlines():
            if ":" in line:
                field, _, value = line.partition(":")
                event[field.strip()] = value.strip()
        return event if event else None


# ── 실행 ─────────────────────────────────────────────

print("=== VRRP 절체 시뮬레이션 ===")
vrrp = VRRPSimulator(
    vip="192.168.1.1",
    master_ip="192.168.1.2",
    backup_ip="192.168.1.3"
)
results = vrrp.simulate()
print(f"\n  절체 결과:")
for r in results:
    print(f"    {r}")
print(f"  클라이언트 영향: VIP {vrrp.vip} 동일 사용, 절체 투명")


print("\n=== SSE 서버/클라이언트 ===")

# 서버 시작
server = HTTPServer(("127.0.0.1", 0), SSEHandler)
port = server.server_address[1]
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
print(f"  SSE 서버 시작: port={port}")

# 클라이언트 연결 (백그라운드)
client = SSEClient("127.0.0.1", port)
client_thread = threading.Thread(target=client.connect, args=(2.0,), daemon=True)
client_thread.start()
time.sleep(0.1)

# 이벤트 발행 (네트워크 이벤트 시뮬레이션)
events = [
    ("port-status", {"device": "sw-core-01", "port": "Gi0/1", "status": "down"}),
    ("trap",        {"device": "sw-dist-01", "type": "cpu-high", "value": 92}),
    ("port-status", {"device": "sw-core-01", "port": "Gi0/1", "status": "up"}),
]
for event_type, data in events:
    broadcast_event(event_type, data)
    time.sleep(0.1)

client_thread.join(timeout=3)
server.shutdown()

print(f"  클라이언트 수신 이벤트 ({len(client.events_received)}개):")
for evt in client.events_received:
    if "data" in evt and "{" in evt.get("data", ""):
        d = json.loads(evt["data"])
        print(f"    [{evt.get('event','message')}] {d}")
```

---

## 면접 예상 질문

- Q: VIP(Virtual IP)가 필요한 이유는?
  A: 서비스 IP를 특정 물리 장비에서 분리. 장비 장애 시 VIP를 다른 장비로 이전(Failover)해 클라이언트는 IP 변경 없이 계속 접근 가능. VRRP/HSRP: 게이트웨이/라우터 HA. Keepalived: 서버 레벨 HA. LB의 Virtual Server IP: 백엔드 변경을 클라이언트에게 투명하게 처리.

- Q: VRRP 절체 과정을 설명하라.
  A: ① Master가 주기적으로 Advertisement 멀티캐스트 전송. ② Backup이 Dead Interval(Master가 설정) 내에 Advertisement를 못 받으면 Master 장애로 판단. ③ Backup이 Master로 승격, VIP를 자신의 NIC에 할당. ④ Gratuitous ARP 브로드캐스트 — 스위치 MAC 테이블과 클라이언트 ARP 캐시 갱신. ⑤ 트래픽이 새 Master로 절체 (통상 3초 이내).

- Q: SSE와 WebSocket의 차이는? 언제 SSE를 선택하나?
  A: SSE는 서버→클라이언트 단방향 HTTP 스트리밍. 재연결 자동, HTTP/2로 멀티플렉싱, 프록시/방화벽 통과 쉬움. WebSocket은 양방향이지만 별도 프로토콜(ws://)로 일부 방화벽에서 차단될 수 있음. 서버 푸시만 필요한 경우(알림, 로그 스트리밍, 모니터링 대시보드)는 SSE가 단순하고 안정적. 채팅, 게임처럼 클라이언트→서버 전송도 빈번하면 WebSocket.

- Q: SSE의 Last-Event-ID는 어떻게 사용되나?
  A: 서버가 각 이벤트에 id: 값을 부여. 브라우저(EventSource)가 이 ID를 기억. 연결 끊김 후 재연결 시 Last-Event-ID 헤더로 마지막 수신 ID 전송. 서버가 그 ID 이후 이벤트를 재전송 → 이벤트 유실 없이 이어받기 가능. 실무에서는 Redis나 DB에 이벤트 로그 보관 필요.

---

## 관련 개념

- [01-11 웹소켓 vs HTTP](./01-11-websocket.md) — SSE vs WebSocket 상세 비교
- [01-13 로드 밸런싱](./01-13-load-balancing.md) — LB의 Virtual Server IP
- [01-03 ARP](./01-03-arp.md) — Gratuitous ARP (VRRP 절체 핵심)
- [01-04 TCP vs UDP](./01-04-tcp-udp.md) — VRRP는 IP 프로토콜 112
