# 02-07 메모리 관리 (페이징, 세그멘테이션)

## 개념

OS가 여러 프로세스에게 메모리를 효율적으로 분배하고 보호하는 메커니즘.

**핵심 문제**: 프로세스는 연속된 메모리를 원하지만, 실제 물리 메모리는 파편화(Fragmentation)된다.

---

## 동작 원리

### 메모리 할당 방식의 진화

```
초기: 연속 할당 (Contiguous Allocation)
  프로세스에게 연속된 물리 메모리 블록 할당
  문제: 외부 단편화 (External Fragmentation)

Process A (100MB) | 빈 공간(50MB) | Process B (200MB) | 빈 공간(30MB)
→ 총 80MB 비어있지만 150MB 프로세스 못 넣음
```

### 페이징 (Paging)

물리 메모리를 고정 크기 **프레임(Frame)**, 논리 주소 공간을 동일 크기 **페이지(Page)**로 분할.

```
페이지 크기: 보통 4KB

논리 주소 공간 (프로세스 관점):
  Page 0 (0~4KB)
  Page 1 (4~8KB)
  Page 2 (8~12KB)

물리 메모리 (실제 RAM):
  Frame 0: OS
  Frame 1: Process A Page 2  ← 순서 바뀌어도 됨
  Frame 2: Process B Page 0
  Frame 3: Process A Page 0  ← 불연속 OK
  Frame 4: Process A Page 1

페이지 테이블 (프로세스별 보유):
  Page 0 → Frame 3
  Page 1 → Frame 4
  Page 2 → Frame 1
```

**주소 변환 (논리 → 물리)**:

```
논리 주소 = 페이지 번호(p) + 페이지 오프셋(d)

예: 논리 주소 = 13
    페이지 크기 = 4KB = 4096
    p = 13 / 4096 = 0 (페이지 0)
    d = 13 % 4096 = 13 (오프셋 13)

    페이지 테이블: Page 0 → Frame 3
    물리 주소 = 3 × 4096 + 13 = 12301
```

**TLB (Translation Lookaside Buffer)**:

```
페이지 테이블은 메모리에 있음 → 주소 변환마다 메모리 2번 접근 (비효율)
TLB: 최근 사용한 페이지 변환 결과 캐시 (CPU 내부)

TLB 히트: 논리→물리 주소 변환 1사이클
TLB 미스: 페이지 테이블 접근 → TLB 업데이트
TLB 히트율: 보통 99% 이상
```

**페이징 장단점**:
- 장점: 외부 단편화 없음, 메모리 보호 (페이지 단위 접근 제어)
- 단점: **내부 단편화** (페이지 마지막에 낭비), 페이지 테이블 메모리 오버헤드

### 세그멘테이션 (Segmentation)

프로세스를 **논리적 의미 단위(세그먼트)**로 분할. 크기 가변.

```
프로세스 메모리 구조:
  Segment 0: 코드 (Code)   — 10KB
  Segment 1: 데이터 (Data) — 5KB
  Segment 2: 힙 (Heap)     — 20KB (가변)
  Segment 3: 스택 (Stack)  — 8KB (가변)

세그먼트 테이블:
  번호 | 베이스 주소 | 한계(크기) | 권한
  0    | 0x1000     | 10240      | r-x  (읽기+실행)
  1    | 0x5000     | 5120       | rw-  (읽기+쓰기)
  2    | 0x8000     | 20480      | rw-
  3    | 0xF000     | 8192       | rw-
```

**주소 변환**:

```
논리 주소 = 세그먼트 번호(s) + 오프셋(d)

유효성 검사: d < 세그먼트 한계 → OK
물리 주소 = 세그먼트 베이스 + d

오프셋이 한계 초과 → Segmentation Fault!
```

**세그멘테이션 장단점**:
- 장점: 논리적 단위로 보호/공유 (코드 세그먼트 공유), 내부 단편화 없음
- 단점: **외부 단편화** (가변 크기로 메모리 구멍 발생)

### 페이징 + 세그멘테이션 혼합

실제 OS (Linux, Windows)는 **페이지드 세그멘테이션** 또는 주로 페이징 사용.

```
Linux x86-64:
  사실상 페이징만 사용 (세그먼트는 거의 무력화)
  4단계 페이지 테이블 (PGD → PUD → PMD → PTE)
  페이지 크기: 4KB (기본), 2MB/1GB (Huge Pages)
```

### 단편화 (Fragmentation)

```
내부 단편화 (Internal Fragmentation):
  할당된 메모리 내부에 낭비
  예: 4KB 페이지에 3.5KB 데이터 → 0.5KB 낭비
  페이징에서 발생

외부 단편화 (External Fragmentation):
  할당되지 않은 공간이 조각조각 흩어짐
  예: 100MB 필요한데 50MB + 50MB로 분리됨
  세그멘테이션, 연속 할당에서 발생

해결:
  Compaction (압축): 프로세스를 이동해 연속 공간 확보 (비용 큼)
  Buddy System: 2의 배수로 블록 분할/합병
```

---

## 예시 코드 (Python)

```python
from dataclasses import dataclass, field
from typing import Optional


# ── 페이지 테이블 시뮬레이션 ──────────────────────────

PAGE_SIZE = 4096  # 4KB


@dataclass
class PageTableEntry:
    frame_number: int
    valid: bool = True
    dirty: bool = False    # 수정됨
    referenced: bool = False  # 최근 접근됨
    protection: str = "rw"  # r=read, w=write, x=execute


class PageTable:
    """프로세스 페이지 테이블"""
    def __init__(self, process_id: str):
        self.pid = process_id
        self.entries: dict[int, PageTableEntry] = {}

    def map(self, page_num: int, frame_num: int, protection: str = "rw"):
        self.entries[page_num] = PageTableEntry(frame_num, protection=protection)
        print(f"[{self.pid}] Page {page_num} → Frame {frame_num} ({protection})")

    def translate(self, logical_addr: int) -> Optional[int]:
        page_num = logical_addr // PAGE_SIZE
        offset   = logical_addr %  PAGE_SIZE

        entry = self.entries.get(page_num)
        if entry is None or not entry.valid:
            raise MemoryError(f"Page Fault! 페이지 {page_num} 유효하지 않음")

        physical_addr = entry.frame_number * PAGE_SIZE + offset
        entry.referenced = True
        return physical_addr


class TLB:
    """Translation Lookaside Buffer (간단 캐시)"""
    def __init__(self, size: int = 8):
        self._cache: dict[tuple, int] = {}  # (pid, page) → frame
        self._size = size
        self._hits = 0
        self._misses = 0

    def lookup(self, pid: str, page_num: int) -> Optional[int]:
        key = (pid, page_num)
        if key in self._cache:
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def update(self, pid: str, page_num: int, frame_num: int):
        if len(self._cache) >= self._size:
            # 단순 FIFO 방출
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[(pid, page_num)] = frame_num

    def stats(self):
        total = self._hits + self._misses
        rate = self._hits / total * 100 if total > 0 else 0
        print(f"TLB: 히트 {self._hits}, 미스 {self._misses}, 히트율 {rate:.1f}%")


# ── 세그먼트 테이블 시뮬레이션 ────────────────────────

@dataclass
class SegmentEntry:
    base: int     # 물리 시작 주소
    limit: int    # 세그먼트 크기
    protection: str = "rw"


class SegmentTable:
    """세그먼트 테이블"""
    def __init__(self, process_id: str):
        self.pid = process_id
        self.segments: dict[int, SegmentEntry] = {}

    def add(self, seg_num: int, base: int, limit: int, protection: str = "rw"):
        self.segments[seg_num] = SegmentEntry(base, limit, protection)
        names = {0: "Code", 1: "Data", 2: "Heap", 3: "Stack"}
        print(f"[{self.pid}] Seg {seg_num}({names.get(seg_num, '?')}) base={hex(base)} limit={limit} ({protection})")

    def translate(self, seg_num: int, offset: int) -> int:
        seg = self.segments.get(seg_num)
        if seg is None:
            raise MemoryError(f"유효하지 않은 세그먼트: {seg_num}")
        if offset >= seg.limit:
            raise MemoryError(f"Segmentation Fault! offset({offset}) >= limit({seg.limit})")
        return seg.base + offset


# ── 물리 메모리 프레임 관리 ────────────────────────────

class PhysicalMemory:
    """물리 메모리 (프레임 할당/해제)"""
    def __init__(self, total_frames: int = 16):
        self._free = list(range(total_frames))
        self._allocated: dict[int, str] = {}  # frame → pid

    def allocate(self, pid: str, count: int) -> list[int]:
        if len(self._free) < count:
            raise MemoryError(f"메모리 부족! 요청={count}, 가용={len(self._free)}")
        frames = [self._free.pop(0) for _ in range(count)]
        for f in frames:
            self._allocated[f] = pid
        return frames

    def free(self, pid: str):
        freed = [f for f, p in self._allocated.items() if p == pid]
        for f in freed:
            del self._allocated[f]
            self._free.append(f)
        self._free.sort()
        print(f"[{pid}] {len(freed)}개 프레임 해제")

    def status(self):
        print(f"물리 메모리: 전체={len(self._free)+len(self._allocated)} 프레임, "
              f"사용={len(self._allocated)}, 여유={len(self._free)}")


# ── 시뮬레이션 ─────────────────────────────────────────

print("=== 페이징 시뮬레이션 ===")
mem = PhysicalMemory(total_frames=16)
tlb = TLB(size=4)

# 프로세스 A: 3페이지 할당
frames_a = mem.allocate("ProcA", 3)
pt_a = PageTable("ProcA")
for i, frame in enumerate(frames_a):
    pt_a.map(i, frame)

# 주소 변환
for addr in [0, 4096, 8100, 100]:
    page = addr // PAGE_SIZE
    # TLB 먼저
    frame = tlb.lookup("ProcA", page)
    if frame is None:
        phys = pt_a.translate(addr)
        tlb.update("ProcA", page, phys // PAGE_SIZE)
    else:
        phys = frame * PAGE_SIZE + (addr % PAGE_SIZE)
    print(f"  논리 {addr:5d} → 물리 {phys:5d} (페이지 {page}, 프레임 {phys // PAGE_SIZE})")

tlb.stats()
mem.status()

print("\n=== 세그멘테이션 시뮬레이션 ===")
st = SegmentTable("ProcB")
st.add(0, base=0x1000, limit=10240, protection="r-x")  # Code
st.add(1, base=0x5000, limit=5120,  protection="rw-")  # Data
st.add(2, base=0x8000, limit=20480, protection="rw-")  # Heap
st.add(3, base=0xF000, limit=8192,  protection="rw-")  # Stack

# 주소 변환
try:
    print(f"  Code[100] → {hex(st.translate(0, 100))}")
    print(f"  Data[200] → {hex(st.translate(1, 200))}")
    print(f"  Heap[1000] → {hex(st.translate(2, 1000))}")
    st.translate(0, 99999)  # Segfault!
except MemoryError as e:
    print(f"  예외: {e}")

mem.free("ProcA")
mem.status()
```

---

## 면접 예상 질문

- Q: 페이징과 세그멘테이션의 차이는?
  A: 페이징은 물리 메모리를 고정 크기 프레임으로 나눠 외부 단편화를 없앰. 내부 단편화 발생. 세그멘테이션은 논리적 의미 단위(코드/데이터/스택)로 분할해 보호와 공유가 쉬움. 외부 단편화 발생. 현대 OS(Linux)는 주로 페이징 사용.

- Q: TLB란? 왜 필요한가?
  A: Translation Lookaside Buffer. 페이지 테이블 변환 결과를 캐시하는 CPU 내 소형 고속 메모리. 페이지 테이블은 RAM에 있어 매번 메모리 접근이 필요하지만, TLB 히트 시 1사이클로 변환. 히트율 99% 이상으로 주소 변환 오버헤드를 사실상 제거.

- Q: 내부 단편화 vs 외부 단편화는?
  A: 내부 단편화는 할당된 블록 내에 사용되지 않는 공간 (페이징에서 페이지 끝부분 낭비). 외부 단편화는 할당 해제된 공간이 작게 흩어져 큰 연속 공간을 못 만드는 것 (세그멘테이션/연속 할당에서 발생). 페이징은 외부 단편화를 없애는 대신 내부 단편화를 허용.

- Q: 페이지 폴트(Page Fault)란?
  A: 프로세스가 접근하려는 페이지가 물리 메모리에 없을 때 발생하는 예외. OS가 디스크에서 해당 페이지를 RAM으로 로드 후 재실행. 가상 메모리의 핵심 메커니즘. (→ 02-08 가상 메모리에서 상세 다룸)

---

## 관련 개념

- [02-01 프로세스 vs 스레드](./02-01-process-thread.md) — 프로세스 메모리 레이아웃
- [02-08 가상 메모리](./02-08-virtual-memory.md) — 페이지 폴트, 스왑, 교체 알고리즘
- [02-09 캐시](./02-09-cache.md) — TLB도 캐시의 일종
