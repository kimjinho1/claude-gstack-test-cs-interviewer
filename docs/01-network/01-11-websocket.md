# 01-11 웹소켓 vs HTTP

## 개념

**HTTP**: 클라이언트가 요청해야만 서버가 응답. 단방향 요청-응답.
**WebSocket**: 한 번 연결하면 서버도 클라이언트에 언제든 데이터 푸시 가능. 양방향 실시간 통신.

---

## 동작 원리

### HTTP의 한계 — Polling

실시간 데이터가 필요한데 HTTP만 쓰면:

```
[Short Polling] 주기적으로 요청 (비효율)
클라이언트: "새 데이터 있어?" → 서버: "없어"
클라이언트: "새 데이터 있어?" → 서버: "없어"
클라이언트: "새 데이터 있어?" → 서버: "있어! 여기"
→ 불필요한 요청 폭발, 서버 부하

[Long Polling] 응답을 일부러 늦게 줌
클라이언트: "새 데이터 있어?" → 서버: (데이터 생길 때까지 응답 안 함)
서버: 데이터 생기면 → "있어! 여기" → 연결 종료
클라이언트: 즉시 다음 요청
→ HTTP보다 낫지만 연결 반복 오버헤드
```

### WebSocket 연결 수립 — HTTP Upgrade

WebSocket은 HTTP로 시작해서 프로토콜을 전환(Upgrade).

```
① 클라이언트 → 서버 (HTTP 요청)
GET /ws HTTP/1.1
Host: nms.local
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==

② 서버 → 클라이언트 (HTTP 101 응답)
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=

③ 이후: WebSocket 프레임으로 양방향 통신
   TCP 연결은 유지된 채 프로토콜만 전환
```

### WebSocket 통신

```
[연결 후]
서버 ──"스위치 포트3 down"──────────▶ 클라이언트 (서버가 먼저 푸시)
클라이언트 ──"포트3 enable 해줘"──────▶ 서버
서버 ──"완료"──────────────────────▶ 클라이언트
서버 ──"AP-02 연결 끊김"─────────────▶ 클라이언트
...
[연결 종료까지 지속]
```

### HTTP vs WebSocket 비교

| 구분 | HTTP | WebSocket |
|------|------|-----------|
| 연결 | 요청마다 새로 (Keep-Alive로 재사용 가능) | 한 번 연결 후 유지 |
| 방향 | 단방향 (클라이언트 → 서버 요청) | 양방향 |
| 서버 푸시 | 불가 (SSE로 우회 가능) | 가능 |
| 오버헤드 | 요청마다 헤더 포함 | 최초 핸드셰이크 후 프레임 단위 (헤더 최소) |
| 용도 | 일반 API, 문서 전송 | 실시간 알림, 채팅, 모니터링 |

### 스위치/AP 관제 관점

```
NMS(Network Management System) 대시보드:
- 스위치 포트 up/down 실시간 표시
- AP 연결 클라이언트 수 실시간 업데이트
- 경보(Alert) 즉시 표시

HTTP Polling 방식:
  브라우저: "장비 상태 줘" → 서버: "이상 없음"  (1초마다 반복)
  → 장비 수 100대면 100번 요청/초

WebSocket 방식:
  한 번 연결 → 서버가 변경 시에만 푸시
  → 효율적, 지연 없는 실시간
```

---

## 예시 코드 (Python)

```python
import asyncio
import json
import websockets
from datetime import datetime


# WebSocket 서버 (NMS 이벤트 푸시)
async def nms_server(websocket):
    print(f"[NMS] 클라이언트 연결: {websocket.remote_address}")
    try:
        # 실시간 이벤트 스트림 시뮬레이션
        events = [
            {"type": "port_down", "device": "SW-CORE-01", "port": 3},
            {"type": "ap_disconnect", "device": "AP-FLOOR2-01"},
            {"type": "cpu_high", "device": "SW-EDGE-01", "value": 92},
        ]
        for event in events:
            await asyncio.sleep(1)
            msg = json.dumps({**event, "timestamp": datetime.now().isoformat()})
            await websocket.send(msg)
            print(f"[NMS] 푸시: {msg}")

        # 클라이언트 메시지 수신도 처리
        async for message in websocket:
            cmd = json.loads(message)
            print(f"[NMS] 수신: {cmd}")
            if cmd.get("action") == "enable_port":
                await websocket.send(json.dumps({"result": "ok", "port": cmd["port"]}))

    except websockets.ConnectionClosed:
        print("[NMS] 클라이언트 연결 종료")


# WebSocket 클라이언트 (대시보드)
async def dashboard_client():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as ws:
        print("[Dashboard] 연결됨")

        # 이벤트 수신 + 명령 전송 동시
        async def receive():
            async for msg in ws:
                event = json.loads(msg)
                print(f"[Dashboard] 이벤트: {event}")

        async def send_command():
            await asyncio.sleep(2)
            await ws.send(json.dumps({"action": "enable_port", "port": 3}))

        await asyncio.gather(receive(), send_command())


# 서버 실행
async def main():
    async with websockets.serve(nms_server, "localhost", 8765):
        await asyncio.Future()  # 무한 대기


# asyncio.run(main())  # 서버 실행
# asyncio.run(dashboard_client())  # 클라이언트 실행
```

---

## 면접 예상 질문

- Q: WebSocket과 HTTP의 차이는?
  A: HTTP는 클라이언트 요청에만 서버가 응답하는 단방향. WebSocket은 한 번 연결 후 서버도 자유롭게 클라이언트로 데이터를 푸시할 수 있는 양방향 통신. HTTP Upgrade 핸드셰이크로 연결 수립 후 TCP 연결을 유지.

- Q: WebSocket이 HTTP보다 효율적인 이유는?
  A: HTTP는 요청마다 헤더(수백 byte)를 반복 전송. WebSocket은 최초 핸드셰이크 후 최소 2byte 헤더의 프레임 단위로 통신. 실시간 빈번한 메시지 교환 시 오버헤드 대폭 감소.

- Q: SSE(Server-Sent Events)와 WebSocket의 차이는?
  A: SSE는 서버→클라이언트 단방향 푸시만 가능. HTTP 기반이라 별도 프로토콜 전환 없음. 재연결 자동 처리. 단순 알림/피드에 적합. WebSocket은 양방향이지만 구현이 복잡. 채팅, 실시간 협업 등 양방향이 필요할 때 사용.

- Q: WebSocket 연결이 끊기면 어떻게 처리하나?
  A: 클라이언트에서 재연결 로직 구현 필요. Exponential Backoff(재시도 간격을 점점 늘림)로 서버 부하 방지. 핑/퐁(Ping/Pong) 프레임으로 연결 살아있는지 주기적 확인.

---

## 관련 개념

- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — WebSocket의 기반 프로토콜
- [01-08 HTTP 버전](./01-08-http-versions.md) — HTTP/2 서버 푸시와 비교
- [01-10 REST API](./01-10-rest-api.md) — REST로 못 하는 실시간 통신
