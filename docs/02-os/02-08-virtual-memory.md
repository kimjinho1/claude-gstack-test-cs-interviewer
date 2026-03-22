# 02-08 가상 메모리 / 페이지 교체 알고리즘

## 개념

**가상 메모리**: 프로세스에게 실제 물리 RAM보다 큰 주소 공간을 제공하는 기술. 실제로 필요한 페이지만 물리 메모리에 올리고, 나머지는 디스크(스왑)에 유지.

```
프로세스 입장: 4GB 연속 메모리 공간 존재 (64비트는 수TB)
실제: 일부만 RAM, 나머지는 디스크 스왑 영역
```

---

## 동작 원리

### 요구 페이징 (Demand Paging)

페이지를 미리 로드하지 않고, **실제 접근할 때** 물리 메모리에 올림.

```
① 프로세스 시작: 페이지 테이블 엔트리 모두 invalid
② CPU가 Page X 접근
③ 페이지 테이블 확인 → invalid (페이지 폴트 발생)
④ OS 페이지 폴트 핸들러 실행:
   a. 빈 프레임 찾기
   b. 없으면 교체 알고리즘으로 희생 프레임 선택
   c. 디스크에서 Page X 로드
   d. 페이지 테이블 업데이트 → valid
⑤ 프로세스 재시작 (같은 명령 재실행)
```

### 스왑 (Swap)

```
RAM 부족 → 일부 페이지를 디스크 스왑 영역으로 쫓아냄

스왑 아웃 (Swap Out): RAM → 디스크
스왑 인  (Swap In):  디스크 → RAM (페이지 폴트 시)

성능 영향:
  RAM 접근:  ~100ns
  SSD 접근:  ~100μs  (RAM의 1,000배 느림)
  HDD 접근:  ~10ms   (RAM의 100,000배 느림)

→ 스왑 과다 발생 시 성능 급락 (Thrashing)
```

### Thrashing (스래싱)

```
프로세스가 너무 많아 각 프로세스 워킹 셋이 RAM에 못 올라감
→ 페이지 폴트 연속 발생
→ 스왑 I/O에 CPU 대부분 소비
→ 실제 작업 거의 못 함

해결:
  - 실행 중 프로세스 수 줄이기
  - RAM 증설
  - Working Set 모델 (각 프로세스 필요 페이지 세트 보장)
```

---

## 페이지 교체 알고리즘

RAM이 꽉 찼을 때 어떤 페이지를 스왑 아웃할지 결정.

### 1. OPT (Optimal) — 이론적 최적

미래에 **가장 오래 사용되지 않을** 페이지 교체. 구현 불가 (미래 예측 필요). 성능 비교 기준.

```
참조열: 7 0 1 2 0 3 0 4 2 3 0 3 2
프레임: 3개

7 → [7]
0 → [7,0]
1 → [7,0,1]
2 → [2,0,1]  ← 7 교체 (미래에 가장 늦게 사용)
0 → 히트
3 → [2,0,3]  ← 1 교체
...
페이지 폴트: 6회
```

### 2. FIFO (First In First Out)

**가장 먼저 올라온** 페이지 교체.

```
참조열: 7 0 1 2 0 3 0 4 2 3 0 3
프레임: 3개

7 → [7,-,-]      폴트
0 → [7,0,-]      폴트
1 → [7,0,1]      폴트
2 → [2,0,1]      폴트 (7 out)
0 → 히트
3 → [2,3,1]      폴트 (0 out)
0 → [2,3,0]      폴트 (1 out)
4 → [4,3,0]      폴트 (2 out)
...
페이지 폴트: 9회

단점: Belady's Anomaly — 프레임 늘려도 폴트 증가하는 경우 있음
```

### 3. LRU (Least Recently Used) — 실무 표준

**가장 오래 사용되지 않은** 페이지 교체. 과거가 미래를 예측한다는 가정.

```
참조열: 7 0 1 2 0 3 0 4 2 3 0 3
프레임: 3개

7 → [7]           폴트
0 → [7,0]         폴트
1 → [7,0,1]       폴트
2 → [2,0,1]       폴트 (7 교체 — 가장 오래 미사용)
0 → [2,0,1] 히트  0 → 최근 사용
3 → [2,0,3]       폴트 (1 교체)
0 → [2,0,3] 히트
4 → [4,0,3]       폴트 (2 교체)
2 → [4,0,2] 폴트  (3 교체)  ← 3이 가장 오래됨
3 → [3,0,2] 폴트  (4 교체)
0 → 히트
3 → 히트
페이지 폴트: 8회

구현:
  정확: 더블 링크드 리스트 + 해시맵 O(1)
  근사: 참조 비트(Reference Bit) — 클락 알고리즘
```

### 4. Clock (Second Chance) — LRU 근사, 실제 OS 사용

FIFO에 참조 비트 추가. 교체 후보 페이지에게 **두 번째 기회** 부여.

```
원형 큐 구조, 시계 바늘이 돌아가며 검사:

페이지 접근 시: 참조 비트 = 1

교체 시:
  바늘이 가리키는 페이지의 참조 비트 확인
  1이면: 0으로 초기화 후 다음으로 (두 번째 기회)
  0이면: 해당 페이지 교체

결과: LRU에 근접한 성능 + 구현 단순
Linux: 클락 알고리즘 변형(LRU-K, PG_active/inactive 리스트) 사용
```

### 알고리즘 비교

| 알고리즘 | 폴트 수 | 구현 | 실제 사용 |
|---------|---------|------|---------|
| OPT | 최소 | 불가 | 기준점 |
| LRU | OPT에 근접 | 복잡 O(1) | 이론 표준 |
| Clock | LRU 근사 | 단순 | Linux 등 OS |
| FIFO | 많음 | 매우 단순 | 거의 안씀 |

---

## 예시 코드 (Python)

```python
from collections import OrderedDict, deque


# ── LRU 캐시 (페이지 교체 시뮬레이션) ───────────────────

class LRUCache:
    """LRU 페이지 교체 알고리즘"""
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._cache: OrderedDict[int, bool] = OrderedDict()
        self.faults = 0
        self.hits = 0

    def access(self, page: int):
        if page in self._cache:
            self._cache.move_to_end(page)  # 최근 사용으로 이동
            self.hits += 1
            return "HIT"
        else:
            self.faults += 1
            if len(self._cache) >= self.capacity:
                evicted = next(iter(self._cache))
                del self._cache[evicted]
                print(f"  페이지 {page} 로드, 페이지 {evicted} 교체 (LRU)")
            else:
                print(f"  페이지 {page} 로드")
            self._cache[page] = True
            return "FAULT"

    def stats(self):
        total = self.hits + self.faults
        print(f"LRU: 총 {total}회, 히트 {self.hits}, 폴트 {self.faults}, "
              f"폴트율 {self.faults/total*100:.1f}%")
        print(f"  현재 프레임: {list(self._cache.keys())}")


# ── FIFO 페이지 교체 ──────────────────────────────────

class FIFOCache:
    """FIFO 페이지 교체 알고리즘"""
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._queue: deque[int] = deque()
        self._pages: set[int] = set()
        self.faults = 0
        self.hits = 0

    def access(self, page: int):
        if page in self._pages:
            self.hits += 1
            return "HIT"
        else:
            self.faults += 1
            if len(self._queue) >= self.capacity:
                evicted = self._queue.popleft()
                self._pages.remove(evicted)
                print(f"  페이지 {page} 로드, 페이지 {evicted} 교체 (FIFO)")
            else:
                print(f"  페이지 {page} 로드")
            self._queue.append(page)
            self._pages.add(page)
            return "FAULT"

    def stats(self):
        total = self.hits + self.faults
        print(f"FIFO: 총 {total}회, 히트 {self.hits}, 폴트 {self.faults}, "
              f"폴트율 {self.faults/total*100:.1f}%")


# ── Clock 알고리즘 ─────────────────────────────────────

class ClockCache:
    """Clock (Second Chance) 알고리즘"""
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._frames: list[tuple[int, int]] = []  # (page, ref_bit)
        self._hand = 0
        self.faults = 0
        self.hits = 0

    def _find(self, page: int) -> int:
        for i, (p, _) in enumerate(self._frames):
            if p == page:
                return i
        return -1

    def access(self, page: int):
        idx = self._find(page)
        if idx >= 0:
            self._frames[idx] = (page, 1)  # 참조 비트 = 1
            self.hits += 1
            return "HIT"

        self.faults += 1
        if len(self._frames) < self.capacity:
            self._frames.append((page, 1))
            print(f"  페이지 {page} 로드 (빈 슬롯)")
            return "FAULT"

        # 교체 대상 탐색
        while True:
            p, ref = self._frames[self._hand]
            if ref == 0:
                print(f"  페이지 {page} 로드, 페이지 {p} 교체 (Clock)")
                self._frames[self._hand] = (page, 1)
                self._hand = (self._hand + 1) % self.capacity
                break
            else:
                self._frames[self._hand] = (p, 0)  # 두 번째 기회 소진
                self._hand = (self._hand + 1) % self.capacity
        return "FAULT"

    def stats(self):
        total = self.hits + self.faults
        print(f"Clock: 총 {total}회, 히트 {self.hits}, 폴트 {self.faults}, "
              f"폴트율 {self.faults/total*100:.1f}%")


# ── 알고리즘 비교 ──────────────────────────────────────

reference_string = [7, 0, 1, 2, 0, 3, 0, 4, 2, 3, 0, 3, 2]
FRAMES = 3

print(f"참조열: {reference_string}, 프레임: {FRAMES}\n")

for CacheClass in [LRUCache, FIFOCache, ClockCache]:
    cache = CacheClass(FRAMES)
    for page in reference_string:
        cache.access(page)
    cache.stats()
    print()
```

---

## 면접 예상 질문

- Q: 가상 메모리란? 왜 필요한가?
  A: 프로세스가 실제 RAM보다 큰 주소 공간을 사용할 수 있게 하는 기술. 실제로 필요한 페이지만 RAM에 올리고 나머지는 디스크에 유지. 이점: 여러 프로세스 동시 실행 가능, 프로그램 크기가 RAM을 초과해도 실행 가능, 메모리 보호.

- Q: 페이지 폴트란? OS는 어떻게 처리하나?
  A: 프로세스가 접근하려는 페이지가 물리 RAM에 없을 때 발생하는 예외. OS가 페이지 폴트 핸들러에서 디스크 스왑에서 해당 페이지를 로드 → 페이지 테이블 업데이트 → 프로세스 재실행. RAM이 가득 찼으면 교체 알고리즘으로 희생 페이지 선택 후 스왑 아웃.

- Q: LRU와 Clock 알고리즘의 차이는?
  A: LRU는 가장 오래 사용 안 한 페이지를 교체. 링크드 리스트+해시맵으로 O(1) 구현. OPT에 근접한 성능. Clock은 LRU 근사로, 각 페이지에 참조 비트를 두고 교체 시 비트가 1이면 0으로 초기화하고 넘어감(두 번째 기회). 성능은 LRU에 근접하면서 구현이 단순해 실제 OS에서 사용.

- Q: Thrashing이란? 어떻게 방지하나?
  A: 프로세스가 많아 각 프로세스의 워킹 셋(실제 필요 페이지)이 RAM에 다 올라오지 못해 페이지 폴트가 연속 발생, CPU가 스왑 I/O만 하는 상태. 방지: 실행 프로세스 수 줄이기, RAM 증설, Working Set 모델로 각 프로세스 최소 프레임 보장.

- Q: OOM Killer란? 어떻게 희생 프로세스를 선택하나?
  A: Out Of Memory Killer. Linux에서 물리 RAM + 스왑이 모두 고갈됐을 때 커널이 프로세스를 강제 종료해 메모리를 회수하는 메커니즘. 각 프로세스에 oom_score(0~1000)를 계산 — 메모리 사용량 큰 것, 오래 실행된 것, root 프로세스 아닌 것 우선 종료. `/proc/<pid>/oom_score`로 확인. `/proc/<pid>/oom_score_adj`로 조정(-1000이면 절대 종료 안 함, +1000이면 우선 종료).

---

## OOM Killer (Out Of Memory Killer)

RAM + 스왑 모두 고갈 시 Linux 커널이 작동하는 최후 수단.

```
메모리 부족 흐름:
  ① 프로세스가 malloc() → 가상 주소 반환 (실제 물리 할당 X — Lazy Allocation)
  ② 실제 접근 시 페이지 폴트 → RAM 할당 시도
  ③ RAM + 스왑 모두 없음 → OOM 상황
  ④ OOM Killer 작동 → oom_score 높은 프로세스 kill -9

oom_score 계산:
  기본 점수 = 프로세스의 RAM + 스왑 사용량 (페이지 수)
  × 1000 / 전체 메모리 (페이지 수)
  → 0~1000 범위

감점 요소:
  - root 프로세스: 점수 낮춤
  - 오래 실행된 프로세스: 점수 낮춤
  - 자식 많은 프로세스: 자식까지 합산

수동 확인:
  $ cat /proc/$(pgrep snmpd)/oom_score      # 현재 점수
  $ cat /proc/$(pgrep snmpd)/oom_score_adj  # 조정값

oom_score_adj 설정:
  -1000 : OOM Killer가 절대 종료 안 함 (중요 데몬에 설정)
   0    : 기본값
  +1000 : 메모리 부족 시 가장 먼저 종료

실무 예:
  echo -1000 > /proc/$(pgrep sshd)/oom_score_adj  # SSH 데몬 보호
  # systemd: OOMPolicy=kill | continue | stop
```

```python
import os, subprocess

def check_oom_scores():
    """현재 프로세스의 OOM 관련 정보 확인"""
    pid = os.getpid()
    print(f"[OOM 정보] PID={pid}")

    # oom_score 읽기
    try:
        with open(f"/proc/{pid}/oom_score") as f:
            score = f.read().strip()
        with open(f"/proc/{pid}/oom_score_adj") as f:
            adj = f.read().strip()
        print(f"  oom_score={score}, oom_score_adj={adj}")
        print(f"  (낮을수록 OOM Killer 대상에서 멀어짐)")
    except FileNotFoundError:
        print("  /proc not available (non-Linux)")

    # 시스템 메모리 상태
    result = subprocess.run(["free", "-h"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"\n  메모리 상태:\n{result.stdout}")

    # top 프로세스 (oom_score 기준)
    try:
        procs = []
        for p in os.listdir("/proc"):
            if p.isdigit():
                try:
                    with open(f"/proc/{p}/oom_score") as f:
                        s = int(f.read().strip())
                    with open(f"/proc/{p}/comm") as f:
                        name = f.read().strip()
                    procs.append((s, p, name))
                except (FileNotFoundError, PermissionError):
                    pass
        procs.sort(reverse=True)
        print("  OOM 우선 종료 대상 (상위 5개):")
        for score, pid, name in procs[:5]:
            print(f"    PID={pid:6s} {name:20s} score={score}")
    except (FileNotFoundError, PermissionError):
        pass

check_oom_scores()
```

## 관련 개념

- [02-07 메모리 관리](./02-07-memory-management.md) — 페이징 기초, TLB
- [02-09 캐시](./02-09-cache.md) — 캐시 미스와 페이지 폴트 비교
