# 03-05 정렬 (Quick, Merge, Heap, Counting)

## 개념

N개의 원소를 특정 순서로 나열. 시간 복잡도와 공간 복잡도, 안정성(Stable)이 선택 기준.

| 알고리즘 | 최선 | 평균 | 최악 | 공간 | 안정 |
|---------|------|------|------|------|------|
| 버블 정렬 | O(N) | O(N²) | O(N²) | O(1) | O |
| 삽입 정렬 | O(N) | O(N²) | O(N²) | O(1) | O |
| 선택 정렬 | O(N²) | O(N²) | O(N²) | O(1) | X |
| **퀵 정렬** | O(NlogN) | O(NlogN) | O(N²) | O(logN) | X |
| **병합 정렬** | O(NlogN) | O(NlogN) | O(NlogN) | O(N) | O |
| **힙 정렬** | O(NlogN) | O(NlogN) | O(NlogN) | O(1) | X |
| **계수 정렬** | O(N+K) | O(N+K) | O(N+K) | O(K) | O |

안정 정렬(Stable): 동일한 값의 원소들이 정렬 후에도 원래 순서 유지.

---

## 동작 원리

### 퀵 정렬 (Quick Sort)

피벗을 기준으로 작은 것 왼쪽, 큰 것 오른쪽으로 분할 → 재귀.

```
[3, 1, 4, 1, 5, 9, 2, 6]  피벗=4 (중간)

분할:
  [3, 1, 1, 2] | 4 | [5, 9, 6]
  왼쪽 재귀      피벗   오른쪽 재귀

최악의 경우:
  [1, 2, 3, 4, 5] 이미 정렬 + 맨 앞 피벗
  피벗=1 → [] | 1 | [2,3,4,5]  ← 분할 불균형
  N번 분할 × 각 N 비교 = O(N²)

해결: 랜덤 피벗 또는 Median-of-3 (앞/중간/뒤 중 중앙값)
```

왜 평균 O(N log N)인가:
```
균등 분할 시: T(N) = 2T(N/2) + O(N)
마스터 정리: T(N) = O(N log N)

실제로는 랜덤 피벗으로 평균 분할 비율 ≈ 1:1
→ 평균 O(N log N), 캐시 친화적 → 실무에서 가장 빠름
```

### 병합 정렬 (Merge Sort)

분할 → 정렬 → 합병. 항상 O(N log N) 보장.

```
[3, 1, 4, 1, 5, 2]
  → [3,1,4]   [1,5,2]     분할
  → [1,3,4]   [1,2,5]     각각 정렬
  → [1,1,2,3,4,5]          합병

합병 단계:
  왼쪽[0], 오른쪽[0] 비교 → 작은 것 결과에 추가
  → O(N)

재귀 깊이 = log N
총 비교 = N × log N = O(N log N)

단점: 합병 시 임시 배열 O(N) 필요
장점: 안정 정렬, 최악도 O(N log N) 보장 → 외부 정렬에 사용
```

### 힙 정렬 (Heap Sort)

Max Heap 구성 → 최댓값을 하나씩 꺼내 뒤로 보냄.

```
[3, 1, 4, 1, 5, 9, 2]
Max Heap 구성: [9, 5, 4, 1, 1, 3, 2]  O(N)
swap(arr[0], arr[N-1]) → 9를 맨 뒤로
Heapify: [5, 3, 4, 1, 1, 2] | 9
반복 → O(N log N)

특징: in-place O(1) 공간, 안정 정렬 아님
      실무에서는 퀵 정렬보다 캐시 미스 많아 느림
```

### 계수 정렬 (Counting Sort)

값의 범위 K가 작을 때 O(N+K).

```
arr = [3, 1, 2, 1, 3, 2, 1]  (값 범위: 1~3)

count = [0, 3, 2, 2]  (인덱스 = 값)
              ↑1이 3개, 2가 2개, 3이 2개

누적합: [0, 3, 5, 7]
결과 배열 역순 배치 → 안정 정렬

O(N+K): N=원소 수, K=값 범위
K가 크면 (예: 1억) → 공간 낭비 → 부적합
```

---

## 예시 코드 (Python)

```python
import random


# ── 퀵 정렬 ──────────────────────────────────────────

def quick_sort(arr: list, lo: int = 0, hi: int = None) -> list:
    if hi is None:
        arr = arr[:]
        hi = len(arr) - 1
    if lo >= hi:
        return arr

    # Median-of-3 피벗
    mid = (lo + hi) // 2
    candidates = [(arr[lo], lo), (arr[mid], mid), (arr[hi], hi)]
    pivot_val, pivot_idx = sorted(candidates)[1]
    arr[pivot_idx], arr[hi] = arr[hi], arr[pivot_idx]

    # Lomuto 파티션
    pivot = arr[hi]
    i = lo - 1
    for j in range(lo, hi):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i+1], arr[hi] = arr[hi], arr[i+1]
    p = i + 1

    quick_sort(arr, lo, p - 1)
    quick_sort(arr, p + 1, hi)
    return arr


# ── 병합 정렬 ─────────────────────────────────────────

def merge_sort(arr: list) -> list:
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left  = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)

def _merge(left: list, right: list) -> list:
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:   # <= 이므로 안정 정렬
            result.append(left[i]); i += 1
        else:
            result.append(right[j]); j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


# ── 힙 정렬 ───────────────────────────────────────────

def heap_sort(arr: list) -> list:
    arr = arr[:]
    N = len(arr)

    def heapify(n, i):          # 인덱스 i를 루트로 하는 서브트리 힙화
        largest = i
        l, r = 2*i+1, 2*i+2
        if l < n and arr[l] > arr[largest]: largest = l
        if r < n and arr[r] > arr[largest]: largest = r
        if largest != i:
            arr[i], arr[largest] = arr[largest], arr[i]
            heapify(n, largest)

    for i in range(N//2 - 1, -1, -1):  # Max Heap 구성 O(N)
        heapify(N, i)

    for i in range(N-1, 0, -1):        # 하나씩 추출
        arr[0], arr[i] = arr[i], arr[0]
        heapify(i, 0)
    return arr


# ── 계수 정렬 ─────────────────────────────────────────

def counting_sort(arr: list) -> list:
    if not arr:
        return []
    min_val, max_val = min(arr), max(arr)
    K = max_val - min_val + 1
    count = [0] * K
    for v in arr:
        count[v - min_val] += 1
    result = []
    for i, c in enumerate(count):
        result.extend([i + min_val] * c)
    return result


# ── 실전: 장비 목록 정렬 ─────────────────────────────

def sort_devices_by_priority(devices: list[dict]) -> list[dict]:
    """
    우선순위 + IP로 정렬 (병합 정렬 — 안정 정렬이라 순서 보장)
    우선순위 낮을수록 먼저, 같은 우선순위면 IP 오름차순
    """
    return sorted(devices, key=lambda d: (d["priority"], d["ip"]))


# ── 성능 비교 ────────────────────────────────────────

import time

def benchmark(name, func, arr):
    a = arr[:]
    start = time.perf_counter()
    func(a)
    elapsed = time.perf_counter() - start
    return elapsed

N = 5000
arr = [random.randint(0, N) for _ in range(N)]

print(f"N={N} 랜덤 배열 정렬 성능:")
for name, fn in [
    ("quick_sort ",  quick_sort),
    ("merge_sort ",  merge_sort),
    ("heap_sort  ",  heap_sort),
    ("Python sort",  lambda a: sorted(a)),
]:
    t = benchmark(name, fn, arr)
    print(f"  {name}: {t*1000:.2f}ms")

# 정렬 결과 검증
sample = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]
print(f"\n원본: {sample}")
print(f"퀵:   {quick_sort(sample)}")
print(f"병합: {merge_sort(sample)}")
print(f"힙:   {heap_sort(sample)}")
print(f"계수: {counting_sort(sample)}")

# 장비 정렬
devices = [
    {"name": "SW-A", "priority": 2, "ip": "192.168.1.3"},
    {"name": "SW-B", "priority": 1, "ip": "192.168.1.5"},
    {"name": "SW-C", "priority": 1, "ip": "192.168.1.1"},
    {"name": "SW-D", "priority": 2, "ip": "192.168.1.2"},
]
print("\n장비 우선순위 정렬:")
for d in sort_devices_by_priority(devices):
    print(f"  {d['name']} priority={d['priority']} ip={d['ip']}")
```

---

## 면접 예상 질문

- Q: 퀵 정렬의 최악 O(N²)이 발생하는 경우와 해결책은?
  A: 이미 정렬된 배열에서 맨 앞/뒤 원소를 피벗으로 선택하면 분할이 1:N-1로 편향되어 N번 재귀 × 각 N 비교 = O(N²). 해결: 랜덤 피벗(임의 위치 선택) 또는 Median-of-3(앞/중간/뒤 중 중앙값을 피벗으로). Python의 Timsort가 삽입 정렬+병합 정렬 혼합으로 이미 정렬된 배열에서 O(N).

- Q: 병합 정렬이 외부 정렬(디스크 정렬)에 적합한 이유는?
  A: 순차 접근 패턴. 데이터를 청크로 나눠 각각 정렬 후 합병 시 두 포인터가 앞에서 뒤로만 이동 → 디스크 순차 읽기에 최적. 퀵 정렬은 랜덤 접근이 많아 디스크 I/O 비효율. 대용량 DB 외부 정렬, 분산 정렬(MapReduce의 Shuffle)에 병합 정렬 사용.

- Q: 안정 정렬이 왜 중요한가?
  A: 같은 값의 원소들이 입력 순서를 유지해야 할 때. 예: 이름으로 정렬된 학생 목록을 점수로 재정렬 시, 같은 점수이면 이름 순서가 유지되어야 함. Python의 sort()/sorted()는 Timsort — 안정 정렬. 안정 정렬이 아닌 퀵/힙 정렬은 2차 정렬 기준이 필요하면 튜플로 키를 구성해야 함.

---

## 관련 개념

- [03-08 Heap](./03-08-heap.md) — 힙 정렬의 기반 자료구조
- [03-01 Big-O](./03-01-big-o.md) — 정렬의 하한 O(N log N)
