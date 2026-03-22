# 01-15 방화벽 / 프록시 / NAT

## 개념

| 장치 | 역할 | 동작 계층 |
|------|------|---------|
| 방화벽 (Firewall) | 트래픽 허용/차단 정책 | L3/L4 (IP, 포트) ~ L7 |
| 프록시 (Proxy) | 클라이언트 대신 통신 중계 | L7 (애플리케이션) |
| NAT | 사설 IP ↔ 공인 IP 변환 | L3 |

---

## 방화벽 (Firewall)

### 동작 원리

트래픽의 출발지/목적지 IP, 포트, 프로토콜을 **ACL(Access Control List)** 규칙으로 허용/차단.

```
규칙 (위에서 아래로 순서대로 적용, 첫 매칭에서 결정):

1. ALLOW  TCP  192.168.99.0/24 → 스위치:22     (관리망 SSH 허용)
2. ALLOW  UDP  192.168.99.0/24 → 스위치:161    (관리망 SNMP 허용)
3. ALLOW  TCP  ANY             → 스위치:443    (HTTPS 전체 허용)
4. DENY   ANY  ANY             → ANY           (나머지 전부 차단)
```

### Stateful vs Stateless 방화벽

**Stateless**: 패킷 하나씩 독립 판단. 응답 패킷도 별도 규칙 필요.

```
ALLOW TCP ANY → 서버:80   (요청)
ALLOW TCP 서버:80 → ANY  (응답도 규칙 필요)
```

**Stateful**: 연결 상태 추적. 허용된 연결의 응답은 자동 허용.

```
ALLOW TCP ANY → 서버:80
→ 이 연결의 응답 패킷(서버:80 → 클라이언트)은 자동 허용
→ 규칙 절반으로 줄어듦 (실무 표준)
```

### 방화벽 유형

| 유형 | 동작 | 특징 |
|------|------|------|
| 패킷 필터링 | L3/L4 IP, 포트 기준 | 빠름, 내용 모름 |
| Stateful Inspection | 연결 상태 추적 | 일반적인 방화벽 |
| WAF (Web Application Firewall) | HTTP 내용 분석 | SQL Injection, XSS 차단 |
| NGFW (Next-Gen Firewall) | 애플리케이션 식별 | L7 DPI, IPS 통합 |

### 스위치/AP 관점

```
관리 VLAN(VLAN99) 방화벽 정책:
ALLOW SSH(22)   from 192.168.99.0/24  (NMS 서버만)
ALLOW SNMP(161) from 192.168.99.10    (NMS 서버만)
ALLOW HTTPS(443) from 192.168.99.0/24
DENY  ALL                              (나머지 차단)

→ 사용자 VLAN에서 스위치 관리 포트 직접 접근 불가
```

---

## 프록시 (Proxy)

### Forward Proxy

**클라이언트 앞**에 위치. 클라이언트 대신 외부 서버에 요청.

```
클라이언트 → [Forward Proxy] → 인터넷

용도:
- 클라이언트 IP 숨기기 (익명성)
- 기업 내부 인터넷 접근 제어 (특정 사이트 차단)
- 캐시 (같은 콘텐츠 반복 요청 시 Proxy에서 응답)
```

### Reverse Proxy

**서버 앞**에 위치. 외부 요청을 받아 내부 서버로 전달.

```
인터넷 → [Reverse Proxy] → 서버1
                        → 서버2
                        → 서버3

용도:
- 서버 IP/구조 은닉 (외부엔 Proxy IP만 노출)
- 로드 밸런싱
- TLS 종료 (Proxy에서 HTTPS 처리, 내부는 HTTP)
- 캐싱, 압축
- WAF 적용

대표 도구: Nginx, HAProxy, Envoy
```

```
NMS 환경 예시:
외부 ──HTTPS──▶ [Nginx Reverse Proxy :443]
                → /api/switches → 스위치 API 서버
                → /api/aps     → AP API 서버
                → /dashboard   → 웹 서버

내부 서버는 HTTP만, 외부엔 HTTPS만 노출
```

---

## NAT (Network Address Translation)

### 동작 원리

**사설 IP → 공인 IP 변환**. 가정/기업 내부 장비가 인터넷에 나갈 수 있게 함.

```
사설 IP 대역 (인터넷 라우팅 안 됨):
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
```

**NAT 동작**

```
[출발]
내부 PC: 192.168.1.10:5000 → 구글: 8.8.8.8:80

라우터 NAT 테이블 기록:
192.168.1.10:5000 → 공인IP:60001

외부로 나가는 패킷:
공인IP:60001 → 구글: 8.8.8.8:80

[응답]
구글: 8.8.8.8:80 → 공인IP:60001

라우터: NAT 테이블 조회 → 192.168.1.10:5000으로 전달
```

### NAT 종류

| 종류 | 설명 | 용도 |
|------|------|------|
| SNAT (Source NAT) | 출발지 IP 변환. 내부→외부 | 가정/기업 인터넷 접속 |
| DNAT (Destination NAT) | 목적지 IP 변환. 외부→내부 | 포트 포워딩, 서버 공개 |
| PAT (Port Address Translation) | 포트까지 변환. 공인 IP 하나로 여러 장비 | 가정 공유기 (NAPT) |

### 포트 포워딩 (DNAT)

```
외부: 공인IP:8022 → 스위치 SSH

라우터 DNAT 규칙:
공인IP:8022 → 192.168.99.1:22 (SW-CORE-01)
공인IP:8023 → 192.168.99.2:22 (SW-EDGE-01)

→ 공인 IP 하나로 내부 장비 여러 개에 SSH 접근 가능
```

---

## 예시 코드 (Python)

```python
from dataclasses import dataclass
from typing import Optional


# ── 방화벽 ACL 시뮬레이션 ─────────────────────────────

@dataclass
class AclRule:
    action: str      # "allow" or "deny"
    proto: str       # "tcp", "udp", "any"
    src: str         # CIDR or "any"
    dst_port: int    # 0 = any
    description: str = ""


class Firewall:
    def __init__(self):
        self.rules: list[AclRule] = []

    def add_rule(self, rule: AclRule):
        self.rules.append(rule)

    def _ip_in_cidr(self, ip: str, cidr: str) -> bool:
        if cidr == "any":
            return True
        import ipaddress
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)

    def check(self, src_ip: str, proto: str, dst_port: int) -> str:
        for rule in self.rules:
            if (rule.proto in (proto, "any") and
                self._ip_in_cidr(src_ip, rule.src) and
                (rule.dst_port == 0 or rule.dst_port == dst_port)):
                return rule.action
        return "deny"  # 기본 차단


# 스위치 관리 방화벽 설정
fw = Firewall()
fw.add_rule(AclRule("allow", "tcp", "192.168.99.0/24", 22,  "관리망 SSH"))
fw.add_rule(AclRule("allow", "udp", "192.168.99.0/24", 161, "관리망 SNMP"))
fw.add_rule(AclRule("allow", "tcp", "any",              443, "HTTPS 전체"))
fw.add_rule(AclRule("deny",  "any", "any",              0,   "나머지 차단"))

tests = [
    ("192.168.99.10", "tcp", 22),   # 관리망 SSH → allow
    ("192.168.1.50",  "tcp", 22),   # 사용자망 SSH → deny
    ("1.2.3.4",       "tcp", 443),  # 외부 HTTPS → allow
    ("1.2.3.4",       "tcp", 80),   # 외부 HTTP → deny
]

print("=== 방화벽 ACL 검사 ===")
for src, proto, port in tests:
    result = fw.check(src, proto, port)
    print(f"  {src:15} {proto:3} :{port:3} → {result.upper()}")


# ── NAT 테이블 시뮬레이션 ─────────────────────────────

@dataclass
class NatEntry:
    private_ip: str
    private_port: int
    public_port: int


class NatTable:
    def __init__(self, public_ip: str):
        self.public_ip = public_ip
        self._table: dict[int, NatEntry] = {}  # public_port → entry
        self._next_port = 60000

    def outbound(self, private_ip: str, private_port: int) -> tuple[str, int]:
        """SNAT: 사설→공인 변환"""
        # 기존 엔트리 확인
        for pub_port, entry in self._table.items():
            if entry.private_ip == private_ip and entry.private_port == private_port:
                return self.public_ip, pub_port

        # 새 엔트리 생성
        pub_port = self._next_port
        self._next_port += 1
        self._table[pub_port] = NatEntry(private_ip, private_port, pub_port)
        print(f"[NAT] 새 매핑: {private_ip}:{private_port} → {self.public_ip}:{pub_port}")
        return self.public_ip, pub_port

    def inbound(self, public_port: int) -> Optional[tuple[str, int]]:
        """DNAT: 공인→사설 변환"""
        entry = self._table.get(public_port)
        if entry:
            return entry.private_ip, entry.private_port
        return None

    def show(self):
        print("\n[NAT Table]")
        for pub_port, e in self._table.items():
            print(f"  {e.private_ip}:{e.private_port} ↔ {self.public_ip}:{pub_port}")


print("\n=== NAT 동작 ===")
nat = NatTable(public_ip="203.0.113.1")

# 내부 장비들이 외부로 나감
nat.outbound("192.168.1.10", 50000)
nat.outbound("192.168.1.20", 50001)
nat.outbound("192.168.1.10", 50000)  # 동일 → 기존 매핑 재사용

# 응답 패킷 역변환
result = nat.inbound(60000)
print(f"[NAT] 공인:60000 → {result}")

nat.show()
```

---

## 면접 예상 질문

- Q: Stateful 방화벽과 Stateless 방화벽의 차이는?
  A: Stateless는 패킷 하나씩 독립 판단, 응답 패킷도 별도 허용 규칙 필요. Stateful은 연결 상태를 추적해 허용된 연결의 응답은 자동 허용. 규칙이 단순해지고 보안이 강화됨. 현대 방화벽은 대부분 Stateful.

- Q: Forward Proxy와 Reverse Proxy의 차이는?
  A: Forward Proxy는 클라이언트 앞에서 외부 요청을 대신 처리 (클라이언트 IP 은닉, 접근 제어). Reverse Proxy는 서버 앞에서 외부 요청을 받아 내부 서버로 전달 (서버 구조 은닉, 로드 밸런싱, TLS 종료).

- Q: NAT이 필요한 이유는?
  A: IPv4 주소 부족. 전 세계 공인 IP는 약 43억 개뿐. NAT으로 사설 IP를 공인 IP로 변환해 하나의 공인 IP로 수천 개 내부 장비가 인터넷 사용 가능. 내부 네트워크 구조도 외부에 숨겨지는 보안 효과도 있음.

- Q: NAT 환경에서 외부에서 내부 서버에 접근하려면?
  A: 포트 포워딩(DNAT) 사용. 라우터에 "공인IP:특정포트 → 내부IP:포트" 규칙 설정. 예: 외부에서 203.0.113.1:8022로 접속 → 내부 스위치 192.168.99.1:22로 포워딩.

- Q: DMZ란?
  A: Demilitarized Zone. 내부망과 외부망 사이의 중간 영역. 외부에서 접근해야 하는 서버(웹, 메일)를 DMZ에 배치. 내부망과 분리해 DMZ 서버가 해킹돼도 내부망은 보호.

---

## 관련 개념

- [01-02 VLAN / Trunk / Access Port](./01-02-vlan.md) — 관리 VLAN 분리
- [01-03 ARP](./01-03-arp.md) — NAT 환경에서 ARP 동작
- [01-13 로드 밸런싱](./01-13-load-balancing.md) — Reverse Proxy와 LB 연관
