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
  │   (지원 TLS 버전, 암호화 알고리즘 목록,  │
  │    Client Random, Session ID)       │
  │                                    │
  │◀── ServerHello ───────────────────│
  │   (선택된 TLS 버전, 암호화 알고리즘,    │
  │    Server Random, Session ID)       │
  │                                    │
  │◀── Certificate ───────────────────│
  │   (서버 인증서 체인: Leaf→중간CA→Root)  │
  │                                    │
  │◀── ServerHelloDone ───────────────│
  │                                    │
  │── 인증서 검증 (아래 상세 설명) ─────────│
  │                                    │
  │── ClientKeyExchange ──────────────▶│
  │   (Pre-Master Secret, 서버 공개키로   │
  │    RSA 암호화 또는 ECDH 키 교환)       │
  │                                    │
  │  양측 동일한 Master Secret 생성        │
  │  → Session Key (대칭키) 유도          │
  │                                    │
  │── ChangeCipherSpec ───────────────▶│
  │── Finished (MAC 검증) ────────────▶│
  │◀── ChangeCipherSpec ───────────────│
  │◀── Finished (MAC 검증) ────────────│
  │                                    │
  │       암호화 통신 시작 (HTTP)          │
```

---

### 인증서 구조와 검증 과정

#### 1. 인증서 체인 (Certificate Chain)

서버 인증서는 단독으로 신뢰되지 않고, **Root CA까지 이어지는 신뢰 체인**을 통해 검증됨.

```
신뢰 체인:
  Root CA (최상위, 브라우저/OS에 내장)
    └── Intermediate CA (중간 인증 기관)
          └── Leaf Certificate (서버 인증서, 예: *.nms.local)

서버는 TLS Handshake에서 Leaf + Intermediate 인증서를 전송.
브라우저는 Root CA 인증서를 로컬에 보유 (신뢰 앵커).

왜 중간 CA를 두는가:
  Root CA의 개인키가 유출되면 전 세계 인증서 신뢰 붕괴.
  Root CA는 오프라인/에어갭으로 극도로 보호.
  중간 CA를 통해 실제 서명 작업을 격리.
```

#### 2. 인증서 필드

```
X.509 인증서 주요 필드:
  Subject:     CN=*.nms.local, O=My Company, C=KR
  Issuer:      CN=DigiCert TLS RSA SHA256 2020 CA1 (중간 CA)
  Serial:      0A:1B:2C:3D:...
  Validity:    Not Before: 2025-01-01
               Not After:  2026-01-01
  Public Key:  RSA 2048bit 또는 ECDSA P-256
  SAN:         DNS:nms.local, DNS:*.nms.local, IP:192.168.1.1
               (Subject Alternative Name — 유효한 도메인/IP 목록)
  Signature:   중간 CA의 개인키로 서명한 값
  Extensions:
    Key Usage: Digital Signature, Key Encipherment
    Extended Key Usage: TLS Web Server Authentication
    CRL Distribution Points: http://crl.digicert.com/...
    OCSP: http://ocsp.digicert.com
```

#### 3. 브라우저의 인증서 검증 단계

```
① 체인 구성
   Leaf → Intermediate CA → Root CA 체인 연결
   Root CA가 로컬 신뢰 저장소에 있는지 확인

② 서명 검증 (각 단계별)
   Intermediate CA의 공개키로 Leaf 서명 검증
   Root CA의 공개키로 Intermediate CA 서명 검증
   Root CA는 자기 자신을 서명 (Self-Signed, 신뢰 앵커)

③ 유효 기간 확인
   현재 시각이 Not Before ~ Not After 범위 내인지

④ 도메인/IP 일치 확인 (Hostname Verification)
   요청한 호스트가 SAN(Subject Alternative Name) 목록에 있는지
   *.nms.local → nms.local의 서브도메인 전체 허용
   IP:192.168.1.1 → IP 직접 접속도 가능

⑤ 폐기 확인 (Revocation Check)
   방법 1) CRL (Certificate Revocation List)
     CA가 주기적으로 폐기된 인증서 목록 발행 (파일 다운로드)
     단점: 파일 크기가 크고 갱신 주기 있음

   방법 2) OCSP (Online Certificate Status Protocol)
     실시간으로 CA 서버에 "이 인증서 유효한가?" 조회
     단점: CA 서버 응답 대기 → 지연 발생

   방법 3) OCSP Stapling (현재 표준)
     서버가 미리 OCSP 응답을 CA에서 받아 TLS Handshake에 포함
     브라우저가 CA 서버에 별도 요청 불필요 → 속도 향상

   모든 단계 통과 ────▶ 인증서 신뢰, 공개키 추출
   어느 단계라도 실패 ▶ 인증서 경고 / 연결 차단
```

#### 4. 키 교환과 세션 키 생성

```
TLS 1.2 (RSA 키 교환):
  ① 클라이언트가 난수(Pre-Master Secret) 생성
  ② 서버 공개키로 암호화해 전송
  ③ 서버가 개인키로 복호화
  ④ 양측 모두 동일한 Master Secret 계산:
     Master Secret = PRF(Pre-Master Secret, Client Random, Server Random)
  ⑤ Master Secret → Session Key (대칭키) 유도

  문제: 서버 개인키 유출 시 과거 모든 통신 복호화 가능 (Forward Secrecy 없음)

TLS 1.2 (ECDHE 키 교환, Forward Secrecy 있음):
  ① ECDH 임시 키 쌍 생성 (ephemeral)
  ② 공개 파라미터 교환 (ECDH 알고리즘으로 공유 비밀 계산)
  ③ 임시 키 사용 후 즉시 폐기 → 과거 세션 복호화 불가

Session Key 구조:
  Master Secret → 4개 키 유도
    Client Write Key (클→서 암호화)
    Server Write Key (서→클 암호화)
    Client MAC Key   (클→서 무결성)
    Server MAC Key   (서→클 무결성)
```

### TLS 1.2 vs TLS 1.3

| 구분 | TLS 1.2 | TLS 1.3 |
|------|---------|---------|
| 핸드셰이크 RTT | 2-RTT | 1-RTT (키 교환 첫 메시지에 포함) |
| 재연결 | 세션 재개 (1-RTT) | 0-RTT (이전 세션 PSK 재사용) |
| 키 교환 | RSA, ECDHE 모두 허용 | ECDHE, X25519만 허용 (Forward Secrecy 강제) |
| 취약 알고리즘 | RC4, MD5, SHA-1 일부 허용 | 완전 제거 |
| 인증서 암호화 | 평문 전송 | Encrypted Extensions로 암호화 |
| 0-RTT 위험 | - | Replay Attack 가능 (GET만 허용 권장) |

```
TLS 1.3 핸드셰이크 (1-RTT):
Client                          Server
  │── ClientHello ─────────────▶│
  │   + Key Share (ECDH 파라미터) │  ← 키 교환 정보 첫 메시지에 포함
  │                               │
  │◀── ServerHello ───────────── │
  │◀── {EncryptedExtensions} ────│  ← 인증서도 암호화됨
  │◀── {Certificate} ────────────│
  │◀── {CertificateVerify} ──────│
  │◀── {Finished} ───────────────│
  │                               │
  │── {Finished} ────────────────▶│
  │                               │
  │   암호화 통신 시작               │
```

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
  A: ClientHello(지원 알고리즘 목록, Client Random) → ServerHello(선택 알고리즘, Server Random) + Certificate(인증서 체인) → 클라이언트가 인증서 검증(체인, 서명, 유효기간, 도메인, 폐기 확인) → Pre-Master Secret을 서버 공개키로 암호화 전송(또는 ECDHE 교환) → 양측 Master Secret → Session Key 유도 → Finished로 핸드셰이크 검증 → 대칭 암호화 통신.

- Q: 브라우저는 서버 인증서를 어떻게 검증하나?
  A: 5단계로 검증. ① 인증서 체인 구성(Leaf→중간CA→Root CA) ② 각 단계 서명 검증(상위 CA 공개키로 하위 인증서 서명 확인) ③ 유효 기간 확인 ④ 도메인 일치 확인(SAN 필드) ⑤ 폐기 확인(CRL 또는 OCSP). OCSP Stapling은 서버가 미리 OCSP 응답을 받아 핸드셰이크에 포함시켜 브라우저가 CA에 별도 요청하지 않아도 되게 함.

- Q: 인증서 체인(Certificate Chain)이란?
  A: 서버 인증서(Leaf) → 중간 CA → Root CA로 이어지는 신뢰 체인. Root CA는 브라우저/OS에 내장되어 신뢰 앵커 역할. 서버는 Leaf와 중간 CA 인증서를 핸드셰이크 시 전송하고, 브라우저는 로컬의 Root CA 인증서로 최종 검증. 중간 CA를 두는 이유는 Root CA 개인키를 오프라인으로 격리 보호하기 위함.

- Q: Forward Secrecy(전방 비밀성)란?
  A: 서버 개인키가 유출되더라도 과거 통신 내용을 복호화하지 못하게 하는 속성. ECDHE는 임시 키 쌍을 매 세션마다 새로 생성하고 사용 후 즉시 폐기해 Forward Secrecy를 제공. RSA 키 교환은 서버 개인키로 직접 Pre-Master Secret을 복호화하므로 과거 세션 복호화 가능. TLS 1.3은 ECDHE를 강제해 Forward Secrecy 보장.

- Q: 대칭키와 비대칭키를 둘 다 쓰는 이유는?
  A: 비대칭키(공개키/개인키)는 안전하지만 느림. 대칭키는 빠르지만 키 교환이 위험. TLS는 비대칭키(또는 ECDHE)로 안전하게 Session Key(대칭키)를 교환하고, 실제 데이터는 대칭키(AES-GCM 등)로 암호화해 속도와 보안을 모두 확보.

- Q: HTTPS인데 왜 중간자 공격이 가능한가?
  A: 클라이언트가 인증서 검증을 무시하거나, 공격자가 신뢰 저장소에 있는 CA 인증서를 보유한 경우. 기업 내부망에서 SSL Inspection(DPI) 장비가 이 원리로 동작 — 루트 CA 인증서를 단말에 설치해 중간에서 복호화/재암호화. 대응: 인증서 핀닝(Certificate Pinning) — 앱에 특정 인증서/공개키 해시를 하드코딩해 다른 인증서 거부.

- Q: OCSP Stapling이란?
  A: 인증서 폐기 확인 방법. 일반 OCSP는 브라우저가 CA 서버에 실시간 조회해 지연 발생. OCSP Stapling은 서버가 주기적으로 CA에서 서명된 OCSP 응답을 받아서 TLS 핸드셰이크 때 클라이언트에게 함께 전달. 브라우저가 CA에 별도 요청 불필요, 속도 향상 및 프라이버시 보호.

- Q: HTTP/1.1에서 Keep-Alive란?
  A: HTTP는 기본적으로 요청마다 TCP 연결을 새로 맺음. Keep-Alive는 하나의 TCP 연결을 유지하며 여러 요청을 처리. 3-way handshake + TLS handshake 반복 오버헤드 감소.

---

## 관련 개념

- [01-05 TCP 3-way / 4-way Handshake](./01-05-tcp-handshake.md) — HTTPS의 기반 TCP 연결
- [01-08 HTTP 버전](./01-08-http-versions.md) — HTTP/1.1 → HTTP/2 → HTTP/3 발전
- [01-09 쿠키 / 세션 / JWT](./01-09-cookie-session-jwt.md) — HTTP 위의 인증 메커니즘
