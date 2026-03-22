# 02-09 캐시 (L1/L2/L3, 히트/미스)

## 개념

**캐시(Cache)**: 느린 저장소 앞에 빠른 소형 저장소를 두어 자주 쓰는 데이터를 빠르게 제공하는 기법.

```
속도 계층 (빠름 → 느림, 크기는 반대):
CPU 레지스터  ~1 사이클   (수십 B)
L1 캐시       ~4 사이클   (32~64KB)
L2 캐시       ~12 사이클  (256KB~1MB)
L3 캐시       ~40 사이클  (8~64MB, 코어 공유)
RAM (DRAM)    ~200 사이클 (수십 GB)
SSD           ~100,000 사이클
HDD           ~수백만 사이클
```

---

## 동작 원리

### 캐시 히트 / 미스

```
CPU가 데이터 요청 시:

캐시 히트(Hit): 캐시에 있음 → 빠르게 반환
캐시 미스(Miss): 캐시에 없음 → 하위 계층에서 가져와 캐시에 적재

히트율(Hit Rate) = 히트 횟수 / 전체 접근 횟수
평균 접근 시간 = 히트율 × L1 접근 시간 + (1-히트율) × 미스 패널티
```

### 지역성 (Locality)

캐시가 효과적인 이유:

```
시간적 지역성 (Temporal Locality):
  최근 접근한 데이터를 곧 다시 접근할 가능성이 높다
  예: for 루프의 루프 카운터 변수

공간적 지역성 (Spatial Locality):
  접근한 주소 근처를 곧 접근할 가능성이 높다
  예: 배열 순차 접근 (array[0], array[1], ...)
  캐시는 1개 데이터가 아닌 캐시라인(64바이트) 단위로 로드
```

### 캐시라인 (Cache Line)

```
캐시는 64바이트 캐시라인 단위로 데이터를 로드

int array[16];  // 64바이트 = 캐시라인 1개에 딱 맞음
array[0] 접근 → 캐시라인 통째로 로드 → array[1]~array[15]도 캐시에
→ 이후 접근: 모두 히트!

역방향/stride 접근 → 캐시 미스 빈발
```

### 캐시 교체 정책

```
Direct-Mapped: 각 메모리 주소가 특정 캐시 슬롯에만 매핑. 빠르지만 충돌 미스.
N-Way Set Associative: N개 슬롯에 매핑 가능. 실제 CPU 사용.
Fully Associative: 어느 슬롯에나 가능. TLB에서 사용.

교체 알고리즘: LRU, Random, PLRU (Pseudo-LRU)
```

### 쓰기 정책

```
Write-Through: 캐시와 메모리 동시 업데이트. 일관성 보장, 쓰기 느림.
Write-Back:    캐시에만 쓰고, 교체 시 메모리에 반영 (Dirty bit). 빠름.
               → 현대 CPU는 Write-Back + Write-Buffer 사용
```

### 캐시 일관성 (Cache Coherence)

멀티코어에서 각 코어가 L1/L2 캐시를 독립 보유 → 같은 메모리를 다르게 볼 수 있음.

```
Core 0 L1: x = 5
Core 1 L1: x = 5
Core 0: x = 10 (Core 0 L1에만 반영)
Core 1: x 읽기 → 5 (오래된 값!)

해결: MESI 프로토콜
  Modified(M): 이 캐시만 최신, 메모리와 다름
  Exclusive(E): 이 캐시만 보유, 메모리와 동일
  Shared(S): 여러 캐시가 공유, 읽기 전용
  Invalid(I): 유효하지 않음

Core 0가 x=10 쓰기 → 다른 코어의 캐시라인 Invalid 처리
Core 1가 x 읽기 → Invalid 감지 → 최신 값 가져옴
```

### False Sharing

```
같은 캐시라인에 있는 다른 변수를 서로 다른 코어가 수정
→ 실제로 공유하지 않지만 캐시 일관성 트래픽 발생 → 성능 저하

예:
struct { int a; int b; }  // a, b가 같은 캐시라인에 있음
Core 0: a++ 반복
Core 1: b++ 반복
→ 서로 Invalid 처리 반복 → 메모리 버스 폭주

해결: 변수를 캐시라인(64바이트)으로 패딩
struct { int a; char pad[60]; int b; }
```

---

## 예시 코드 (Python)

```python
import time
import random


# ── 캐시 히트/미스 시뮬레이션 ────────────────────────

class SimpleCache:
    """직접 매핑 캐시 시뮬레이션"""
    def __init__(self, size: int = 8):
        self.size = size
        self._data: dict[int, int] = {}  # addr → value
        self._lru: list[int] = []
        self.hits = 0
        self.misses = 0

    def access(self, addr: int, memory: dict[int, int]) -> int:
        if addr in self._data:
            self.hits += 1
            self._lru.remove(addr)
            self._lru.append(addr)
            return self._data[addr]

        # 캐시 미스 → 메모리에서 로드
        self.misses += 1
        if len(self._data) >= self.size:
            evict = self._lru.pop(0)  # LRU 방출
            del self._data[evict]

        self._data[addr] = memory.get(addr, 0)
        self._lru.append(addr)
        return self._data[addr]

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0


# ── 지역성 비교: 순차 접근 vs 랜덤 접근 ──────────────

def locality_demo():
    SIZE = 1024
    memory = {i: i * 2 for i in range(SIZE)}

    # 순차 접근 (공간적 지역성 O)
    cache_seq = SimpleCache(size=32)
    for i in range(SIZE):
        cache_seq.access(i, memory)

    # 랜덤 접근 (지역성 X)
    cache_rnd = SimpleCache(size=32)
    addrs = list(range(SIZE))
    random.shuffle(addrs)
    for addr in addrs:
        cache_rnd.access(addr, memory)

    print(f"순차 접근: 히트율 {cache_seq.hit_rate():.2%} "
          f"(히트 {cache_seq.hits}, 미스 {cache_seq.misses})")
    print(f"랜덤 접근: 히트율 {cache_rnd.hit_rate():.2%} "
          f"(히트 {cache_rnd.hits}, 미스 {cache_rnd.misses})")


# ── 캐시 친화적 코드 vs 비친화적 코드 ────────────────

def cache_friendly_demo():
    """2D 배열 접근 패턴: 행 우선 vs 열 우선"""
    N = 500
    matrix = [[i * N + j for j in range(N)] for i in range(N)]

    # 행 우선 접근 (캐시 친화적 — 공간적 지역성)
    start = time.perf_counter()
    total = 0
    for i in range(N):
        for j in range(N):
            total += matrix[i][j]  # 연속 메모리 접근
    row_time = time.perf_counter() - start

    # 열 우선 접근 (캐시 비친화적 — stride 접근)
    start = time.perf_counter()
    total = 0
    for j in range(N):
        for i in range(N):
            total += matrix[i][j]  # N칸 건너뜀
    col_time = time.perf_counter() - start

    print(f"행 우선 접근: {row_time*1000:.2f}ms (캐시 친화적)")
    print(f"열 우선 접근: {col_time*1000:.2f}ms (캐시 비친화적)")
    print(f"속도 차이: {col_time/row_time:.1f}배")


# ── 간단한 캐시 계층 (L1/L2/L3 시뮬레이션) ──────────

class CacheHierarchy:
    """L1 → L2 → L3 → Memory 계층"""
    LATENCY = {"L1": 4, "L2": 12, "L3": 40, "MEM": 200}  # 사이클

    def __init__(self):
        self.l1 = set()  # 최대 4개 항목
        self.l2 = set()  # 최대 8개
        self.l3 = set()  # 최대 16개
        self.stats = {"L1": 0, "L2": 0, "L3": 0, "MEM": 0}

    def _l1_add(self, addr):
        if len(self.l1) >= 4:
            self.l1.pop()
        self.l1.add(addr)

    def access(self, addr: int) -> int:
        if addr in self.l1:
            self.stats["L1"] += 1
            return self.LATENCY["L1"]
        if addr in self.l2:
            self.stats["L2"] += 1
            self._l1_add(addr)
            return self.LATENCY["L2"]
        if addr in self.l3:
            self.stats["L3"] += 1
            self.l2.add(addr); self._l1_add(addr)
            return self.LATENCY["L3"]
        # 메모리 접근
        self.stats["MEM"] += 1
        self.l3.add(addr); self.l2.add(addr); self._l1_add(addr)
        return self.LATENCY["MEM"]

    def report(self, accesses: int):
        total_cycles = sum(self.LATENCY[l] * cnt for l, cnt in self.stats.items())
        avg = total_cycles / accesses
        print(f"캐시 계층 통계:")
        for level, cnt in self.stats.items():
            print(f"  {level}: {cnt}회 ({cnt/accesses*100:.1f}%)")
        print(f"  평균 접근 비용: {avg:.1f} 사이클")


print("=== 지역성 비교 ===")
locality_demo()

print("\n=== 캐시 친화적 접근 ===")
cache_friendly_demo()

print("\n=== 캐시 계층 시뮬레이션 ===")
hier = CacheHierarchy()
# 반복 접근 (시간적 지역성)
addrs = [1, 2, 3, 4, 1, 2, 1, 3, 2, 1, 5, 1, 2, 3, 1]
total_cycles = sum(hier.access(a) for a in addrs)
hier.report(len(addrs))
```

---

## 면접 예상 질문

- Q: CPU 캐시 L1/L2/L3의 차이는?
  A: 속도와 크기의 트레이드오프. L1: 코어당 독립, 가장 빠름(~4사이클), 가장 작음(32~64KB). L2: 코어당 독립, 중간 속도(~12사이클), 중간 크기(수백KB). L3: 모든 코어 공유, 느림(~40사이클), 가장 큼(수~수십MB). L1 미스 → L2 탐색 → L3 탐색 → RAM 순서.

- Q: 캐시 히트율이 성능에 미치는 영향은?
  A: 평균 접근 시간 = 히트율 × L1 시간 + (1-히트율) × RAM 시간. L1=4사이클, RAM=200사이클일 때 히트율 99% → 평균 약 6사이클. 히트율 90% → 평균 약 24사이클. 히트율 1% 차이가 성능에 큰 영향. 지역성이 좋은 코드(순차 접근, 반복 접근)로 히트율 개선.

- Q: False Sharing이란?
  A: 멀티코어 환경에서 서로 다른 코어가 논리적으로 무관한 변수를 수정하지만, 그 변수들이 같은 캐시라인(64바이트)에 있어 캐시 일관성 프로토콜(MESI)이 불필요한 무효화/동기화를 일으키는 현상. 성능이 순차 처리보다 떨어질 수 있음. 해결: 캐시라인 크기(64바이트)로 변수 정렬/패딩.

- Q: Write-Through와 Write-Back의 차이는?
  A: Write-Through는 캐시에 쓸 때 메모리에도 동시 반영. 일관성 보장이 쉽지만 쓰기마다 메모리 접근 발생. Write-Back은 캐시에만 쓰고(Dirty 비트 표시), 해당 캐시라인이 교체될 때만 메모리에 반영. 쓰기 성능 우수. 현대 CPU는 Write-Back + Write-Buffer 사용.

---

## 관련 개념

- [02-07 메모리 관리](./02-07-memory-management.md) — TLB도 캐시 (페이지 변환 결과 캐시)
- [02-08 가상 메모리](./02-08-virtual-memory.md) — 캐시 미스 vs 페이지 폴트 비교
