# 04-09 Redis (캐시 전략, 자료구조)

## 개념

**Redis**: 메모리 기반 Key-Value 저장소. 캐시, 세션, 실시간 데이터, 메시지 큐에 사용.

```
특징:
  - 메모리 저장 → 마이크로초 응답 (MySQL 대비 100~1000x 빠름)
  - 단일 스레드 이벤트 루프 → Lock-Free, 원자적 연산
  - 다양한 자료구조 내장
  - 영속성: RDB(스냅샷) + AOF(로그) 옵션
```

---

## 동작 원리

### Redis 자료구조

```
String:   SET key value [EX seconds]
          → 세션, 카운터, 캐시

List:     LPUSH / RPUSH / LPOP / RPOP
          → 메시지 큐, 최근 N개 이벤트

Hash:     HSET key field value / HGETALL key
          → 객체 저장 (장비 상태 여러 필드)

Set:      SADD / SMEMBERS / SINTERSTORE
          → 고유 방문자, 태그

Sorted Set: ZADD key score member / ZRANGE
          → 랭킹, 우선순위 큐, 시계열

Bitmap:   SETBIT / GETBIT / BITCOUNT
          → 일별 접속 여부, 권한 비트

HyperLogLog: PFADD / PFCOUNT
          → 대략적 카디널리티 (메모리 12KB로 수십억 개 근사)
```

### 캐시 전략 (Cache Strategy)

```
Cache-Aside (Lazy Loading):
  1. 앱이 캐시 조회
  2. 없으면(Miss) DB 조회
  3. DB 결과를 캐시에 저장
  4. 결과 반환
  → 가장 일반적. 캐시와 DB 불일치 가능 (TTL로 관리)

Write-Through:
  1. DB에 쓰기
  2. 즉시 캐시에도 쓰기
  → 항상 캐시 최신화. 쓰기 지연 증가

Write-Back (Write-Behind):
  1. 캐시에만 쓰기
  2. 비동기로 DB에 플러시
  → 쓰기 성능 최고. 캐시 장애 시 데이터 손실 위험

Read-Through:
  캐시가 DB 읽기를 직접 처리 (앱이 캐시만 바라봄)
  → Redis + DB 연동 미들웨어 필요

Cache Stampede (캐시 스탬피드):
  인기 캐시 만료 순간 대량 DB 요청 폭주
  해결: ① Mutex Lock (한 스레드만 DB 조회)
        ② Probabilistic Early Expiration (만료 직전 확률적 갱신)
        ③ 긴 TTL + 백그라운드 갱신
```

### 메모리 정책 (Eviction Policy)

```
maxmemory 도달 시 어떤 키를 삭제할지:

noeviction:     삭제 안 함, OOM 오류 반환
allkeys-lru:    전체 키에서 LRU 삭제 (캐시 용도 일반적)
volatile-lru:   TTL 있는 키에서 LRU 삭제
allkeys-lfu:    전체 키에서 LFU (최소 사용 빈도)
allkeys-random: 무작위 삭제
volatile-ttl:   TTL 가장 짧은 키 삭제

설정: maxmemory-policy allkeys-lru
```

---

## 예시 코드 (Python)

```python
import time
import json
import threading
from typing import Optional, Any
from collections import OrderedDict


# ── Redis 핵심 기능 시뮬레이션 ────────────────────────

class MockRedis:
    """Redis 주요 자료구조 및 동작 시뮬레이션"""

    def __init__(self, max_memory_keys: int = 1000,
                 eviction: str = "allkeys-lru"):
        self._strings:      dict = {}
        self._hashes:       dict = {}
        self._lists:        dict = {}
        self._sets:         dict = {}
        self._sorted_sets:  dict = {}  # {key: {member: score}}
        self._ttl:          dict = {}
        self._max_keys    = max_memory_keys
        self._eviction    = eviction
        self._access_time: dict = {}  # LRU 추적
        self._access_count: dict = {}  # LFU 추적
        self._t = time.time

    def _is_expired(self, key: str) -> bool:
        if key in self._ttl and self._t() > self._ttl[key]:
            self._delete_key(key)
            return True
        return False

    def _touch(self, key: str):
        self._access_time[key]  = self._t()
        self._access_count[key] = self._access_count.get(key, 0) + 1

    def _delete_key(self, key: str):
        for store in [self._strings, self._hashes, self._lists,
                      self._sets, self._sorted_sets]:
            store.pop(key, None)
        self._ttl.pop(key, None)
        self._access_time.pop(key, None)

    def _maybe_evict(self):
        total_keys = sum(len(s) for s in [self._strings, self._hashes,
                                           self._lists, self._sets])
        if total_keys < self._max_keys:
            return
        # LRU: 가장 오래 전에 접근한 키 삭제
        if self._access_time:
            oldest = min(self._access_time, key=self._access_time.get)
            self._delete_key(oldest)

    # ── String 명령 ──────────────────────────────────

    def set(self, key: str, value: Any, ex: Optional[int] = None,
            nx: bool = False) -> bool:
        """SET key value [EX seconds] [NX]"""
        if nx and key in self._strings and not self._is_expired(key):
            return False   # NX: 키 없을 때만
        self._maybe_evict()
        self._strings[key] = value
        if ex:
            self._ttl[key] = self._t() + ex
        self._touch(key)
        return True

    def get(self, key: str) -> Optional[Any]:
        if self._is_expired(key):
            return None
        val = self._strings.get(key)
        if val is not None:
            self._touch(key)
        return val

    def incr(self, key: str) -> int:
        val = int(self._strings.get(key, 0)) + 1
        self._strings[key] = val
        self._touch(key)
        return val

    def expire(self, key: str, seconds: int):
        self._ttl[key] = self._t() + seconds

    def ttl(self, key: str) -> int:
        if key not in self._ttl:
            return -1
        remaining = int(self._ttl[key] - self._t())
        return remaining if remaining > 0 else -2

    # ── Hash 명령 ────────────────────────────────────

    def hset(self, key: str, **fields):
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key].update(fields)
        self._touch(key)

    def hget(self, key: str, field: str) -> Optional[Any]:
        if self._is_expired(key):
            return None
        self._touch(key)
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key: str) -> dict:
        if self._is_expired(key):
            return {}
        self._touch(key)
        return dict(self._hashes.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int) -> int:
        if key not in self._hashes:
            self._hashes[key] = {}
        val = int(self._hashes[key].get(field, 0)) + amount
        self._hashes[key][field] = val
        self._touch(key)
        return val

    # ── List 명령 ────────────────────────────────────

    def lpush(self, key: str, *values):
        if key not in self._lists:
            self._lists[key] = []
        for v in values:
            self._lists[key].insert(0, v)
        self._touch(key)

    def rpush(self, key: str, *values):
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        self._touch(key)

    def lpop(self, key: str) -> Optional[Any]:
        lst = self._lists.get(key, [])
        return lst.pop(0) if lst else None

    def lrange(self, key: str, start: int, end: int) -> list:
        lst = self._lists.get(key, [])
        end = len(lst) if end == -1 else end + 1
        return lst[start:end]

    def llen(self, key: str) -> int:
        return len(self._lists.get(key, []))

    # ── Sorted Set 명령 ──────────────────────────────

    def zadd(self, key: str, mapping: dict):
        """mapping = {member: score}"""
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}
        self._sorted_sets[key].update(mapping)
        self._touch(key)

    def zrange(self, key: str, start: int, end: int,
               withscores: bool = False) -> list:
        ss = self._sorted_sets.get(key, {})
        sorted_members = sorted(ss.items(), key=lambda x: x[1])
        end = len(sorted_members) if end == -1 else end + 1
        sliced = sorted_members[start:end]
        return [(m, s) for m, s in sliced] if withscores else [m for m, _ in sliced]

    def zrevrange(self, key: str, start: int, end: int,
                  withscores: bool = False) -> list:
        ss = self._sorted_sets.get(key, {})
        sorted_members = sorted(ss.items(), key=lambda x: -x[1])
        end = len(sorted_members) if end == -1 else end + 1
        sliced = sorted_members[start:end]
        return [(m, s) for m, s in sliced] if withscores else [m for m, _ in sliced]

    def zincrby(self, key: str, amount: float, member: str) -> float:
        if key not in self._sorted_sets:
            self._sorted_sets[key] = {}
        score = self._sorted_sets[key].get(member, 0) + amount
        self._sorted_sets[key][member] = score
        self._touch(key)
        return score


# ── Cache-Aside 패턴 ─────────────────────────────────

class DeviceStatusCache:
    """
    Cache-Aside 패턴으로 장비 상태 캐싱
    SNMP 폴링 결과를 Redis에 캐시, DB 부하 감소
    """

    def __init__(self, redis: MockRedis, ttl: int = 300):
        self.redis = redis
        self.ttl   = ttl
        self._db_calls = 0

    def _fetch_from_db(self, device_id: str) -> dict:
        """DB 조회 시뮬레이션 (느림)"""
        self._db_calls += 1
        time.sleep(0.001)   # DB 쿼리 지연
        return {
            "hostname": f"device-{device_id}",
            "cpu_util": "45%", "mem_util": "60%",
            "status": "up", "port_count": 48
        }

    def get_status(self, device_id: str) -> dict:
        cache_key = f"device:status:{device_id}"

        # 1. 캐시 조회
        cached = self.redis.hgetall(cache_key)
        if cached:
            return {"source": "cache", **cached}

        # 2. Cache Miss → DB 조회
        data = self._fetch_from_db(device_id)

        # 3. 캐시 저장 (TTL 5분)
        self.redis.hset(cache_key, **data)
        self.redis.expire(cache_key, self.ttl)

        return {"source": "db", **data}

    def invalidate(self, device_id: str):
        """장비 상태 변경 시 캐시 무효화"""
        cache_key = f"device:status:{device_id}"
        self.redis.hset(cache_key)   # 빈 해시로 덮어씀 (실제: DEL 명령)

    @property
    def db_calls(self) -> int:
        return self._db_calls


# ── 실시간 트래픽 카운터 (Sorted Set) ────────────────

def traffic_ranking_demo(redis: MockRedis):
    """네트워크 포트별 트래픽 실시간 랭킹"""
    ports = [f"Gi0/{i}" for i in range(8)]
    import random

    # SNMP 폴링 시뮬레이션 (트래픽 카운터 누적)
    for _ in range(10):
        for port in ports:
            traffic_mb = random.randint(10, 1000)
            redis.zincrby("traffic:ranking", traffic_mb, port)

    print("[트래픽 랭킹 Top 3]")
    top3 = redis.zrevrange("traffic:ranking", 0, 2, withscores=True)
    for rank, (port, traffic) in enumerate(top3, 1):
        print(f"  {rank}위: {port} — {traffic:.0f} MB")


# ── 세션 관리 ─────────────────────────────────────────

def session_demo(redis: MockRedis):
    """웹 세션 저장 (TTL 1시간)"""
    session_id = "sess_abc123"
    redis.hset(f"session:{session_id}",
               user="admin",
               role="network-engineer",
               login_at=str(time.time()))
    redis.expire(f"session:{session_id}", 3600)

    session = redis.hgetall(f"session:{session_id}")
    ttl_remaining = redis.ttl(f"session:{session_id}")
    print(f"[세션] {session}")
    print(f"  TTL 잔여: {ttl_remaining}초")


# ── 메시지 큐 (List) ─────────────────────────────────

def message_queue_demo(redis: MockRedis):
    """SNMP Trap 큐 — Producer/Consumer 패턴"""
    queue_key = "trap:queue"

    # Producer: Trap 이벤트 enqueue
    traps = [
        {"device": "sw-core-01", "type": "link-down", "port": "Gi0/1"},
        {"device": "sw-dist-01", "type": "temp-high", "value": 75},
        {"device": "ap-floor1",  "type": "client-assoc", "mac": "aa:bb:cc"},
    ]
    for trap in traps:
        redis.rpush(queue_key, json.dumps(trap))

    print(f"[메시지 큐] 큐 크기: {redis.llen(queue_key)}")

    # Consumer: Trap 처리
    print("  처리:")
    while redis.llen(queue_key) > 0:
        item = redis.lpop(queue_key)
        trap = json.loads(item)
        print(f"    Trap 처리: {trap}")


# ── 실행 ─────────────────────────────────────────────

redis = MockRedis()

print("=== Cache-Aside 패턴 ===")
cache = DeviceStatusCache(redis, ttl=300)

# 첫 번째 조회 — DB Miss
for dev_id in ["sw-001", "sw-002", "sw-001"]:   # sw-001은 두 번
    result = cache.get_status(dev_id)
    print(f"  {dev_id}: {result['source']} (cpu={result['cpu_util']})")

print(f"  DB 호출 횟수: {cache.db_calls} (sw-001 캐시 히트로 2회만)")

print("\n=== 트래픽 랭킹 ===")
traffic_ranking_demo(redis)

print("\n=== 세션 관리 ===")
session_demo(redis)

print("\n=== 메시지 큐 (SNMP Trap) ===")
message_queue_demo(redis)
```

---

## 면접 예상 질문

- Q: Redis가 빠른 이유는?
  A: ① 메모리 저장 — 디스크 I/O 없음. ② 단순한 자료구조 — 해시, 리스트 등 최적화된 연산. ③ 단일 스레드 이벤트 루프 — Lock 없는 원자적 연산. ④ I/O Multiplexing (epoll) — 많은 커넥션 처리. 단, 메모리 한계가 있어 전체 데이터 저장소로는 부적합.

- Q: Cache-Aside와 Write-Through의 차이는?
  A: Cache-Aside — 앱이 캐시 미스 시 직접 DB 조회 후 캐시 저장. 캐시와 DB 불일치 가능 (TTL로 관리). Write-Through — DB 쓰기와 동시에 캐시도 업데이트. 항상 최신 상태지만 쓰기 지연 증가. 읽기 많은 시스템은 Cache-Aside, 데이터 정합성 중요한 경우 Write-Through.

- Q: Redis의 데이터 영속성은?
  A: RDB(스냅샷) — 주기적으로 메모리 전체를 디스크에 저장. 복구 빠르지만 최근 변경 손실 가능. AOF(Append Only File) — 모든 쓰기 명령을 로그로 기록. 데이터 손실 최소화지만 파일 크기 증가. 실무: AOF + RDB 혼용, 또는 Redis Sentinel/Cluster로 고가용성.

---

## 관련 개념

- [04-01 RDBMS vs NoSQL](./04-01-rdbms-nosql.md) — Redis는 NoSQL Key-Value
- [04-06 격리 수준](./04-06-isolation-level.md) — Redis의 원자적 연산과 비교
- [04-10 파티셔닝/샤딩](./04-10-partitioning-sharding.md) — Redis Cluster
