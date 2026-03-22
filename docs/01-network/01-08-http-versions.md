# 01-08 HTTP/1.1 vs HTTP/2 vs HTTP/3

## 개념

HTTP가 버전업 되면서 **성능 문제**를 하나씩 해결해온 역사.

| 버전 | 연도 | 기반 | 핵심 개선 |
|------|------|------|----------|
| HTTP/1.0 | 1996 | TCP | 요청마다 TCP 연결 새로 맺음 |
| HTTP/1.1 | 1997 | TCP | Keep-Alive, 파이프라이닝 |
| HTTP/2 | 2015 | TCP | 멀티플렉싱, 헤더 압축, 서버 푸시 |
| HTTP/3 | 2022 | UDP(QUIC) | TCP 자체를 UDP+QUIC으로 교체 |

---

## 동작 원리

### HTTP/1.1 — Keep-Alive와 HOL Blocking

**Keep-Alive**: 요청마다 TCP 연결을 새로 맺지 않고 하나의 연결 재사용.

```
HTTP/1.0 (비효율):
TCP 연결 → 요청1 → 응답1 → TCP 종료
TCP 연결 → 요청2 → 응답2 → TCP 종료  ← 매번 3-way handshake

HTTP/1.1 Keep-Alive:
TCP 연결 → 요청1 → 응답1 → 요청2 → 응답2 → 요청3 → 응답3 → TCP 종료
           ↑ 하나의 연결로 여러 요청 처리
```

**HOL Blocking (Head-Of-Line Blocking) 문제**

파이프라이닝(요청을 연속으로 보내기)을 지원하지만, 앞 요청의 응답이 오기 전에는 뒤 응답을 처리 못 함.

```
요청: [img1] [img2] [img3] 연속 전송

응답: [img1(느림)........] [img2] [img3]
                           ↑ img1 완료될 때까지 img2, img3 대기
```

브라우저가 이를 우회하려고 **도메인당 TCP 연결 6개**를 병렬로 맺음 → 리소스 낭비.

---

### HTTP/2 — 멀티플렉싱과 TLS

**HTTP/2는 실질적으로 TLS 위에서만 동작한다.**

```
스펙상으로는 HTTP/2를 평문(h2c)으로도 허용하지만,
Chrome, Firefox, Safari 등 모든 브라우저는 TLS 위에서만 HTTP/2 사용.
→ HTTP/2 = HTTPS라고 봐도 무방.

왜 TLS와 함께 쓰는가:
  TLS Handshake의 ALPN(Application-Layer Protocol Negotiation) 확장을 통해
  어떤 프로토콜을 쓸지 협상:

  ClientHello → ALPN extension: ["h2", "http/1.1"]
  ServerHello → ALPN: "h2" 선택
  → TLS 연결 완료와 동시에 HTTP/2 사용 합의
  → 별도 업그레이드 왕복 없이 바로 HTTP/2 시작
```

**하나의 TLS 연결 안에서 여러 요청/응답을 동시에 처리.**

```
HTTP/1.1 (TLS × 3개 연결):
  TLS연결1: [TLS 핸드셰이크] → 요청A → 응답A
  TLS연결2: [TLS 핸드셰이크] → 요청B → 응답B
  TLS연결3: [TLS 핸드셰이크] → 요청C → 응답C
  → TLS 핸드셰이크 비용 × 3배

HTTP/2 (TLS 1개 연결, 스트림으로 분리):
  [TLS 핸드셰이크 1회]
          스트림1: [요청A] ──── [응답A]
  연결1 ── 스트림2: [요청B] ──── [응답B]  ← 동시 처리
          스트림3: [요청C] ──── [응답C]
  → TLS 세션 재사용, 핸드셰이크 비용 1회로 절감
```

**프레임과 스트림 구조**

```
HTTP/2 데이터 단위: 프레임(Frame)

┌─────────┬──────┬──────────────┬──────────────────────┐
│ Length  │ Type │  Flags       │ Stream ID            │
│ (24bit) │(8bit)│  (8bit)      │ (31bit)              │
├─────────┴──────┴──────────────┴──────────────────────┤
│ Payload (가변 길이)                                    │
└───────────────────────────────────────────────────────┘

프레임 타입:
  DATA    : 실제 HTTP Body
  HEADERS : HTTP 헤더 (HPACK 압축)
  SETTINGS: 연결 설정 (최대 스트림 수 등)
  WINDOW_UPDATE: 흐름 제어
  PING    : 연결 유지 확인
  RST_STREAM: 스트림 즉시 종료

스트림 ID:
  클라이언트 요청: 홀수 (1, 3, 5...)
  서버 푸시:      짝수 (2, 4, 6...)
  스트림 0:       연결 전체 제어 메시지
```

**멀티플렉싱이 가능한 이유 — Nginx로 이해하기**

HTTP/1.1도 Keep-Alive로 연결을 재사용하는데, 왜 멀티플렉싱이 안 됐나?

```
HTTP/1.1의 근본 문제: 요청-응답이 텍스트 스트림 위에서 순서대로 흘러감

클라이언트 → 서버:
  "GET /style.css HTTP/1.1\r\nHost: ...\r\n\r\n"  ← 요청1 끝
  "GET /script.js HTTP/1.1\r\nHost: ...\r\n\r\n"  ← 요청2 끝

서버는 어디서 요청1이 끝나고 요청2가 시작되는지 알지만,
응답은 반드시 순서대로 보내야 함:
  응답1 완전히 끝 → 응답2 시작
  응답 중간에 다른 응답 데이터를 끼워 넣을 방법이 없음
  (텍스트 스트림에서 어디까지가 응답1인지 구분 불가)
```

HTTP/2는 **바이너리 프레임 + Stream ID** 로 이 문제를 해결:

```
프레임마다 Stream ID가 있으므로 인터리빙(끼워넣기)이 가능:

TCP 소켓으로 흘러가는 바이트열:
  [Stream1 HEADERS] [Stream3 HEADERS] [Stream1 DATA(1/3)]
  [Stream5 HEADERS] [Stream3 DATA(1/2)] [Stream1 DATA(2/3)]
  [Stream3 DATA(2/2)] [Stream1 DATA(3/3)] [Stream5 DATA]

수신 측에서 Stream ID로 조립:
  Stream1 → HEADERS + DATA 1/3 + DATA 2/3 + DATA 3/3 → 응답A 완성
  Stream3 → HEADERS + DATA 1/2 + DATA 2/2           → 응답B 완성
  Stream5 → HEADERS + DATA                           → 응답C 완성

핵심: 큰 응답(DATA)을 잘게 쪼개서 다른 스트림의 작은 응답과 교차 전송.
      응답A가 느려도 응답B, C의 프레임이 그 사이에 전송될 수 있음.
```

**Nginx가 HTTP/2 멀티플렉싱을 처리하는 방법**

```
# nginx.conf — HTTP/2 활성화
server {
    listen 443 ssl;
    http2  on;           # Nginx 1.25.1+ (이전: listen 443 ssl http2)

    ssl_certificate     /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;

    # TLS 세션 캐시: 클라이언트 재접속 시 핸드셰이크 생략
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # HTTP/2 튜닝
    http2_max_concurrent_streams 128;  # 하나의 연결당 최대 동시 스트림
    http2_recv_buffer_size       256k;
    keepalive_timeout            65;

    location / {
        proxy_pass http://backend;
    }
}
```

Nginx 내부에서 일어나는 일:

```
[클라이언트]              [Nginx worker 프로세스]         [백엔드]
     │                          │                            │
     │── TLS + h2 연결 ────────▶│                            │
     │                          │  단일 소켓 fd               │
     │── Stream1 HEADERS ──────▶│                            │
     │── Stream3 HEADERS ──────▶│  프레임 수신 즉시 처리        │
     │── Stream5 HEADERS ──────▶│  (이벤트 루프)              │
     │                          │                            │
     │                          │── HTTP/1.1 요청 ──────────▶│  (upstream은 대부분 HTTP/1.1)
     │                          │── HTTP/1.1 요청 ──────────▶│
     │                          │── HTTP/1.1 요청 ──────────▶│
     │                          │                            │
     │                          │◀── 응답 ───────────────────│
     │◀── Stream5 DATA ─────────│  완료된 스트림부터 즉시 전송
     │◀── Stream1 DATA(1/2)─────│  (느린 Stream3 기다리지 않음)
     │◀── Stream3 DATA ─────────│
     │◀── Stream1 DATA(2/2)─────│
```

왜 Nginx 워커 하나가 수천 개 연결을 처리할 수 있나:

```
Nginx 아키텍처: 비동기 이벤트 기반 (epoll/kqueue)

전통적 Thread-per-Connection:
  연결 1000개 → 스레드 1000개 → 메모리/컨텍스트 스위치 폭발

Nginx 이벤트 루프:
  while True:
      events = epoll_wait(fd_list)  ← 데이터 있는 소켓만 알림
      for event in events:
          if event.type == READABLE:
              read_http2_frame()        ← Stream ID 파싱
              dispatch_to_stream()      ← 해당 스트림 처리
          if event.type == WRITABLE:
              send_pending_frames()     ← 버퍼에 있는 프레임 전송

  → 하나의 스레드가 소켓 수만 개를 논블로킹으로 처리
  → HTTP/2: 연결 1개당 128개 스트림 → 사실상 클라이언트당 단일 연결로 충분

HTTP/1.1 연결 6개 vs HTTP/2 연결 1개 (128 스트림):
  HTTP/1.1: Nginx 6개 fd, TLS 세션 6개, 메모리 6배
  HTTP/2:   Nginx 1개 fd, TLS 세션 1개, 스트림은 메모리 경량
```

클라이언트-Nginx는 HTTP/2, Nginx-백엔드는 HTTP/1.1인 이유:

```
[브라우저] ─── HTTP/2 ──▶ [Nginx] ─── HTTP/1.1 ──▶ [Django/Flask/Node]

백엔드로 HTTP/2를 쓰지 않는 이유:
  - 내부망(loopback, VPC)은 패킷 손실이 거의 없어 HTTP/2 이점 적음
  - 대부분의 백엔드 프레임워크가 HTTP/1.1 기반
  - Nginx upstream HTTP/2 지원은 비교적 최근 (1.19.1+, 실험적)

proxy_http_version 1.1;          # upstream은 HTTP/1.1
proxy_set_header Connection "";  # upstream keepalive 재사용
keepalive 32;                    # upstream 연결 풀
```

**한 줄 요약: 스레드 → 소켓 → 병렬 처리 관계**

```
Q: 무조건 단일 스레드야?

A: Nginx 워커 프로세스 하나 = 스레드 1개 (기본).
   단, 워커 프로세스는 CPU 코어 수만큼 띄운다.

  [워커1: 코어0]  ─── 소켓 N개 (epoll로 단일 스레드가 담당)
  [워커2: 코어1]  ─── 소켓 N개
  [워커3: 코어2]  ─── 소켓 N개
  [워커4: 코어3]  ─── 소켓 N개

  → "멀티 스레드"가 아니라 "멀티 프로세스 × 단일 스레드 이벤트 루프"

  worker_processes auto;          # CPU 코어 수만큼
  worker_connections 1024;        # 워커 1개당 최대 소켓 수


Q: 스레드 하나가 처리할 수 있는 이벤트(소켓) 개수는?

A: 이론상 제한 없음. 실제 제한은 OS 설정과 메모리.

  제한 요소:
    worker_connections 1024   ← Nginx 설정 (기본값, 올릴 수 있음)
    ulimit -n 65535           ← OS의 프로세스당 최대 fd(파일 디스크립터) 수
    epoll 자체:               ← Linux epoll은 수십만 fd 지원

  실무 예시 (4코어):
    worker_processes 4;
    worker_connections 10000;
    → 최대 동시 소켓 = 4 × 10000 = 40,000개
    → HTTP/2면 소켓 1개당 스트림 128개
    → 이론상 동시 처리 = 40,000 × 128 = 512만 스트림


Q: 그럼 스레드 1개가 소켓 10,000개를 어떻게 "동시에" 처리해?

A: 진짜 동시는 아님. epoll이 "지금 데이터 있는 소켓"만 알려줌.

  비유:
    식당 직원 1명이 테이블 100개 담당
    → 모든 테이블을 1초마다 순회하지 않음 (Polling 방식 — 비효율)
    → 손님이 손 들 때만 달려감 (epoll 방식 — 효율)

  실제 동작:
    epoll_wait() 호출 → 커널이 데이터 도착한 fd 목록만 반환
    → 스레드는 해당 fd만 처리 → 다시 epoll_wait()

  CPU를 쓰는 건 "데이터가 실제로 있을 때"뿐.
  나머지 시간: epoll_wait() 안에서 대기 (CPU 0%)

  핵심 전제: 각 소켓 처리가 빨리 끝나야 함.
    빠름 (논블로킹): 프레임 읽기, 버퍼에 쓰기, 라우팅 결정 → OK
    느림 (블로킹):   DB 쿼리, 파일 읽기 → 스레드 점유 → 다른 소켓 못 처리
    → Nginx가 백엔드 I/O를 비동기로 처리하는 이유


Q: HTTP/1.1 대비 HTTP/2에서 스레드 부담이 왜 줄어드나?

  HTTP/1.1 브라우저: TCP 연결 6개 → fd 6개, TLS 세션 6개
  HTTP/2 브라우저:  TCP 연결 1개 → fd 1개, TLS 세션 1개, 스트림 최대 128개

  클라이언트 1,000명 기준:
    HTTP/1.1: fd 6,000개, TLS 세션 6,000개
    HTTP/2:   fd 1,000개, TLS 세션 1,000개
    → 메모리·컨텍스트 스위치 대폭 감소
```

**주요 개선사항**

| 기능 | 설명 |
|------|------|
| 멀티플렉싱 | 하나의 TLS 연결에서 여러 스트림 동시 처리 |
| 헤더 압축 (HPACK) | 반복되는 헤더 압축 (Cookie, User-Agent 등) — 최대 85~88% 압축 |
| 서버 푸시 | 클라이언트 요청 전에 서버가 미리 리소스 전송 |
| 바이너리 프레임 | 텍스트 → 바이너리로 파싱 효율 향상 |
| 흐름 제어 | 스트림/연결 단위로 수신 윈도우 크기 조절 |
| 스트림 우선순위 | 중요한 리소스(CSS)를 먼저 처리 지정 가능 |

**HTTP/2의 한계 — TCP 레벨 HOL Blocking**

멀티플렉싱으로 애플리케이션 레벨 HOL은 해결했지만, TCP 자체의 문제는 남아있음.

```
TCP 패킷 하나 손실 시:
손실된 패킷 재전송 완료될 때까지 → 모든 스트림 대기
(TCP는 순서를 보장해야 하므로)

스트림1 데이터 ──────▶ (손실) ──────▶ 재전송 대기...
스트림2 데이터 ─────────────────────▶ (대기 중)
스트림3 데이터 ─────────────────────▶ (대기 중)
```

---

### HTTP/3 — QUIC (UDP 기반)과 TLS 통합

**TCP를 버리고 UDP 위에 QUIC 프로토콜을 새로 구현. TLS 1.3이 QUIC 내부에 통합.**

```
HTTP/1.1, HTTP/2: [HTTP] → [TLS] → [TCP] → [IP]
HTTP/3:           [HTTP/3] → [QUIC (TLS 1.3 내장)] → [UDP] → [IP]
```

**QUIC + TLS 1.3 통합의 의미**

```
HTTP/2 + TLS 1.2:
  TCP 핸드셰이크 (1RTT) + TLS 핸드셰이크 (2RTT) = 총 3RTT

HTTP/2 + TLS 1.3:
  TCP 핸드셰이크 (1RTT) + TLS 핸드셰이크 (1RTT) = 총 2RTT

HTTP/3 (QUIC + TLS 1.3 통합):
  QUIC 초기 패킷에 TLS ClientHello 포함 = 1RTT로 전체 완료
  재접속(이전 세션 있으면) = 0-RTT

왜 가능한가:
  QUIC은 연결 수립과 TLS 협상을 하나의 패킷으로 묶음.
  TLS 1.3의 Handshake 메시지를 QUIC Initial/Handshake 패킷으로 전송.
  TLS 인증서, 키 교환, 연결 파라미터가 단일 왕복으로 완료.

보안 강화:
  QUIC은 헤더 포함 거의 모든 패킷을 암호화 (TLS 1.3 의무)
  TCP+TLS: 초기 TCP 핸드셰이크는 평문
  QUIC: Initial 패킷도 AEAD로 보호 → 트래픽 분석/수정 방지
```

**QUIC이 해결한 것들**

| 문제 | HTTP/2 (TCP+TLS) | HTTP/3 (QUIC) |
|------|-----------------|--------------|
| HOL Blocking | TCP 레벨 존재 | 스트림별 독립 처리 |
| 초기 연결 | TCP(1RTT)+TLS(1~2RTT) = 2~3RTT | QUIC 1RTT (TLS 통합) |
| 재연결 | 새 핸드셰이크 (1~2RTT) | 0-RTT (PSK 재사용) |
| IP 변경 시 | 연결 끊김 (WiFi→LTE) | Connection ID로 유지 |
| 패킷 암호화 | TLS 전까지 평문 | 처음부터 암호화 |

**스트림별 독립 패킷 손실 처리**
```
QUIC 스트림1 패킷 손실 → 스트림1만 재전송 대기
QUIC 스트림2, 3 → 영향 없이 계속 진행

(HTTP/2 TCP: 스트림1 손실 → 스트림2, 3도 전부 대기)
```

**Connection Migration**
```
WiFi → LTE로 전환 시:
TCP: (src IP, src Port, dst IP, dst Port) 4-tuple로 연결 식별
     → IP 변경 = 새 연결 (TCP 핸드셰이크 + TLS 핸드셰이크 재시작)

QUIC: 64bit Connection ID로 연결 식별
      → IP 변경되어도 Connection ID 유지 → 끊김 없이 계속
      → 모바일 앱에서 WiFi → LTE 전환 시 스트리밍 유지
```

**0-RTT 재연결 메커니즘**
```
첫 연결:
  QUIC 핸드셰이크 → 서버가 Session Ticket(PSK) 발급 → 클라이언트 저장

재연결 (0-RTT):
  클라이언트 → 첫 패킷에 PSK + 데이터 함께 전송
  서버 → PSK 검증 후 즉시 처리 (핸드셰이크 대기 없음)

0-RTT 주의점:
  Replay Attack 가능 (공격자가 패킷 재전송)
  → 멱등성 있는 GET 요청에만 권장, POST/PUT은 1-RTT 권장
```

---

## 버전별 비교 요약

```
HTTP/1.1  ── TCP 1개 연결, 순차 처리, HOL Blocking 심각
HTTP/2    ── TCP 1개 연결, 멀티플렉싱, TCP 레벨 HOL 남음
HTTP/3    ── UDP+QUIC, 스트림 독립, HOL 완전 해결, 빠른 연결
```

---

## 예시 코드 (Python)

```python
import asyncio
import ssl
import time
from dataclasses import dataclass


@dataclass
class Request:
    id: int
    url: str
    size_kb: int


# ── HTTP/1.1 순차 처리 vs HTTP/2 멀티플렉싱 비교 ─────────

def http1_sequential(requests: list[Request]) -> float:
    """HTTP/1.1: 순차 처리 (HOL Blocking 시뮬레이션)"""
    start = time.time()
    for req in requests:
        time.sleep(req.size_kb * 0.005)
        print(f"[HTTP/1.1] 완료: {req.url} ({req.size_kb}KB)")
    return time.time() - start


async def _fetch_h2(req: Request):
    """HTTP/2 스트림 하나 — 비동기로 동시에 처리"""
    await asyncio.sleep(req.size_kb * 0.005)
    print(f"[HTTP/2]   완료: {req.url} ({req.size_kb}KB)")


async def http2_multiplexed(requests: list[Request]) -> float:
    """HTTP/2: asyncio.gather로 멀티플렉싱 시뮬레이션"""
    start = time.time()
    # 하나의 TLS 연결 위에서 모든 요청을 동시에 처리
    await asyncio.gather(*[_fetch_h2(r) for r in requests])
    return time.time() - start


# ── asyncio + HTTPS: 실제 비동기 HTTPS 요청 패턴 ─────────

async def async_https_request(host: str, path: str) -> bytes:
    """
    asyncio로 HTTPS 요청 (저수준):
    SSL 컨텍스트 생성 → open_connection으로 TLS 연결 → HTTP 요청 → 읽기
    """
    ssl_ctx = ssl.create_default_context()

    # asyncio가 TLS 핸드셰이크를 비동기로 처리
    # → 핸드셰이크 대기 중에도 이벤트 루프가 다른 코루틴 실행 가능
    reader, writer = await asyncio.open_connection(host, 443, ssl=ssl_ctx)

    # HTTP/1.1 요청 전송
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Connection: close\r\n\r\n"
    )
    writer.write(request.encode())
    await writer.drain()

    # 응답 읽기 (비동기 — 데이터 올 때까지 이벤트 루프에 제어 반환)
    response = await reader.read(4096)
    writer.close()
    return response


async def concurrent_https_demo(host: str = "httpbin.org"):
    """
    여러 HTTPS 요청을 동시에 (asyncio.gather):
    HTTP/1.1 방식이지만 비동기로 I/O 대기를 겹치게 만든 것.
    HTTP/2 라이브러리(httpx, aiohttp)를 쓰면 실제 단일 TLS 연결로 멀티플렉싱.
    """
    paths = ["/get", "/ip", "/uuid"]
    print(f"\n[비동기 HTTPS] {len(paths)}개 요청 동시 처리")

    start = time.time()
    try:
        results = await asyncio.gather(
            *[async_https_request(host, p) for p in paths],
            return_exceptions=True
        )
        elapsed = time.time() - start
        for path, result in zip(paths, results):
            if isinstance(result, Exception):
                print(f"  {path}: 오류 ({result})")
            else:
                status_line = result.split(b"\r\n")[0].decode()
                print(f"  {path}: {status_line}")
        print(f"  총 시간: {elapsed:.2f}s (순차라면 ~{len(paths)*0.5:.1f}s 예상)")
    except Exception as e:
        print(f"  접속 실패 (네트워크 없음 가능): {e}")


# ── HTTPS 연결 풀과 TLS 세션 재사용 ──────────────────────

class HttpsConnectionPool:
    """
    TLS 세션 재사용을 활용한 HTTPS 연결 풀.
    HTTP/2 멀티플렉싱의 핵심: 하나의 TLS 연결을 여러 요청이 공유.
    """
    def __init__(self, host: str, max_connections: int = 5):
        self.host = host
        self.max_connections = max_connections
        self._ssl_ctx = ssl.create_default_context()

        # TLS 세션 재사용 활성화:
        # 이전 핸드셰이크의 Session Ticket(TLS 1.3 PSK)으로
        # 다음 연결 시 핸드셰이크 생략 가능 (0-RTT 또는 1-RTT로 단축)
        # Python ssl은 자동으로 세션 캐시 유지

        self._semaphore = asyncio.Semaphore(max_connections)

    async def get(self, path: str) -> tuple[int, bytes]:
        async with self._semaphore:  # 최대 연결 수 제한
            try:
                reader, writer = await asyncio.open_connection(
                    self.host, 443, ssl=self._ssl_ctx
                )
                writer.write(
                    f"GET {path} HTTP/1.1\r\nHost: {self.host}\r\n"
                    f"Connection: close\r\n\r\n".encode()
                )
                await writer.drain()
                data = await reader.read(8192)
                writer.close()
                status = int(data.split(b" ")[1]) if b" " in data else 0
                return status, data
            except Exception as e:
                return 0, str(e).encode()


# ── TCP HOL Blocking vs QUIC 스트림 독립 시뮬레이션 ──────

async def tcp_hol_blocking():
    """
    HTTP/2 over TCP: 패킷 손실 시 모든 스트림 대기
    """
    print("\n[HTTP/2 + TCP] 패킷 손실 시뮬레이션")

    # TCP 레벨 HOL: 손실된 패킷 재전송될 때까지 뒤 스트림 전부 대기
    async def stream_tcp(name: str, delay: float, hol_block_until: float = 0):
        await asyncio.sleep(hol_block_until)   # HOL 블로킹 대기
        await asyncio.sleep(delay)
        print(f"  [{name}] 완료")

    start = time.time()
    packet_loss_retransmit = 0.15  # 재전송 시간
    await asyncio.gather(
        stream_tcp("스트림1(손실)", 0.05, hol_block_until=packet_loss_retransmit),
        stream_tcp("스트림2",       0.02, hol_block_until=packet_loss_retransmit),
        stream_tcp("스트림3",       0.01, hol_block_until=packet_loss_retransmit),
    )
    print(f"  HTTP/2+TCP 총 시간: {time.time()-start:.2f}s (모든 스트림이 재전송 대기)")


async def quic_independent_streams():
    """
    HTTP/3 QUIC: 스트림별 독립 → 다른 스트림에 영향 없음
    """
    print("\n[HTTP/3 + QUIC] 스트림 독립 처리")

    async def stream_quic(name: str, delay: float, packet_loss: bool = False):
        if packet_loss:
            print(f"  [{name}] 패킷 손실 → 해당 스트림만 재전송 중...")
            await asyncio.sleep(0.15)  # 해당 스트림만 재전송 대기
        await asyncio.sleep(delay)
        print(f"  [{name}] 완료")

    start = time.time()
    await asyncio.gather(
        stream_quic("스트림1(손실)", 0.05, packet_loss=True),
        stream_quic("스트림2",       0.02),   # 스트림1과 무관하게 진행
        stream_quic("스트림3",       0.01),   # 스트림1과 무관하게 진행
    )
    print(f"  HTTP/3+QUIC 총 시간: {time.time()-start:.2f}s (다른 스트림은 영향 없음)")


# ── 실행 ──────────────────────────────────────────────────

if __name__ == "__main__":
    requests = [
        Request(1, "/api/switches", 50),
        Request(2, "/api/aps",      30),
        Request(3, "/dashboard.js", 200),
    ]

    print("=== HTTP/1.1 순차 처리 ===")
    t1 = http1_sequential(requests)
    print(f"총 시간: {t1:.3f}s\n")

    print("=== HTTP/2 멀티플렉싱 (asyncio.gather) ===")
    t2 = asyncio.run(http2_multiplexed(requests))
    print(f"총 시간: {t2:.3f}s (가장 느린 요청 기준 — 병렬 처리)\n")

    # HOL Blocking vs QUIC 비교
    asyncio.run(tcp_hol_blocking())
    asyncio.run(quic_independent_streams())

    # 비동기 HTTPS (네트워크 있으면 실행)
    # asyncio.run(concurrent_https_demo("httpbin.org"))
```

---

## 면접 예상 질문

- Q: HTTP/1.1의 HOL Blocking이란?
  A: 파이프라이닝 사용 시 앞 요청의 응답이 오기 전까지 뒤 응답을 처리 못 하는 문제. 앞 요청이 느리면 뒤 요청들이 모두 대기. 브라우저는 이를 우회하려고 도메인당 TCP 연결 6개를 병렬로 맺음.

- Q: HTTP/2는 왜 TLS(HTTPS)가 사실상 필수인가?
  A: 스펙상 평문(h2c)도 가능하지만, Chrome/Firefox 등 모든 브라우저가 TLS 위에서만 HTTP/2를 구현. 이유는 TLS Handshake의 ALPN 확장을 통해 h2 프로토콜을 별도 왕복 없이 협상할 수 있고, 중간 네트워크 장비(프록시, NAT)가 HTTP/2 바이너리 프레임을 HTTP/1.1로 오해해 변형하는 문제를 방지하기 위함.

- Q: HTTP/2 멀티플렉싱이란?
  A: 하나의 TLS 연결 안에서 여러 스트림으로 요청/응답을 동시에 처리. 각 스트림은 독립적으로 HTTP 요청/응답을 처리하고 프레임 단위로 인터리빙(교차 전송). HTTP/1.1의 애플리케이션 레벨 HOL Blocking 해결. 단, TCP 패킷 손실 시 모든 스트림이 대기하는 TCP 레벨 HOL은 여전히 존재.

- Q: HTTP/3이 UDP를 쓰는 이유는?
  A: TCP의 구조적 한계(HOL Blocking, 느린 연결 수립, IP 변경 시 연결 끊김)를 해결하기 위해. UDP 위에 QUIC을 구현해 스트림별 독립 패킷 손실 처리, 1RTT 연결 수립(TLS 1.3 통합), Connection Migration을 지원. 또한 QUIC은 TLS 1.3을 내장해 초기 패킷부터 암호화.

- Q: HTTP/2와 HTTP/3의 HOL Blocking 차이는?
  A: HTTP/2는 멀티플렉싱으로 애플리케이션 레벨 HOL은 해결했지만, TCP 패킷 하나 손실 시 전체 스트림이 재전송을 기다리는 TCP 레벨 HOL이 남아있음. HTTP/3(QUIC)은 스트림별로 독립적으로 패킷 손실을 처리해 하나의 스트림 손실이 다른 스트림에 영향 없음.

- Q: QUIC의 0-RTT 재연결이란? 위험은?
  A: 이전 세션에서 받은 Session Ticket(PSK)을 다음 연결의 첫 패킷에 데이터와 함께 전송해 핸드셰이크 없이 즉시 통신. 위험: Replay Attack — 공격자가 캡처한 0-RTT 패킷을 재전송하면 서버가 동일 요청을 중복 처리할 수 있음. 대응: 멱등성 있는 GET 요청에만 사용, POST/결제 등은 1-RTT 사용.

- Q: QUIC의 Connection Migration이란?
  A: TCP는 (src IP, src Port, dst IP, dst Port) 4-tuple로 연결을 식별해 WiFi→LTE 전환 시 IP 변경으로 연결이 끊김. QUIC은 64bit Connection ID로 연결을 식별해 IP가 바뀌어도 연결이 유지됨. 모바일 환경에서 끊김 없는 통신 가능. 새 TLS+TCP 핸드셰이크 불필요.

- Q: asyncio로 HTTP 요청을 동시에 보내면 HTTP/2 멀티플렉싱이 되는가?
  A: 다르다. asyncio.gather로 여러 HTTP 요청을 보내면 각각 별도 TCP/TLS 연결을 맺어 I/O 대기를 겹치게 하는 것(동시성). HTTP/2 멀티플렉싱은 단일 TLS 연결 위에서 스트림으로 여러 요청을 처리. 실제 HTTP/2 멀티플렉싱을 쓰려면 httpx, aiohttp 같은 HTTP/2 지원 라이브러리 필요.

---

## 관련 개념

- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — HTTP 기본 동작 및 TLS
- [01-05 TCP 3-way Handshake](./01-05-tcp-handshake.md) — HTTP/1.1, HTTP/2의 기반
- [01-04 TCP vs UDP](./01-04-tcp-udp.md) — HTTP/3 QUIC의 UDP 기반
