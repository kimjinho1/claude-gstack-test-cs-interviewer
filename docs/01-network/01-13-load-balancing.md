# 01-13 로드 밸런싱 (Load Balancing)

## 개념

여러 서버에 트래픽을 분산해 **단일 장애점 제거 + 성능 향상**.

```
클라이언트 ──▶ [로드 밸런서] ──▶ 서버1
                           ──▶ 서버2
                           ──▶ 서버3
```

---

## 동작 원리

### 알고리즘

| 알고리즘 | 방식 | 적합한 상황 |
|---------|------|-----------|
| Round Robin | 순서대로 분배 | 서버 성능 동일할 때 |
| Weighted Round Robin | 가중치 비율로 분배 | 서버 성능 다를 때 |
| Least Connection | 현재 연결 수 가장 적은 서버 | 요청 처리 시간 다를 때 |
| IP Hash | 클라이언트 IP로 서버 고정 | 세션 유지 필요 시 |
| Random | 랜덤 | 단순 분산 |

### L4 vs L7 로드 밸런서

**L4 (Transport)**: TCP/UDP 포트 기준 분산. 패킷 내용 안 봄. 빠름.

```
클라이언트 TCP:443 → LB → 서버1:443
                        → 서버2:443
IP/포트만 보고 분산. HTTP 내용 모름.
```

**L7 (Application)**: HTTP 내용(URL, 헤더, 쿠키) 보고 분산. 느리지만 정교함.

```
GET /api/switches → 스위치 API 서버군
GET /api/aps      → AP API 서버군
GET /dashboard    → 웹 서버군

URL 패턴, 헤더, 쿠키 기반으로 라우팅 가능
```

### 헬스 체크

```
LB: 주기적으로 서버에 헬스 체크 요청
GET /health → 200 OK: 정상 → 트래픽 분배
           → 타임아웃/에러: 비정상 → 풀에서 제외
           → 복구 시 다시 풀에 추가
```

### Sticky Session

세션 방식 인증 사용 시, 같은 클라이언트는 항상 같은 서버로.

```
IP Hash or 쿠키 기반:
사용자A → 항상 서버1 (세션 있음)
사용자B → 항상 서버2

단점: 서버1 장애 시 사용자A 세션 손실
해결: Redis로 세션 중앙화 → Sticky Session 불필요
```

---

## 예시 코드 (Python)

```python
import random
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Server:
    id: str
    host: str
    weight: int = 1
    active_connections: int = 0
    healthy: bool = True


class LoadBalancer:
    def __init__(self, algorithm: str = "round_robin"):
        self.servers: list[Server] = []
        self.algorithm = algorithm
        self._rr_index = 0

    def add_server(self, server: Server):
        self.servers.append(server)

    def _healthy_servers(self) -> list[Server]:
        return [s for s in self.servers if s.healthy]

    def get_server(self, client_ip: str = "") -> Server | None:
        healthy = self._healthy_servers()
        if not healthy:
            return None

        if self.algorithm == "round_robin":
            server = healthy[self._rr_index % len(healthy)]
            self._rr_index += 1
            return server

        elif self.algorithm == "weighted_round_robin":
            pool = []
            for s in healthy:
                pool.extend([s] * s.weight)
            server = pool[self._rr_index % len(pool)]
            self._rr_index += 1
            return server

        elif self.algorithm == "least_connection":
            return min(healthy, key=lambda s: s.active_connections)

        elif self.algorithm == "ip_hash":
            idx = hash(client_ip) % len(healthy)
            return healthy[idx]

        elif self.algorithm == "random":
            return random.choice(healthy)

        return healthy[0]

    def mark_unhealthy(self, server_id: str):
        for s in self.servers:
            if s.id == server_id:
                s.healthy = False
                print(f"[LB] {server_id} 비정상 → 풀에서 제외")

    def mark_healthy(self, server_id: str):
        for s in self.servers:
            if s.id == server_id:
                s.healthy = True
                print(f"[LB] {server_id} 복구 → 풀에 추가")


# 시뮬레이션
lb = LoadBalancer(algorithm="least_connection")
lb.add_server(Server("srv1", "192.168.1.1", weight=2))
lb.add_server(Server("srv2", "192.168.1.2", weight=1))
lb.add_server(Server("srv3", "192.168.1.3", weight=1))

print("=== Least Connection 분배 ===")
lb.servers[0].active_connections = 5   # srv1 바쁨
lb.servers[1].active_connections = 2   # srv2 한가
lb.servers[2].active_connections = 3

for i in range(4):
    server = lb.get_server()
    print(f"요청{i+1} → {server.id} (connections={server.active_connections})")

print("\n=== 장애 처리 ===")
lb.mark_unhealthy("srv2")
for i in range(3):
    server = lb.get_server()
    print(f"요청{i+1} → {server.id}")

lb.mark_healthy("srv2")
```

---

## 면접 예상 질문

- Q: L4와 L7 로드 밸런서의 차이는?
  A: L4는 TCP/UDP 포트만 보고 분산. 패킷 내용을 보지 않아 빠름. L7은 HTTP 헤더, URL, 쿠키 등 내용을 분석해 정교한 라우팅 가능. URL 패턴별 서버 분리, A/B 테스트 등 가능. 대신 느리고 복잡.

- Q: Least Connection 알고리즘이 유리한 상황은?
  A: 요청 처리 시간이 균일하지 않을 때. 일부 요청이 오래 걸리면 Round Robin은 해당 서버에 요청이 쌓임. Least Connection은 현재 연결 수가 적은 서버로 보내 부하를 고르게 분산.

- Q: 로드 밸런서 자체가 단일 장애점이 되지 않나?
  A: Active-Passive 또는 Active-Active 이중화로 해결. Active-Passive: 평소엔 하나만 동작, 장애 시 Passive가 VIP(Virtual IP)를 이어받음. Active-Active: 두 LB가 동시 동작, DNS Round Robin이나 Anycast로 분산.

---

## 관련 개념

- [01-09 쿠키 / 세션 / JWT](./01-09-cookie-session-jwt.md) — Sticky Session과 JWT
- [01-15 방화벽 / 프록시 / NAT](./01-15-firewall-proxy-nat.md) — 네트워크 레벨 트래픽 제어
