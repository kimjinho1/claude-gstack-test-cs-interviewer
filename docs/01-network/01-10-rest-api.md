# 01-10 REST API 설계 원칙

## 개념

**REST (Representational State Transfer)** : HTTP를 잘 활용하기 위한 아키텍처 스타일.
Roy Fielding이 2000년 논문에서 정의. 6가지 제약 조건을 만족하면 RESTful.

---

## 6가지 제약 조건

| 제약 | 설명 |
|------|------|
| Stateless | 서버는 클라이언트 상태 저장 안 함. 요청에 필요한 정보 모두 포함 |
| Client-Server | 클라이언트와 서버 역할 분리 |
| Cacheable | 응답에 캐시 가능 여부 명시 |
| Uniform Interface | 일관된 인터페이스 (URI, HTTP 메서드 규칙) |
| Layered System | 클라이언트는 중간 레이어(프록시, 로드밸런서) 존재를 몰라도 됨 |
| Code on Demand | 서버가 클라이언트에 코드 전송 가능 (선택 사항) |

실무에서 핵심은 **Stateless + Uniform Interface**.

---

## 동작 원리

### URI 설계 규칙

**리소스는 명사, 행위는 HTTP 메서드로 표현**

```
나쁜 예 (동사 URI):
GET  /getSwitch?id=1
POST /createSwitch
POST /deleteSwitch/1
POST /updateSwitchPort

좋은 예 (명사 URI + HTTP 메서드):
GET    /switches/1        스위치 조회
POST   /switches          스위치 생성
PUT    /switches/1        스위치 전체 수정
PATCH  /switches/1        스위치 일부 수정
DELETE /switches/1        스위치 삭제
```

**계층 구조 표현**

```
GET  /switches                      모든 스위치 목록
GET  /switches/{id}                 특정 스위치
GET  /switches/{id}/ports           특정 스위치의 모든 포트
GET  /switches/{id}/ports/{port_id} 특정 포트
PUT  /switches/{id}/ports/{port_id} 특정 포트 수정
```

**URI 규칙**

```
✓ 소문자 사용          /network-devices
✓ 복수형 명사          /switches (not /switch)
✓ 하이픈(-)으로 구분   /access-points
✗ 언더스코어(_) 금지   /access_points
✗ 확장자 금지          /switches.json
✗ 끝에 슬래시 금지     /switches/
```

### HTTP 메서드와 멱등성

| 메서드 | 역할 | 멱등성 | 안전성 |
|--------|------|-------|--------|
| GET | 조회 | ✓ | ✓ |
| POST | 생성 | ✗ | ✗ |
| PUT | 전체 수정 | ✓ | ✗ |
| PATCH | 부분 수정 | ✗ | ✗ |
| DELETE | 삭제 | ✓ | ✗ |

- **멱등성**: 같은 요청을 여러 번 보내도 결과 동일 (PUT /switches/1을 10번 → 항상 같은 결과)
- **안전성**: 서버 상태를 변경하지 않음 (GET은 조회만)

### 응답 상태 코드 규칙

```
GET    /switches/1    → 200 OK
POST   /switches      → 201 Created  (Location: /switches/42 헤더 포함)
PUT    /switches/1    → 200 OK
DELETE /switches/1    → 204 No Content
GET    /switches/999  → 404 Not Found
POST   /switches (잘못된 body) → 400 Bad Request
인증 없음             → 401 Unauthorized
권한 없음             → 403 Forbidden
```

### 버전 관리

```
URI 버전:    /api/v1/switches  (가장 흔함)
헤더 버전:   Accept: application/vnd.api+json;version=1
쿼리 버전:   /switches?version=1
```

### HATEOAS (선택적)

응답에 관련 링크를 포함해 클라이언트가 API를 탐색할 수 있게 함.

```json
{
  "id": 1,
  "name": "SW-CORE-01",
  "links": [
    {"rel": "self",  "href": "/switches/1"},
    {"rel": "ports", "href": "/switches/1/ports"},
    {"rel": "vlans", "href": "/switches/1/vlans"}
  ]
}
```

실무에서는 구현 비용 대비 효용이 낮아 생략하는 경우 많음.

---

## 스위치/AP 관리 API 설계 예시

```
# 스위치 관리
GET    /api/v1/switches                  스위치 목록
POST   /api/v1/switches                  스위치 등록
GET    /api/v1/switches/{id}             스위치 상세
PATCH  /api/v1/switches/{id}             스위치 정보 수정
DELETE /api/v1/switches/{id}             스위치 삭제

# 포트 관리
GET    /api/v1/switches/{id}/ports       포트 목록
PATCH  /api/v1/switches/{id}/ports/{no} 포트 설정 변경
                                         body: {"enabled": false, "vlan": 10}

# AP 관리
GET    /api/v1/access-points             AP 목록
GET    /api/v1/access-points/{id}        AP 상세
PATCH  /api/v1/access-points/{id}        AP 설정 변경

# AP ↔ 스위치 연결 관계
GET    /api/v1/switches/{id}/access-points   스위치에 연결된 AP 목록
```

---

## 예시 코드 (Python)

```python
from flask import Flask, jsonify, request
from http import HTTPStatus

app = Flask(__name__)

# 인메모리 DB
switches = {
    1: {"id": 1, "name": "SW-CORE-01", "ip": "192.168.99.1", "ports": 48},
    2: {"id": 2, "name": "SW-EDGE-01", "ip": "192.168.99.2", "ports": 24},
}

# ── 스위치 목록 조회 ──────────────────────────────────
@app.get("/api/v1/switches")
def list_switches():
    return jsonify(list(switches.values())), HTTPStatus.OK


# ── 스위치 상세 조회 ──────────────────────────────────
@app.get("/api/v1/switches/<int:switch_id>")
def get_switch(switch_id: int):
    sw = switches.get(switch_id)
    if not sw:
        return jsonify({"error": "스위치 없음"}), HTTPStatus.NOT_FOUND
    return jsonify(sw), HTTPStatus.OK


# ── 스위치 생성 ───────────────────────────────────────
@app.post("/api/v1/switches")
def create_switch():
    body = request.get_json()
    if not body or "name" not in body or "ip" not in body:
        return jsonify({"error": "name, ip 필수"}), HTTPStatus.BAD_REQUEST

    new_id = max(switches.keys()) + 1
    sw = {"id": new_id, **body}
    switches[new_id] = sw

    response = jsonify(sw)
    response.headers["Location"] = f"/api/v1/switches/{new_id}"
    return response, HTTPStatus.CREATED  # 201


# ── 스위치 부분 수정 (PATCH) ──────────────────────────
@app.patch("/api/v1/switches/<int:switch_id>")
def update_switch(switch_id: int):
    sw = switches.get(switch_id)
    if not sw:
        return jsonify({"error": "스위치 없음"}), HTTPStatus.NOT_FOUND

    body = request.get_json() or {}
    # id는 수정 불가
    for key, value in body.items():
        if key != "id":
            sw[key] = value

    return jsonify(sw), HTTPStatus.OK


# ── 스위치 삭제 ───────────────────────────────────────
@app.delete("/api/v1/switches/<int:switch_id>")
def delete_switch(switch_id: int):
    if switch_id not in switches:
        return jsonify({"error": "스위치 없음"}), HTTPStatus.NOT_FOUND

    del switches[switch_id]
    return "", HTTPStatus.NO_CONTENT  # 204 (body 없음)


# ── 에러 핸들러 ───────────────────────────────────────
@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({"error": "허용되지 않는 메서드"}), 405


if __name__ == "__main__":
    app.run(debug=True)
```

---

## 면접 예상 질문

- Q: REST의 Stateless 제약이란?
  A: 서버가 클라이언트의 상태를 저장하지 않음. 각 요청은 처리에 필요한 모든 정보를 포함해야 함. 덕분에 서버 확장이 쉬움(어떤 서버도 요청 처리 가능). 반면 요청마다 인증 정보를 포함해야 하는 오버헤드 있음.

- Q: PUT과 PATCH의 차이는?
  A: PUT은 리소스 전체를 교체 (보내지 않은 필드는 null/기본값). PATCH는 보낸 필드만 수정. 예를 들어 스위치의 이름만 바꾸고 싶으면 PATCH가 적합. PUT으로 이름만 보내면 나머지 필드가 초기화될 수 있음.

- Q: POST와 PUT의 멱등성 차이는?
  A: PUT은 멱등성 있음. 같은 PUT 요청을 여러 번 보내도 결과 동일. POST는 멱등성 없음. POST /switches를 여러 번 보내면 스위치가 여러 개 생성됨.

- Q: REST API에서 동사를 URI에 쓰면 안 되는 이유는?
  A: HTTP 메서드(GET, POST, PUT, DELETE)가 이미 행위를 표현함. URI에 동사를 쓰면 메서드와 중복되고 일관성이 깨짐. /deleteSwitch/1보다 DELETE /switches/1이 더 직관적이고 HTTP 시맨틱에 맞음.

- Q: 204 No Content를 DELETE 응답으로 쓰는 이유는?
  A: 삭제 성공 시 반환할 body가 없기 때문. 200 OK는 body를 포함하는 성공 응답. 204는 요청은 성공했지만 반환할 내용이 없음을 명시. HTTP 시맨틱에 더 정확히 부합.

---

## 관련 개념

- [01-07 HTTP vs HTTPS](./01-07-http-https.md) — REST의 기반 프로토콜
- [01-09 쿠키 / 세션 / JWT](./01-09-cookie-session-jwt.md) — REST API 인증
- [01-11 웹소켓 vs HTTP](./01-11-websocket.md) — REST로 못 하는 실시간 통신
