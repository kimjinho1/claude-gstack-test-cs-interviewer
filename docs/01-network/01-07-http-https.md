# 01-07 HTTP vs HTTPS

## 개념

**HTTP (HyperText Transfer Protocol)** : 웹 통신 프로토콜. TCP 80번 포트. 평문 전송.
**HTTPS** : HTTP + TLS(Transport Layer Security). TCP 443번 포트. 암호화 전송.

| 구분 | HTTP | HTTPS |
|------|------|-------|
| 포트 | 80 | 443 |
| 암호화 | 없음 | TLS로 암호화 |
| 인증 | 없음 | 서버 인증서로 신원 확인 |
| 속도 | 빠름 | TLS 핸드셰이크 오버헤드 있음 |
| 용도 | 공개 정적 콘텐츠 | 로그인, 개인정보, API 등 전부 |

---

## 동작 원리

### HTTP 요청/응답 구조

```
[요청]
GET /api/switches HTTP/1.1
Host: nms.local
Authorization: Bearer eyJhbGci...

[응답]
HTTP/1.1 200 OK
Content-Type: application/json

{"switches": [...]}
```

**HTTP 메서드**

| 메서드 | 역할 |
|--------|------|
| GET | 데이터 조회 |
| POST | 데이터 생성 |
| PUT | 데이터 전체 수정 |
| PATCH | 데이터 일부 수정 |
| DELETE | 데이터 삭제 |

**HTTP 상태 코드**

| 코드 | 의미 |
|------|------|
| 200 OK | 성공 |
| 201 Created | 생성 성공 |
| 400 Bad Request | 잘못된 요청 |
| 401 Unauthorized | 인증 필요 |
| 403 Forbidden | 권한 없음 |
| 404 Not Found | 리소스 없음 |
| 500 Internal Server Error | 서버 오류 |

### HTTPS — TLS Handshake

TCP 3-way handshake 완료 후 **TLS Handshake** 추가 진행.

```
Client                              Server
  │                                    │
  │── TCP 3-way handshake ─────────────│
  │                                    │
  │── ClientHello ────────────────────▶│
  │   (지원 TLS 버전, 암호화 알고리즘 목록)  │
  │                                    │
  │◀── ServerHello ───────────────────│
  │   (선택된 TLS 버전, 암호화 알고리즘)    │
  │                                    │
  │◀── Certificate ───────────────────│
  │   (서버 공개키 포함 인증서)             │
  │                                    │
  │── 인증서 검증 (CA 서명 확인) ──────────│
  │                                    │
  │── Pre-Master Secret ──────────────▶│
  │   (서버 공개키로 암호화해서 전송)        │
  │                                    │
  │  양측 동일한 Session Key 생성          │
  │── Finished ───────────────────────▶│
  │◀── Finished ───────────────────────│
  │                                    │
  │       암호화 통신 시작 (HTTP)          │
```

**왜 안전한가?**
- 서버 인증서로 "진짜 서버인지" 확인 → 중간자 공격 방지
- Session Key로 대칭 암호화 → 도청해도 복호화 불가
- 데이터 무결성 검증 → 전송 중 변조 감지

### TLS 1.2 vs TLS 1.3

| 구분 | TLS 1.2 | TLS 1.3 |
|------|---------|---------|
| 핸드셰이크 | 2-RTT | 1-RTT (핸드셰이크 간소화) |
| 재연결 | - | 0-RTT (이전 세션 재사용) |
| 보안 | 취약 알고리즘 일부 허용 | 취약 알고리즘 제거 |

---

## HTTP가 왜 위험한가

```
HTTP로 스위치 관리 웹 접속 시:
  브라우저 ──[admin:password123]──▶ 스위치

네트워크 상 누구든 패킷 캡처하면 평문으로 보임:
  Wireshark로 캡처 → "Authorization: Basic YWRtaW46cGFzc3dvcmQxMjM="
  Base64 디코딩 → "admin:password123"  ← 그냥 평문이나 마찬가지
```

HTTPS라도 인증서 검증을 무시하면 MITM 공격에 취약:
```
브라우저 ──▶ 공격자(가짜 인증서) ──▶ 스위치
브라우저가 "인증서 경고 무시" 누르면 → 공격자가 중간에서 복호화 가능
```

---

## 예시 코드 (Python)

```python
import http.server
import ssl
import urllib.request
import json
from http.client import HTTPConnection, HTTPSConnection


# HTTP 요청 (평문)
def http_get(host: str, path: str) -> dict:
    conn = HTTPConnection(host, 80)
    conn.request("GET", path, headers={"Accept": "application/json"})
    response = conn.getresponse()
    print(f"[HTTP] {response.status} {response.reason}")
    return json.loads(response.read())


# HTTPS 요청 (암호화)
def https_get(host: str, path: str, verify: bool = True) -> dict:
    import ssl
    ctx = ssl.create_default_context() if verify else ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    if not verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE  # 인증서 검증 무시 (비권장)

    conn = HTTPSConnection(host, 443, context=ctx)
    conn.request("GET", path, headers={"Accept": "application/json"})
    response = conn.getresponse()
    print(f"[HTTPS] {response.status} {response.reason}")
    return json.loads(response.read())


# HTTP 상태 코드별 처리
class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def request(self, method: str, path: str, body: dict = None) -> tuple[int, dict]:
        import urllib.request
        import json

        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, {"error": e.reason}

    def get_switch(self, switch_id: str):
        status, body = self.request("GET", f"/api/switches/{switch_id}")
        if status == 200:
            return body
        elif status == 404:
            raise ValueError(f"스위치 {switch_id} 없음")
        elif status == 401:
            raise PermissionError("인증 필요")
        else:
            raise RuntimeError(f"오류: {status}")

    def update_port(self, switch_id: str, port: int, enabled: bool):
        status, body = self.request(
            "PATCH",
            f"/api/switches/{switch_id}/ports/{port}",
            body={"enabled": enabled}
        )
        return status == 200


# TLS 인증서 정보 확인
def check_tls_cert(host: str, port: int = 443):
    import ssl
    ctx = ssl.create_default_context()
    with ctx.wrap_socket(
        __import__("socket").socket(), server_hostname=host
    ) as s:
        s.connect((host, port))
        cert = s.getpeercert()
        print(f"[TLS] 발급 대상: {cert.get('subject')}")
        print(f"[TLS] 발급 기관: {cert.get('issuer')}")
        print(f"[TLS] 만료일: {cert.get('notAfter')}")
        print(f"[TLS] TLS 버전: {s.version()}")
```

---

## 면접 예상 질문

- Q: HTTP와 HTTPS의 차이는?
  A: HTTP는 평문 전송으로 도청/변조 가능. HTTPS는 TLS를 통해 암호화, 서버 인증, 무결성 검증을 제공. TCP 3-way handshake 후 TLS handshake를 추가로 거침.

- Q: TLS Handshake 과정을 설명하라.
  A: ClientHello(지원 알고리즘 목록) → ServerHello(선택된 알고리즘) + Certificate(서버 인증서) → 클라이언트가 CA로 인증서 검증 → Pre-Master Secret을 서버 공개키로 암호화 전송 → 양측 동일한 Session Key 생성 → 이후 대칭 암호화로 통신.

- Q: 대칭키와 비대칭키를 둘 다 쓰는 이유는?
  A: 비대칭키(공개키/개인키)는 안전하지만 느림. 대칭키는 빠르지만 키 교환이 위험. TLS는 비대칭키로 안전하게 Session Key(대칭키)를 교환하고, 실제 데이터는 대칭키로 암호화해 속도와 보안을 모두 확보.

- Q: HTTPS인데 왜 중간자 공격이 가능한가?
  A: 클라이언트가 인증서 검증을 무시하거나, 공격자가 신뢰할 수 있는 CA 인증서를 가진 경우. 기업 내부망에서 SSL Inspection 장비가 이 원리로 동작함. 대응: 인증서 핀닝(Certificate Pinning).

- Q: HTTP/1.1에서 Keep-Alive란?
  A: HTTP는 기본적으로 요청마다 TCP 연결을 새로 맺음. Keep-Alive는 하나의 TCP 연결을 유지하며 여러 요청을 처리. 3-way handshake 반복 오버헤드 감소.

---

## 관련 개념

- [01-05 TCP 3-way / 4-way Handshake](./01-05-tcp-handshake.md) — HTTPS의 기반 TCP 연결
- [01-08 HTTP 버전](./01-08-http-versions.md) — HTTP/1.1 → HTTP/2 → HTTP/3 발전
- [01-09 쿠키 / 세션 / JWT](./01-09-cookie-session-jwt.md) — HTTP 위의 인증 메커니즘
