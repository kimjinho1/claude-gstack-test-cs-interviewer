# 01-09 쿠키 / 세션 / JWT

## 개념

HTTP는 **Stateless** — 요청마다 이전 상태를 기억하지 못함.
로그인 상태를 유지하려면 별도 메커니즘이 필요.

| 방식 | 상태 저장 위치 | 특징 |
|------|-------------|------|
| 쿠키 | 클라이언트(브라우저) | 서버 부담 없음, 브라우저 자동 전송 |
| 세션 | 서버 (+ 세션ID는 쿠키) | 서버가 상태 관리, 확장성 문제 |
| JWT | 클라이언트 (토큰) | 서버 무상태, 분산 환경 적합 |

---

## 동작 원리

### 쿠키

서버가 응답에 `Set-Cookie` 헤더로 값을 심으면, 브라우저가 이후 요청마다 자동으로 `Cookie` 헤더에 포함해서 전송.

```
[로그인 요청]
POST /login
Body: {id: "admin", pw: "1234"}

[로그인 응답]
HTTP/1.1 200 OK
Set-Cookie: user_id=42; Path=/; HttpOnly; Secure; Max-Age=3600

[이후 모든 요청에 자동 포함]
GET /dashboard
Cookie: user_id=42
```

**쿠키 주요 속성**

| 속성 | 역할 |
|------|------|
| `HttpOnly` | JS로 접근 불가 → XSS 공격 시 탈취 방지 |
| `Secure` | HTTPS에서만 전송 |
| `SameSite` | 다른 도메인 요청에 쿠키 포함 여부 → CSRF 방지 |
| `Max-Age` | 만료 시간 (초). 없으면 브라우저 닫을 때 삭제 |
| `Domain` | 쿠키 유효 도메인 범위 |

**쿠키 단점**
- 클라이언트에 저장 → 민감 정보 직접 저장 위험
- 4KB 크기 제한
- 브라우저 자동 전송 → CSRF 공격 취약

---

### 세션

쿠키에 민감 정보 대신 **세션 ID만** 저장. 실제 데이터는 서버(메모리/DB/Redis)에 보관.

```
[로그인]
클라이언트 ──POST /login──▶ 서버
                             서버: 세션 생성 (session_id=abc123, user_id=42, role=admin)
                             서버 메모리에 저장
클라이언트 ◀──Set-Cookie: session_id=abc123── 서버

[이후 요청]
클라이언트 ──GET /dashboard (Cookie: session_id=abc123)──▶ 서버
                             서버: session_id로 메모리 조회 → user_id=42, role=admin 확인
클라이언트 ◀──200 OK── 서버

[로그아웃]
서버: 세션 삭제 → 즉시 무효화
```

**세션 문제점 — 확장성**
```
서버 A에 세션 저장
          → 로드 밸런서가 서버 B로 요청 보내면?
          → 서버 B는 세션 모름 → 로그인 풀림

해결:
1. Sticky Session: 같은 클라이언트는 항상 같은 서버로 (비효율)
2. 세션 공유 저장소: Redis 같은 외부 저장소에 세션 중앙화
```

---

### JWT (JSON Web Token)

서버가 상태를 저장하지 않음. **토큰 자체에 정보를 담고 서명**해서 클라이언트에 발급.
서버는 토큰의 서명만 검증하면 됨.

**구조: Header.Payload.Signature** (`.`으로 구분, Base64 인코딩)

```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo0Mn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
└──── Header ────┘ └──── Payload ────┘ └──────────── Signature ─────────────────────┘

Header:    {"alg": "HS256", "typ": "JWT"}
Payload:   {"user_id": 42, "role": "admin", "exp": 1700000000}
Signature: HMAC-SHA256(base64(header) + "." + base64(payload), secret_key)
```

**동작 흐름**

```
[로그인]
클라이언트 ──POST /login──▶ 서버
                             서버: JWT 생성 (서명 포함)
클라이언트 ◀──{token: "eyJ..."}── 서버
클라이언트: 로컬스토리지 또는 메모리에 저장

[이후 요청]
클라이언트 ──GET /api/switches (Authorization: Bearer eyJ...)──▶ 서버
                             서버: Signature 검증 → Payload 읽기
                             DB 조회 없이 user_id, role 바로 확인
클라이언트 ◀──200 OK── 서버
```

**JWT 검증 원리**

```
서버가 가진 secret_key로 Header+Payload 재서명
→ 토큰의 Signature와 비교
→ 일치하면 변조 없음, 불일치하면 위조 토큰
```

Payload는 Base64 인코딩(암호화 아님) → **누구나 읽을 수 있음**. 민감 정보 넣으면 안 됨.

**JWT 단점 — 로그아웃/무효화 문제**

```
세션: 서버에서 삭제하면 즉시 무효화 가능
JWT:  토큰이 클라이언트에 있음 → 서버가 강제 무효화 불가
      만료 시간(exp) 전까지 유효

해결:
1. 짧은 만료 시간 (Access Token: 15분) + 긴 Refresh Token (7일)
2. Blacklist: 무효화할 토큰 ID를 Redis에 저장 (stateless 장점 일부 포기)
```

---

### Access Token + Refresh Token 패턴

```
[최초 로그인]
서버 발급:
  Access Token  (만료: 15분) → API 요청에 사용
  Refresh Token (만료: 7일)  → Access Token 재발급에만 사용

[일반 API 요청]
Authorization: Bearer {access_token}

[Access Token 만료 시]
클라이언트 ──POST /refresh (refresh_token)──▶ 서버
클라이언트 ◀──{new_access_token}── 서버

[로그아웃]
Refresh Token을 서버 Blacklist에 추가 or DB에서 삭제
→ Access Token은 15분 후 자연 만료
```

---

## 세 가지 비교

| 구분 | 쿠키 | 세션 | JWT |
|------|------|------|-----|
| 상태 저장 | 클라이언트 | 서버 | 클라이언트 (토큰) |
| 서버 부담 | 없음 | 있음 (조회 필요) | 없음 (검증만) |
| 확장성 | 좋음 | 나쁨 (공유 저장소 필요) | 좋음 |
| 즉시 무효화 | 불가 | 가능 | 어려움 |
| 보안 | CSRF 취약 | 안전 | XSS 주의 |

---

## 예시 코드 (Python)

```python
import hmac
import hashlib
import base64
import json
import time
import secrets
from dataclasses import dataclass, field
from typing import Optional


# ── 세션 구현 ─────────────────────────────────────────

class SessionStore:
    """서버 측 세션 저장소 (Redis 역할)"""
    def __init__(self):
        self._store: dict[str, dict] = {}

    def create(self, user_id: int, role: str) -> str:
        session_id = secrets.token_hex(16)
        self._store[session_id] = {
            "user_id": user_id,
            "role": role,
            "created_at": time.time()
        }
        return session_id

    def get(self, session_id: str) -> Optional[dict]:
        return self._store.get(session_id)

    def delete(self, session_id: str):
        self._store.pop(session_id, None)


# ── JWT 구현 ──────────────────────────────────────────

class JwtService:
    def __init__(self, secret: str, access_ttl: int = 900, refresh_ttl: int = 604800):
        self.secret = secret.encode()
        self.access_ttl = access_ttl    # 15분
        self.refresh_ttl = refresh_ttl  # 7일
        self._blacklist: set[str] = set()

    def _b64(self, data: dict) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(data, separators=(",", ":")).encode()
        ).rstrip(b"=").decode()

    def _sign(self, header_b64: str, payload_b64: str) -> str:
        msg = f"{header_b64}.{payload_b64}".encode()
        sig = hmac.new(self.secret, msg, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(sig).rstrip(b"=").decode()

    def create_access_token(self, user_id: int, role: str) -> str:
        header = self._b64({"alg": "HS256", "typ": "JWT"})
        payload = self._b64({
            "user_id": user_id,
            "role": role,
            "exp": int(time.time()) + self.access_ttl,
            "type": "access"
        })
        return f"{header}.{payload}.{self._sign(header, payload)}"

    def create_refresh_token(self, user_id: int) -> str:
        jti = secrets.token_hex(8)  # JWT ID (블랙리스트용)
        header = self._b64({"alg": "HS256", "typ": "JWT"})
        payload = self._b64({
            "user_id": user_id,
            "jti": jti,
            "exp": int(time.time()) + self.refresh_ttl,
            "type": "refresh"
        })
        return f"{header}.{payload}.{self._sign(header, payload)}"

    def verify(self, token: str) -> Optional[dict]:
        try:
            header_b64, payload_b64, sig = token.split(".")
        except ValueError:
            return None

        # 서명 검증
        expected_sig = self._sign(header_b64, payload_b64)
        if not hmac.compare_digest(sig, expected_sig):
            print("[JWT] 서명 불일치 → 위조 토큰")
            return None

        # Payload 디코딩
        padding = "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + padding))

        # 만료 확인
        if payload.get("exp", 0) < time.time():
            print("[JWT] 만료된 토큰")
            return None

        # 블랙리스트 확인
        if payload.get("jti") in self._blacklist:
            print("[JWT] 블랙리스트 토큰")
            return None

        return payload

    def revoke(self, token: str):
        """Refresh Token 무효화"""
        payload = self.verify(token)
        if payload and "jti" in payload:
            self._blacklist.add(payload["jti"])
            print(f"[JWT] 토큰 무효화: jti={payload['jti']}")


# ── 시뮬레이션 ────────────────────────────────────────

print("=== 세션 방식 ===")
store = SessionStore()
session_id = store.create(user_id=42, role="admin")
print(f"세션 생성: {session_id}")
print(f"세션 조회: {store.get(session_id)}")
store.delete(session_id)
print(f"로그아웃 후: {store.get(session_id)}")  # None

print("\n=== JWT 방식 ===")
jwt = JwtService(secret="super-secret-key")
access = jwt.create_access_token(user_id=42, role="admin")
refresh = jwt.create_refresh_token(user_id=42)

print(f"Access Token: {access[:50]}...")
payload = jwt.verify(access)
print(f"검증 결과: user_id={payload['user_id']}, role={payload['role']}")

# 위조 토큰 시도
fake_token = access[:-5] + "XXXXX"
print(f"위조 토큰 검증: {jwt.verify(fake_token)}")

# Refresh Token 무효화 (로그아웃)
jwt.revoke(refresh)
print(f"무효화 후 Refresh 검증: {jwt.verify(refresh)}")
```

---

## 면접 예상 질문

- Q: 쿠키와 세션의 차이는?
  A: 쿠키는 상태를 클라이언트에 저장. 세션은 서버에 상태를 저장하고 클라이언트에는 세션 ID만 쿠키로 전달. 쿠키는 클라이언트 위변조 가능, 세션은 서버에서 관리해 안전하지만 확장성 문제 있음.

- Q: JWT의 장단점은?
  A: 장점: 서버가 상태를 저장하지 않아 확장성 좋음. 분산 서버 환경에서 DB 조회 없이 검증 가능. 단점: 토큰 즉시 무효화 어려움. Payload는 암호화 아니라 누구나 읽을 수 있음. 토큰 탈취 시 만료 전까지 악용 가능.

- Q: JWT를 localStorage에 저장하면 안 되는 이유는?
  A: XSS 공격으로 JS가 실행되면 localStorage 토큰을 탈취할 수 있음. HttpOnly 쿠키에 저장하면 JS 접근 불가. 단, 쿠키 저장 시 CSRF 방어 필요(SameSite 설정).

- Q: Access Token + Refresh Token 패턴을 쓰는 이유는?
  A: JWT 즉시 무효화 문제 완화. Access Token은 짧은 만료 시간(15분)으로 탈취 피해 최소화. Refresh Token으로 Access Token 재발급. 로그아웃 시 Refresh Token만 서버에서 무효화.

- Q: 세션의 확장성 문제와 해결책은?
  A: 로드 밸런서가 여러 서버로 분산 시 세션이 저장된 서버가 아닌 다른 서버로 요청이 가면 세션을 찾지 못함. 해결: Redis 같은 중앙 세션 저장소 공유, 또는 Sticky Session(같은 클라이언트는 항상 같은 서버로 라우팅).

---

## 관련 개념

- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — 쿠키/세션/JWT가 동작하는 기반
- [01-10 REST API 설계 원칙](./01-10-rest-api.md) — Stateless와 JWT의 연관성
