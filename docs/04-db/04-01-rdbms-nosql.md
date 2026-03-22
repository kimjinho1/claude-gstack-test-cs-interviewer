# 04-01 RDBMS vs NoSQL

## 개념

**RDBMS(관계형 DB)**: 테이블 + 외래키로 데이터 관계를 표현. 스키마 고정, ACID 보장.
**NoSQL**: 비관계형 DB. 스키마 유연, 수평 확장 용이, CAP 트레이드오프.

---

## 동작 원리

### RDBMS 핵심 특성

```
스키마 (Schema):
  - 테이블 구조를 미리 정의 (컬럼, 타입, 제약)
  - 데이터 일관성 강제
  - 변경 시 ALTER TABLE → 운영 중 스키마 변경 비용 큼

관계 (Relation):
  - 외래키 (Foreign Key)로 테이블 간 관계 정의
  - 조인(JOIN)으로 관련 데이터 한 번에 조회
  - 정규화로 중복 제거

ACID 보장:
  - Atomicity: 트랜잭션 전체 성공/실패
  - Consistency: 무결성 제약 항상 유지
  - Isolation: 동시 트랜잭션 간섭 없음
  - Durability: 커밋된 데이터 영구 보존
```

### NoSQL 유형

```
Key-Value:
  - 구조: { key: value }
  - 조회: O(1) 해시맵
  - 예: Redis, DynamoDB
  - 용도: 세션, 캐시, 실시간 카운터

Document:
  - 구조: JSON/BSON 문서
  - 유연한 스키마, 중첩 가능
  - 예: MongoDB, CouchDB
  - 용도: 카탈로그, CMS, 이벤트 로그

Column-Family:
  - 구조: 행 키 + 컬럼 패밀리
  - 넓은 테이블, 희소 데이터 효율적
  - 예: Cassandra, HBase
  - 용도: 시계열, IoT 센서 데이터, 로그

Graph:
  - 구조: 노드 + 엣지
  - 관계 탐색 최적화
  - 예: Neo4j
  - 용도: SNS 관계, 추천, 경로 탐색
```

### CAP 정리

분산 시스템은 CAP 중 2개만 선택 가능.

```
C (Consistency):   모든 노드가 동일한 데이터 반환
A (Availability):  모든 요청에 응답 (오류 없음)
P (Partition):     네트워크 분리 상황에서도 동작

CP (일관성 + 분산): 네트워크 장애 시 가용성 포기 — HBase, MongoDB (설정에 따라)
AP (가용성 + 분산): 네트워크 장애 시 오래된 데이터 반환 가능 — Cassandra, DynamoDB
CA (일관성 + 가용성): 실제 분산 시스템에서는 불가 → 단일 서버 RDBMS

현실:
  네트워크 파티션(P)은 피할 수 없음
  → 결국 C와 A의 트레이드오프 선택
```

### 언제 무엇을 쓰나

```
RDBMS 선택:
  - 금융, 결제: 정확한 잔액 계산 → ACID 필수
  - 복잡한 관계: JOIN 많은 경우
  - 데이터 일관성 최우선

NoSQL 선택:
  - 대용량 로그/이벤트: 쓰기 속도 중요 → Cassandra
  - 세션/캐시: 빠른 조회 → Redis
  - 유연한 스키마: 서비스 초기, 필드 변경 잦을 때 → MongoDB
  - 수평 확장: 트래픽 폭발적 증가 예상

네트워크 장비 관제 시스템 예:
  RDBMS: 장비 자산 정보, 설정 이력, 담당자
  Redis:  실시간 상태 캐시 (포트 up/down)
  InfluxDB/Cassandra: SNMP 폴링 시계열 데이터 (5분마다 수천 장비)
```

---

## 예시 코드 (Python)

```python
import sqlite3
import json
from typing import Optional


# ── RDBMS: SQLite 예시 ───────────────────────────────

def rdbms_demo():
    """관계형 DB: 장비 관리 시스템"""
    conn = sqlite3.connect(":memory:")
    cur  = conn.cursor()

    # 스키마 정의 (테이블 + 외래키)
    cur.executescript("""
        CREATE TABLE devices (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname VARCHAR(64) UNIQUE NOT NULL,
            ip      VARCHAR(15) NOT NULL,
            type    VARCHAR(20)   -- 'switch' | 'router' | 'ap'
        );

        CREATE TABLE interfaces (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER NOT NULL,
            name      VARCHAR(20),
            status    VARCHAR(10) DEFAULT 'up',
            vlan_id   INTEGER,
            FOREIGN KEY (device_id) REFERENCES devices(id)
        );
    """)

    # 데이터 삽입
    cur.execute("INSERT INTO devices (hostname, ip, type) VALUES (?, ?, ?)",
                ("sw-core-01", "10.0.0.1", "switch"))
    dev_id = cur.lastrowid
    interfaces = [
        (dev_id, "Gi0/0", "up",   10),
        (dev_id, "Gi0/1", "down", 20),
        (dev_id, "Gi0/2", "up",   10),
    ]
    cur.executemany(
        "INSERT INTO interfaces (device_id, name, status, vlan_id) VALUES (?,?,?,?)",
        interfaces
    )
    conn.commit()

    # JOIN 조회
    print("[RDBMS] 장비 + 인터페이스 JOIN:")
    cur.execute("""
        SELECT d.hostname, i.name, i.status, i.vlan_id
        FROM devices d
        JOIN interfaces i ON d.id = i.device_id
        ORDER BY d.hostname, i.name
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:15s} {row[1]:8s} {row[2]:5s} VLAN={row[3]}")

    # 집계
    cur.execute("""
        SELECT status, COUNT(*) as cnt
        FROM interfaces WHERE device_id = ?
        GROUP BY status
    """, (dev_id,))
    print("\n[RDBMS] 포트 상태 집계:")
    for status, cnt in cur.fetchall():
        print(f"  {status}: {cnt}개")

    conn.close()


# ── NoSQL: Document DB 시뮬레이션 (Python dict) ───────

class SimpleDocumentDB:
    """MongoDB 스타일 Document DB 시뮬레이션"""

    def __init__(self):
        self._store: dict[str, dict] = {}
        self._next_id = 1

    def insert(self, collection: str, doc: dict) -> str:
        oid = f"{collection}_{self._next_id}"
        self._next_id += 1
        doc["_id"] = oid
        self._store[oid] = doc
        return oid

    def find(self, collection: str, query: dict) -> list[dict]:
        results = []
        for oid, doc in self._store.items():
            if not oid.startswith(collection + "_"):
                continue
            if all(doc.get(k) == v for k, v in query.items()):
                results.append(doc)
        return results

    def find_one(self, collection: str, query: dict) -> Optional[dict]:
        results = self.find(collection, query)
        return results[0] if results else None


def nosql_demo():
    """NoSQL Document DB: 유연한 스키마"""
    db = SimpleDocumentDB()

    # 유연한 스키마 — 각 문서가 다른 필드를 가질 수 있음
    db.insert("devices", {
        "hostname": "sw-core-01",
        "ip": "10.0.0.1",
        "type": "switch",
        "interfaces": [        # 중첩 배열 — RDBMS라면 별도 테이블
            {"name": "Gi0/0", "status": "up",   "vlan": 10},
            {"name": "Gi0/1", "status": "down", "vlan": 20},
        ],
        "vendor_info": {"brand": "Cisco", "model": "C9300"},  # 선택적 필드
    })
    db.insert("devices", {
        "hostname": "ap-floor2-01",
        "ip": "10.0.1.1",
        "type": "ap",
        "ssid_list": ["corp-wifi", "guest"],   # AP만 가지는 필드
        "channel": 6,
    })

    # 쿼리
    switches = db.find("devices", {"type": "switch"})
    print("\n[NoSQL] 스위치 장비:")
    for dev in switches:
        iface_cnt = len(dev.get("interfaces", []))
        print(f"  {dev['hostname']} ({dev['ip']}) — 인터페이스 {iface_cnt}개")
        for iface in dev.get("interfaces", []):
            print(f"    {iface['name']}: {iface['status']} VLAN={iface['vlan']}")


# ── Key-Value: Redis 패턴 시뮬레이션 ────────────────

class SimpleRedis:
    """Redis 핵심 패턴 시뮬레이션"""

    def __init__(self):
        self._kv: dict = {}
        self._ttl: dict = {}
        import time
        self._time = time.time

    def set(self, key: str, value, ttl: Optional[int] = None):
        self._kv[key] = value
        if ttl:
            self._ttl[key] = self._time() + ttl

    def get(self, key: str):
        if key in self._ttl and self._time() > self._ttl[key]:
            del self._kv[key]; del self._ttl[key]
            return None
        return self._kv.get(key)

    def incr(self, key: str) -> int:
        val = int(self._kv.get(key, 0)) + 1
        self._kv[key] = val
        return val

    def hset(self, key: str, field: str, value):
        if key not in self._kv:
            self._kv[key] = {}
        self._kv[key][field] = value

    def hgetall(self, key: str) -> dict:
        return dict(self._kv.get(key, {}))


def kv_demo():
    redis = SimpleRedis()

    # 세션 캐싱 (TTL 설정)
    redis.set("session:abc123", {"user": "admin", "role": "network-engineer"}, ttl=3600)
    print(f"\n[Redis] 세션: {redis.get('session:abc123')}")

    # 실시간 카운터
    for _ in range(5):
        redis.incr("snmp:poll:count")
    print(f"[Redis] SNMP 폴링 횟수: {redis.get('snmp:poll:count')}")

    # 해시 — 장비 상태 캐시
    redis.hset("device:sw-core-01", "cpu_util", "45%")
    redis.hset("device:sw-core-01", "mem_util", "60%")
    redis.hset("device:sw-core-01", "uptime",   "30d")
    print(f"[Redis] 장비 상태: {redis.hgetall('device:sw-core-01')}")


# ── 실행 ─────────────────────────────────────────────

print("=== RDBMS (SQLite) ===")
rdbms_demo()

print("\n=== NoSQL (Document DB) ===")
nosql_demo()

kv_demo()
```

---

## 면접 예상 질문

- Q: RDBMS와 NoSQL의 차이는?
  A: RDBMS는 스키마 고정, 테이블-관계 모델, ACID 보장. 복잡한 JOIN과 정확한 데이터 일관성 필요한 금융/결제에 적합. NoSQL은 스키마 유연, 수평 확장 용이, CAP의 A/P를 우선. 대용량 로그, 캐시, 유연한 문서 구조에 적합. 둘 중 하나가 낫다기보다 목적에 맞게 선택.

- Q: CAP 정리란?
  A: 분산 시스템은 Consistency(일관성), Availability(가용성), Partition Tolerance(분산 허용) 중 동시에 2개만 만족. 실제 네트워크 파티션은 피할 수 없으므로 CP(일관성 우선, MongoDB/HBase) vs AP(가용성 우선, Cassandra/DynamoDB) 중 선택.

- Q: 언제 NoSQL을 선택하나?
  A: ① 스키마가 자주 바뀌거나 필드가 불규칙한 경우 (Document DB). ② 초당 수만 건 쓰기 + 수평 확장 필요한 시계열/로그 (Cassandra). ③ 밀리초 응답의 캐시/세션 (Redis). ④ 복잡한 JOIN이 거의 없고 단순 Key 조회가 대부분인 경우.

---

## 관련 개념

- [04-02 트랜잭션/ACID](./04-02-transaction-acid.md)
- [04-05 인덱스](./04-05-index.md)
- [04-09 Redis](./04-09-redis.md)
