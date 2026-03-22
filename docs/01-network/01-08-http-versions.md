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

### HTTP/2 — 멀티플렉싱

**하나의 TCP 연결 안에서 여러 요청/응답을 동시에 처리.**

```
HTTP/1.1:
연결1: 요청A ──────── 응답A
연결2: 요청B ──────── 응답B
연결3: 요청C ──────── 응답C

HTTP/2 (하나의 연결, 스트림으로 분리):
          스트림1: [요청A] ──── [응답A]
연결1 ─── 스트림2: [요청B] ──── [응답B]  ← 동시 처리
          스트림3: [요청C] ──── [응답C]
```

**주요 개선사항**

| 기능 | 설명 |
|------|------|
| 멀티플렉싱 | 하나의 TCP 연결에서 여러 스트림 동시 처리 |
| 헤더 압축 (HPACK) | 반복되는 헤더 압축 (Cookie, User-Agent 등) |
| 서버 푸시 | 클라이언트 요청 전에 서버가 미리 리소스 전송 |
| 바이너리 프레임 | 텍스트 → 바이너리로 파싱 효율 향상 |

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

### HTTP/3 — QUIC (UDP 기반)

**TCP를 버리고 UDP 위에 QUIC 프로토콜을 새로 구현.**

```
HTTP/1.1, HTTP/2: [HTTP] → [TLS] → [TCP] → [IP]
HTTP/3:           [HTTP] → [QUIC (TLS 내장)] → [UDP] → [IP]
```

**QUIC이 해결한 것들**

| 문제 | HTTP/2 (TCP) | HTTP/3 (QUIC) |
|------|-------------|--------------|
| HOL Blocking | TCP 레벨 존재 | 스트림별 독립 처리 |
| 연결 수립 | TCP(1RTT) + TLS(1RTT) = 2RTT | QUIC 1RTT (TLS 내장) |
| 재연결 | 새 핸드셰이크 | 0-RTT (이전 세션 재사용) |
| IP 변경 시 | 연결 끊김 (WiFi→LTE) | Connection ID로 유지 |

**스트림별 독립 패킷 손실 처리**
```
QUIC 스트림1 패킷 손실 → 스트림1만 재전송 대기
QUIC 스트림2, 3 → 영향 없이 계속 진행
```

**Connection Migration**
```
WiFi → LTE로 전환 시:
TCP: IP 변경 → 연결 끊김 → 재연결 (3-way handshake 다시)
QUIC: Connection ID 유지 → 끊김 없이 継続
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
import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class Request:
    id: int
    url: str
    size_kb: int  # 응답 크기 (처리 시간 시뮬레이션용)


# HTTP/1.1 시뮬레이션: 순차 처리
def http1_sequential(requests: list[Request]) -> float:
    start = time.time()
    for req in requests:
        time.sleep(req.size_kb * 0.01)  # 크기에 비례한 처리 시간
        print(f"[HTTP/1.1] 완료: {req.url} ({req.size_kb}KB)")
    return time.time() - start


# HTTP/2 시뮬레이션: 멀티플렉싱 (비동기 동시 처리)
async def _fetch_http2(req: Request):
    await asyncio.sleep(req.size_kb * 0.01)
    print(f"[HTTP/2]   완료: {req.url} ({req.size_kb}KB)")


async def http2_multiplexed(requests: list[Request]) -> float:
    start = time.time()
    await asyncio.gather(*[_fetch_http2(r) for r in requests])  # 동시 처리
    return time.time() - start


# HTTP/1.1 HOL Blocking 시뮬레이션
def hol_blocking_demo():
    print("\n=== HTTP/1.1 HOL Blocking ===")
    requests = [
        Request(1, "/large-image.jpg", 500),   # 느린 요청 (먼저 들어옴)
        Request(2, "/style.css", 10),
        Request(3, "/script.js", 20),
    ]
    # 앞 요청이 느리면 뒤 요청들이 모두 대기
    for req in requests:
        delay = req.size_kb * 0.001
        time.sleep(delay)
        print(f"  응답: {req.url} (대기 후 완료)")


# QUIC 스트림 독립성 시뮬레이션
async def quic_independent_streams():
    print("\n=== HTTP/3 QUIC 스트림 독립 처리 ===")

    async def stream(req: Request, packet_loss: bool = False):
        if packet_loss:
            print(f"  [스트림{req.id}] 패킷 손실 발생 → 재전송 중...")
            await asyncio.sleep(0.1)  # 재전송 딜레이
        await asyncio.sleep(req.size_kb * 0.001)
        print(f"  [스트림{req.id}] 완료: {req.url}")

    # 스트림1만 패킷 손실, 나머지는 영향 없음
    await asyncio.gather(
        stream(Request(1, "/large.jpg", 500), packet_loss=True),
        stream(Request(2, "/style.css", 10)),   # 스트림1 영향 없음
        stream(Request(3, "/script.js", 20)),   # 스트림1 영향 없음
    )


# 실행
if __name__ == "__main__":
    requests = [
        Request(1, "/api/switches", 50),
        Request(2, "/api/aps", 30),
        Request(3, "/dashboard.js", 200),
    ]

    print("=== HTTP/1.1 순차 처리 ===")
    t1 = http1_sequential(requests)
    print(f"총 시간: {t1:.2f}s\n")

    print("=== HTTP/2 멀티플렉싱 ===")
    t2 = asyncio.run(http2_multiplexed(requests))
    print(f"총 시간: {t2:.2f}s (병렬 처리로 가장 느린 요청 시간만큼)")

    hol_blocking_demo()
    asyncio.run(quic_independent_streams())
```

---

## 면접 예상 질문

- Q: HTTP/1.1의 HOL Blocking이란?
  A: 파이프라이닝 사용 시 앞 요청의 응답이 오기 전까지 뒤 응답을 처리 못 하는 문제. 앞 요청이 느리면 뒤 요청들이 모두 대기. 브라우저는 이를 우회하려고 도메인당 TCP 연결 6개를 병렬로 맺음.

- Q: HTTP/2 멀티플렉싱이란?
  A: 하나의 TCP 연결 안에서 여러 스트림으로 요청/응답을 동시에 처리. HTTP/1.1의 애플리케이션 레벨 HOL Blocking 해결. 단, TCP 패킷 손실 시 모든 스트림이 대기하는 TCP 레벨 HOL은 여전히 존재.

- Q: HTTP/3이 UDP를 쓰는 이유는?
  A: TCP의 구조적 한계(HOL Blocking, 느린 연결 수립, IP 변경 시 연결 끊김)를 해결하기 위해. UDP 위에 QUIC을 구현해 스트림별 독립 패킷 손실 처리, 1RTT 연결 수립(TLS 내장), Connection Migration을 지원.

- Q: HTTP/2와 HTTP/3의 HOL Blocking 차이는?
  A: HTTP/2는 멀티플렉싱으로 애플리케이션 레벨 HOL은 해결했지만, TCP 패킷 하나 손실 시 전체 스트림이 재전송을 기다리는 TCP 레벨 HOL이 남아있음. HTTP/3(QUIC)은 스트림별로 독립적으로 패킷 손실을 처리해 하나의 스트림 손실이 다른 스트림에 영향 없음.

- Q: QUIC의 Connection Migration이란?
  A: TCP는 IP 주소 기반으로 연결을 식별해 WiFi→LTE 전환 시 연결이 끊김. QUIC은 Connection ID로 연결을 식별해 IP가 바뀌어도 연결이 유지됨. 모바일 환경에서 끊김 없는 통신 가능.

---

## 관련 개념

- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — HTTP 기본 동작 및 TLS
- [01-05 TCP 3-way Handshake](./01-05-tcp-handshake.md) — HTTP/1.1, HTTP/2의 기반
- [01-04 TCP vs UDP](./01-04-tcp-udp.md) — HTTP/3 QUIC의 UDP 기반
