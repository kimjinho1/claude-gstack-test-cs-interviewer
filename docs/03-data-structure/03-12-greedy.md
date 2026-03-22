# 03-12 그리디 (Greedy)

## 개념

**그리디**: 매 단계에서 **현재 가장 좋아 보이는 선택**을 함. 전체 최적이 보장될 때만 사용.

```
DP: 모든 경우를 고려하여 최적해 보장
그리디: 현재 최선만 선택, 이전 선택 번복 안 함
       → 더 빠름, 단 항상 최적 아님

그리디가 최적인 조건:
  1. 최적 부분 구조 (Optimal Substructure)
  2. 탐욕적 선택 속성 (Greedy Choice Property)
     — 현재의 최선 선택이 미래에도 최선
```

---

## 동작 원리

### 대표 문제들

**거스름돈 문제** (그리디 O)
```
500, 100, 50, 10원으로 1260원 거스름돈:
  500 × 2 = 1000원
  100 × 2 = 200원
  50  × 1 = 50원
  10  × 1 = 10원
  합계: 6개

왜 그리디가 최적인가:
  큰 단위 화폐가 작은 단위의 배수 → 그리디 선택이 항상 최적

단, 임의 화폐 단위 (예: 1, 3, 4원)에서는 그리디 실패:
  6원 = 3+3 (2개) 최적
  그리디: 4+1+1 (3개) → DP 필요!
```

**활동 선택 문제** (Interval Scheduling)
```
회의실 예약 최대화: 겹치지 않는 최대 활동 수
활동: [(1,4), (3,5), (0,6), (5,7), (3,9), (5,9), (6,10), (8,11), (8,12), (2,14)]

그리디: 끝나는 시간이 빠른 것부터 선택
  정렬 후: [(1,4), (3,5), (0,6), (5,7), ...]
  선택: (1,4) → 다음 시작≥4: (5,7) → 다음 시작≥7: (8,11) → ...
  최대 4개 선택

왜 최적인가: 끝나는 시간이 빠를수록 이후 활동에 방해 적음
```

**허프만 코딩**
```
문자 빈도수에 따라 가변 길이 코드 부여:
빈도: a=45, b=13, c=12, d=16, e=9, f=5

Min Heap으로 빈도 낮은 것부터 합침:
  (5,f), (9,e) → 합: 14
  (12,c), (13,b) → 합: 25
  (14, [f,e]), (16,d) → 합: 30
  ...

결과: a=0, c=100, b=101, d=111, f=1100, e=1101
짧은 코드를 자주 쓰는 문자에 → 압축률 최대화
```

---

## 예시 코드 (Python)

```python
import heapq
from dataclasses import dataclass


# ── 거스름돈 ─────────────────────────────────────────

def coin_change_greedy(coins: list[int], amount: int) -> dict:
    """정렬된 화폐 단위일 때만 최적 보장"""
    coins = sorted(coins, reverse=True)
    result = {}
    for coin in coins:
        count = amount // coin
        if count:
            result[coin] = count
            amount -= coin * count
    return result if amount == 0 else {}


# ── 활동 선택 (Interval Scheduling) ─────────────────

def activity_selection(activities: list[tuple]) -> list[tuple]:
    """
    겹치지 않는 최대 활동 수 선택
    그리디: 끝 시간 오름차순 정렬 후 선택
    O(N log N)
    """
    sorted_acts = sorted(activities, key=lambda x: x[1])
    selected = [sorted_acts[0]]
    for start, end in sorted_acts[1:]:
        if start >= selected[-1][1]:   # 직전 끝나는 시간 이후 시작
            selected.append((start, end))
    return selected


# ── 구간 커버링 ───────────────────────────────────────

def min_intervals_to_cover(intervals: list[tuple], start: int, end: int) -> int:
    """
    [start, end]를 덮는 최소 구간 수
    그리디: 현재 위치에서 가장 멀리 뻗는 구간 선택
    활용: 네트워크 커버리지 최적화
    """
    intervals.sort()
    count, cur_end, i = 0, start, 0
    while cur_end < end:
        best = -1
        while i < len(intervals) and intervals[i][0] <= cur_end:
            best = max(best, intervals[i][1])
            i += 1
        if best == -1:
            return -1   # 커버 불가
        cur_end = best
        count += 1
    return count


# ── 허프만 코딩 ───────────────────────────────────────

class HuffmanNode:
    def __init__(self, char, freq):
        self.char  = char
        self.freq  = freq
        self.left  = self.right = None

    def __lt__(self, other): return self.freq < other.freq


def huffman_encoding(text: str) -> tuple[dict, str]:
    """
    허프만 코딩 — 최적 접두사 코드
    O(N log N) 빌드, O(L) 인코딩
    """
    from collections import Counter
    freq = Counter(text)
    heap = [HuffmanNode(ch, f) for ch, f in freq.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        l = heapq.heappop(heap)
        r = heapq.heappop(heap)
        merged = HuffmanNode(None, l.freq + r.freq)
        merged.left, merged.right = l, r
        heapq.heappush(heap, merged)

    # 코드 테이블 생성
    codes: dict[str, str] = {}
    def build_codes(node, code=""):
        if node is None: return
        if node.char is not None:
            codes[node.char] = code or "0"
            return
        build_codes(node.left,  code + "0")
        build_codes(node.right, code + "1")
    build_codes(heap[0])

    encoded = "".join(codes[ch] for ch in text)
    return codes, encoded


# ── 실행 ─────────────────────────────────────────────

print("=== 거스름돈 ===")
coins = [500, 100, 50, 10]
print(f"  1260원: {coin_change_greedy(coins, 1260)}")
print(f"  730원:  {coin_change_greedy(coins, 730)}")

print("\n=== 활동 선택 (회의실 최대화) ===")
meetings = [(1,4),(3,5),(0,6),(5,7),(3,9),(5,9),(6,10),(8,11)]
selected = activity_selection(meetings)
print(f"  전체 회의: {len(meetings)}개")
print(f"  선택:      {selected} ({len(selected)}개)")

print("\n=== 구간 커버링 ===")
segments = [(0,3),(2,5),(4,7),(6,9),(8,10)]
print(f"  [0,10] 커버 최소 구간: {min_intervals_to_cover(segments, 0, 10)}")

print("\n=== 허프만 코딩 ===")
text = "switch configuration backup vlan"
codes, encoded = huffman_encoding(text)
print(f"  원본: {len(text)*8}비트")
print(f"  압축: {len(encoded)}비트 ({len(encoded)/len(text)/8*100:.1f}%)")
print(f"  코드 테이블 (상위 5개):")
for ch, code in sorted(codes.items(), key=lambda x: len(x[1]))[:5]:
    print(f"    '{ch}'({text.count(ch)}회): {code}")
```

---

## 면접 예상 질문

- Q: 그리디가 항상 최적해를 내지 못하는 예는?
  A: 화폐 단위가 배수 관계가 아닌 경우. 예: 1, 3, 4원으로 6원 거슬러줄 때 그리디는 4+1+1=3개, 최적은 3+3=2개. 이 경우 DP 필요. 배낭 문제(0/1 Knapsack)도 그리디 불가 — 현재 가성비 최고를 선택해도 남은 공간 활용이 비최적일 수 있음. 분수 배낭(Fractional Knapsack)은 그리디 O.

- Q: 그리디와 DP의 선택 기준은?
  A: 탐욕적 선택 속성 확인. 현재의 최선 선택이 나중에도 최선임을 증명할 수 있으면 그리디. 확신 없으면 DP. 그리디는 O(N log N) 이하, DP는 보통 O(N²) 이상. 활동 선택, 허프만, MST(Kruskal/Prim)은 그리디로 증명됨.

- Q: 허프만 코딩이 최적 접두사 코드인 이유는?
  A: 빈도가 낮은 두 노드를 합쳐 트리를 구성하는 그리디 과정이 최적 접두사 코드를 보장함을 수학적으로 증명 가능. 접두사 코드(Prefix-Free Code) — 어떤 코드도 다른 코드의 접두사가 아님 → 디코딩 시 모호함 없음. 최소 기대 비트 수를 달성하는 유일한 접두사 코드.

---

## 관련 개념

- [03-11 DP](./03-11-dp.md) — 그리디로 안 풀리는 최적화 문제
- [03-08 Heap](./03-08-heap.md) — 그리디에서 Min Heap 활용
- [03-15 MST](./03-15-mst.md) — Kruskal, Prim이 그리디 알고리즘
