# 04-10 파티셔닝 / 샤딩 / 레플리케이션

## 개념

**파티셔닝**: 한 테이블의 데이터를 여러 파티션으로 분할 (같은 서버 내).
**샤딩**: 데이터를 여러 서버(샤드)로 수평 분산.
**레플리케이션**: 데이터를 여러 서버에 복제 (읽기 확장, 고가용성).

---

## 동작 원리

### 파티셔닝 (Partitioning)

```
Range Partitioning (범위):
  PARTITION BY RANGE (site_id)
  PARTITION p_1_50  VALUES LESS THAN (51)   → 사이트 1~50
  PARTITION p_51_100 VALUES LESS THAN (101) → 사이트 51~100

  장점: 범위 쿼리 특정 파티션만 스캔
  단점: 핫 파티션 (최신 데이터에 집중)

List Partitioning (목록):
  PARTITION BY LIST (region)
  PARTITION p_seoul   VALUES IN ('서울', '경기')
  PARTITION p_busan   VALUES IN ('부산', '울산')

Hash Partitioning (해시):
  PARTITION BY HASH (device_id) PARTITIONS 4
  → device_id % 4 로 균등 분산
  장점: 균등 분배
  단점: 범위 쿼리 불리

파티션 프루닝 (Partition Pruning):
  WHERE site_id = 42 → p_1_50 파티션만 스캔
  → 데이터량 ÷ 파티션 수로 스캔 범위 축소
```

### 샤딩 (Sharding)

```
수평 샤딩 (Horizontal Sharding):
  같은 테이블 구조, 다른 서버에 분산
  shard_key = device_id % shard_count

  Shard 0: device_id 0, 4, 8, ...
  Shard 1: device_id 1, 5, 9, ...
  Shard 2: device_id 2, 6, 10, ...
  Shard 3: device_id 3, 7, 11, ...

샤딩 문제점:
  1. Cross-Shard JOIN: 여러 샤드 데이터 합치기 어려움
  2. 재샤딩: 샤드 수 변경 시 데이터 이동 필요
     → Consistent Hashing으로 최소화
  3. 트랜잭션: 여러 샤드에 걸친 트랜잭션 복잡
  4. 핫 샤드: 특정 샤드에 트래픽 집중

Consistent Hashing:
  해시 링 위에 샤드 배치 → 샤드 추가/삭제 시 최소 데이터 이동
  샤드 N개 → N+1개로 증가 시 1/N만큼만 재배치
```

### 레플리케이션 (Replication)

```
Master-Slave (Primary-Replica):
  Master: 쓰기
  Slave:  읽기 (Read Replica)

  읽기 트래픽 분산: SELECT → Slave
  쓰기는 Master 단일 → 병목 가능

비동기 vs 동기:
  비동기: Master 커밋 후 Slave에 전파 → 지연(lag) 발생
          → Slave가 오래된 데이터 반환 가능 (Stale Read)
  반동기: 최소 1개 Slave 확인 후 커밋 응답 → 지연 약간 증가
  동기:   모든 Slave 확인 → 안전하지만 쓰기 성능 저하

Replication Lag (복제 지연):
  원인: 네트워크 지연, 쓰기 폭주
  문제: Slave에서 최신 데이터 못 읽음
  해결: 중요한 읽기는 Master에서, 통계/리포트는 Slave

고가용성 (HA):
  Master 장애 시 Slave를 Master로 승격 (Failover)
  자동 감지: Sentinel (Redis), Orchestrator (MySQL)
```

---

## 예시 코드 (Python)

```python
import hashlib
import time
import threading
from typing import Optional


# ── Hash Partitioning 시뮬레이션 ─────────────────────

class PartitionedTable:
    """Hash Partitioning 시뮬레이션"""

    def __init__(self, partition_count: int = 4):
        self.partitions = [{} for _ in range(partition_count)]
        self.n = partition_count

    def _partition_for(self, key: int) -> int:
        return key % self.n

    def insert(self, device_id: int, data: dict):
        p = self._partition_for(device_id)
        self.partitions[p][device_id] = data

    def get(self, device_id: int) -> Optional[dict]:
        p = self._partition_for(device_id)
        return self.partitions[p].get(device_id)

    def scan_partition(self, partition_id: int,
                       filter_fn=None) -> list:
        """특정 파티션만 스캔 (Partition Pruning)"""
        rows = list(self.partitions[partition_id].values())
        return [r for r in rows if filter_fn is None or filter_fn(r)]

    def stats(self):
        print("[파티션 분포]")
        for i, p in enumerate(self.partitions):
            print(f"  Partition {i}: {len(p)}개 행")


# ── Consistent Hashing ───────────────────────────────

class ConsistentHashRing:
    """
    Consistent Hashing Ring
    샤드 추가/삭제 시 최소 데이터 이동
    """

    def __init__(self, virtual_nodes: int = 150):
        self.virtual_nodes = virtual_nodes
        self.ring: dict[int, str] = {}   # {hash_position: shard_name}
        self.shards: set = set()

    def _hash(self, key: str) -> int:
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def add_shard(self, shard: str):
        self.shards.add(shard)
        for i in range(self.virtual_nodes):
            h = self._hash(f"{shard}:{i}")
            self.ring[h] = shard
        print(f"  샤드 추가: {shard} ({self.virtual_nodes}개 가상 노드)")

    def remove_shard(self, shard: str):
        self.shards.discard(shard)
        to_remove = [h for h, s in self.ring.items() if s == shard]
        for h in to_remove:
            del self.ring[h]
        print(f"  샤드 제거: {shard}")

    def get_shard(self, key: str) -> str:
        if not self.ring:
            raise RuntimeError("샤드 없음")
        h = self._hash(key)
        sorted_positions = sorted(self.ring.keys())
        # 키보다 크거나 같은 첫 번째 위치
        for pos in sorted_positions:
            if h <= pos:
                return self.ring[pos]
        return self.ring[sorted_positions[0]]   # 링 wrap-around

    def distribution(self, keys: list) -> dict:
        """키 분포 확인"""
        dist: dict = {}
        for k in keys:
            shard = self.get_shard(k)
            dist[shard] = dist.get(shard, 0) + 1
        return dist


# ── Master-Slave 레플리케이션 시뮬레이션 ─────────────

class ReplicationSimulator:
    """Master-Slave 비동기 레플리케이션 시뮬레이션"""

    def __init__(self, replication_lag_ms: float = 5):
        self.master: dict = {}
        self.slaves: list[dict] = [{}, {}]   # 2개 슬레이브
        self.lag_ms = replication_lag_ms
        self._lock = threading.Lock()
        self.stats = {"writes": 0, "stale_reads": 0, "fresh_reads": 0}

    def write(self, key: str, value, important: bool = False):
        """Master에 쓰기, Slave에 비동기 복제"""
        with self._lock:
            self.master[key] = value
            self.stats["writes"] += 1

        # 비동기 복제 (지연)
        def replicate():
            time.sleep(self.lag_ms / 1000)
            with self._lock:
                for slave in self.slaves:
                    slave[key] = value

        threading.Thread(target=replicate, daemon=True).start()

    def read(self, key: str, from_master: bool = False) -> tuple:
        """
        from_master=True: 최신 데이터 보장 (Master에서 읽기)
        from_master=False: 약간 오래된 데이터 가능 (Slave에서 읽기)
        """
        with self._lock:
            if from_master:
                val = self.master.get(key)
                return val, "master"
            else:
                # Slave에서 읽기 (Round-robin)
                slave = self.slaves[self.stats["writes"] % 2]
                val = slave.get(key)
                is_stale = (key in self.master and
                            self.master[key] != val)
                if is_stale:
                    self.stats["stale_reads"] += 1
                else:
                    self.stats["fresh_reads"] += 1
                return val, f"slave (stale={is_stale})"


# ── 실행 ─────────────────────────────────────────────

print("=== Hash Partitioning ===")
table = PartitionedTable(partition_count=4)
import random
for i in range(100):
    table.insert(i, {
        "hostname": f"device-{i:03d}",
        "site_id": random.randint(1, 20),
        "status": random.choice(["up", "down"])
    })
table.stats()

# 파티션 프루닝 시뮬레이션 (특정 조건의 장비만 스캔)
print("\n  device_id % 4 == 2인 파티션 스캔 (Partition Pruning):")
result = table.scan_partition(2, filter_fn=lambda r: r["status"] == "up")
print(f"  → 파티션 2에서 UP 상태: {len(result)}개 (전체 {len(table.partitions[2])}개 중)")


print("\n=== Consistent Hashing ===")
ring = ConsistentHashRing(virtual_nodes=100)
ring.add_shard("shard-0")
ring.add_shard("shard-1")
ring.add_shard("shard-2")

keys = [f"device:{i}" for i in range(1000)]
dist_before = ring.distribution(keys)
print(f"  분포 (3 샤드): {dist_before}")

# 샤드 추가 시 재배치 최소화
ring.add_shard("shard-3")
dist_after = ring.distribution(keys)
print(f"  분포 (4 샤드): {dist_after}")

moved = sum(1 for k in keys
            if ring.get_shard(k) !=
               ConsistentHashRing(100).__class__.__name__)
print(f"  재배치: 약 {1000 // 4}개 (1/4 수준, 일반 해싱은 전체 재배치)")


print("\n=== Master-Slave 레플리케이션 ===")
repl = ReplicationSimulator(replication_lag_ms=10)

# 쓰기
repl.write("device:sw-core-01:status", "up")
repl.write("device:sw-core-01:cpu", "45%")

# 즉시 읽기 — Stale Read 가능
val, src = repl.read("device:sw-core-01:status")
print(f"  즉시 읽기 (Slave): {val} from {src}")

# Master에서 읽기 — 항상 최신
val, src = repl.read("device:sw-core-01:status", from_master=True)
print(f"  Master 읽기:       {val} from {src}")

# 복제 지연 후 읽기
time.sleep(0.02)
val, src = repl.read("device:sw-core-01:status")
print(f"  지연 후 읽기 (Slave): {val} from {src}")
print(f"  통계: {repl.stats}")
```

---

## 면접 예상 질문

- Q: 파티셔닝과 샤딩의 차이는?
  A: 파티셔닝은 하나의 서버 내에서 테이블을 여러 파티션으로 분할 (스토리지 최적화, 쿼리 프루닝). 샤딩은 여러 서버에 데이터를 분산 (수평 확장, 처리 용량 증가). 파티셔닝은 단일 서버 한계 내, 샤딩은 서버 자체를 늘림.

- Q: Consistent Hashing이란? 일반 해싱과 차이는?
  A: 해시 링(원형 해시 공간)에 서버(샤드)를 배치. 데이터 키를 링에 매핑 → 시계 방향으로 가장 가까운 서버에 배치. 서버 추가/삭제 시 평균 K/N개 키만 이동 (K=전체 키, N=서버 수). 일반 해싱(key % N)은 N 변경 시 거의 모든 키 재배치.

- Q: 레플리케이션 지연(Lag)이 문제가 되는 경우는?
  A: 방금 쓴 데이터를 Slave에서 읽을 때 오래된 데이터 반환 (Stale Read). 예: 잔액 업데이트 후 Slave에서 조회 → 이전 잔액 표시. 해결: ① 중요한 읽기는 Master에서. ② Read-Your-Writes 일관성 (자신의 쓰기는 Master에서 읽기). ③ 반동기 복제 (최소 1 Slave 확인 후 커밋 응답).

---

## 관련 개념

- [04-01 RDBMS vs NoSQL](./04-01-rdbms-nosql.md) — 분산 DB 선택
- [04-09 Redis](./04-09-redis.md) — Redis Cluster (샤딩)
- [03-04 Hash Table](../03-data-structure/03-04-hash-table.md) — Consistent Hashing 기반
