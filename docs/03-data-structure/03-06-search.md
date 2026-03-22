# 03-06 탐색 (BFS, DFS, 이진 탐색)

## 개념

**이진 탐색**: 정렬된 배열에서 O(log N) 탐색.
**DFS**: 깊이 우선 탐색 — 한 방향으로 끝까지 가고 백트래킹.
**BFS**: 너비 우선 탐색 — 가까운 것부터 레벨별로 탐색.

---

## 동작 원리

### 이진 탐색 (Binary Search)

정렬된 배열에서 중간값과 비교하며 탐색 범위를 절반씩 줄임.

```
arr = [1, 3, 5, 7, 9, 11, 13, 15]  target = 7

1단계: lo=0, hi=7, mid=3 → arr[3]=7 == target → 찾음!

target = 6 이라면:
1단계: mid=3, arr[3]=7 > 6  → hi=2
2단계: mid=1, arr[1]=3 < 6  → lo=2
3단계: mid=2, arr[2]=5 < 6  → lo=3
4단계: lo > hi → 없음

→ log₂8 = 3번 만에 탐색 완료
```

**주의: off-by-one 실수**
```python
# 흔한 실수
while lo < hi:   # lo == hi일 때 원소 1개 남음 → 검사 안 함!
    ...

# 올바른 형태
while lo <= hi:  # lo == hi: 원소 1개 남아도 검사
    mid = lo + (hi - lo) // 2  # (lo+hi)//2 는 overflow 위험 (C/Java)
```

**이진 탐색 변형**:
```
lower_bound: target 이상인 첫 번째 인덱스
upper_bound: target 초과인 첫 번째 인덱스

[1, 3, 3, 3, 5, 7]  target=3
lower_bound → 1  (index 1, 첫 번째 3)
upper_bound → 4  (index 4, 3 다음인 5의 위치)
```

### DFS (Depth-First Search)

스택(또는 재귀)으로 한 방향으로 끝까지 탐색 후 백트래킹.

```
그래프:
  A — B — D
  |       |
  C — E — F

DFS(A):
  방문: A
  → B (A의 첫 이웃)
    → D (B의 이웃)
      → F (D의 이웃)
        → E (F의 이웃)
          → C (E의 이웃)
  방문 순서: A → B → D → F → E → C

사용처: 경로 존재 여부, 사이클 감지, 위상 정렬,
        연결 요소 찾기, 미로 탈출
```

### BFS (Breadth-First Search)

큐로 가까운 노드부터 레벨별로 탐색.

```
그래프:
  A — B — D
  |       |
  C — E — F

BFS(A):
  Level 0: A
  Level 1: B, C
  Level 2: D, E
  Level 3: F
  방문 순서: A → B → C → D → E → F

사용처: 최단 경로(가중치 없는 그래프),
        최소 홉 수, 레벨별 탐색, 토폴로지 분석
```

**DFS vs BFS 선택 기준**:
```
최단 경로(최소 홉) → BFS
  이유: BFS는 레벨별로 탐색 → 처음 도달 = 최단

경로 존재 여부, 모든 경로 탐색 → DFS
  이유: 재귀/스택으로 구현 단순, 메모리 O(깊이)

BFS 메모리: 최악 O(N) — 한 레벨에 노드 전체
DFS 메모리: O(깊이) — 현재 경로만
```

---

## 예시 코드 (Python)

```python
from collections import deque
from typing import Optional
import bisect


# ── 이진 탐색 ─────────────────────────────────────────

def binary_search(arr: list, target) -> int:
    """기본 이진 탐색 — target 인덱스 반환, 없으면 -1"""
    lo, hi = 0, len(arr) - 1
    while lo <= hi:
        mid = lo + (hi - lo) // 2
        if arr[mid] == target:   return mid
        elif arr[mid] < target:  lo = mid + 1
        else:                    hi = mid - 1
    return -1


def lower_bound(arr: list, target) -> int:
    """target 이상인 첫 번째 인덱스 (삽입 위치)"""
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] < target: lo = mid + 1
        else:                  hi = mid
    return lo


def upper_bound(arr: list, target) -> int:
    """target 초과인 첫 번째 인덱스"""
    lo, hi = 0, len(arr)
    while lo < hi:
        mid = (lo + hi) // 2
        if arr[mid] <= target: lo = mid + 1
        else:                   hi = mid
    return lo


# 실전: 정렬된 VLAN 목록에서 범위 조회
def vlans_in_range(vlans: list[int], lo: int, hi: int) -> list[int]:
    """O(log N + K): lo~hi 범위의 VLAN 반환"""
    start = lower_bound(vlans, lo)
    end   = upper_bound(vlans, hi)
    return vlans[start:end]


# ── DFS 구현 (재귀 + 반복문) ─────────────────────────

Graph = dict[str, list[str]]

def dfs_recursive(graph: Graph, start: str,
                  visited: set = None) -> list[str]:
    if visited is None:
        visited = set()
    visited.add(start)
    result = [start]
    for neighbor in graph.get(start, []):
        if neighbor not in visited:
            result.extend(dfs_recursive(graph, neighbor, visited))
    return result


def dfs_iterative(graph: Graph, start: str) -> list[str]:
    stack, visited, result = [start], set(), []
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        result.append(node)
        # 역순 push → 원래 순서대로 방문
        for neighbor in reversed(graph.get(node, [])):
            if neighbor not in visited:
                stack.append(neighbor)
    return result


def has_path_dfs(graph: Graph, src: str, dst: str) -> bool:
    """두 노드 간 경로 존재 여부 O(V+E)"""
    visited = set()
    def dfs(node):
        if node == dst: return True
        visited.add(node)
        return any(dfs(n) for n in graph.get(node, []) if n not in visited)
    return dfs(src)


def find_all_paths(graph: Graph, src: str, dst: str) -> list[list]:
    """모든 경로 탐색 (백트래킹)"""
    results = []
    def dfs(node, path, visited):
        if node == dst:
            results.append(path[:])
            return
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                dfs(neighbor, path, visited)
                path.pop()
                visited.remove(neighbor)
    dfs(src, [src], {src})
    return results


# ── BFS 구현 ─────────────────────────────────────────

def bfs(graph: Graph, start: str) -> list[str]:
    queue, visited = deque([start]), {start}
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return result


def bfs_shortest_path(graph: Graph, src: str, dst: str) -> Optional[list]:
    """BFS 최단 경로 (홉 수 기준) O(V+E)"""
    queue   = deque([(src, [src])])
    visited = {src}
    while queue:
        node, path = queue.popleft()
        if node == dst:
            return path
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return None


def bfs_levels(graph: Graph, start: str) -> dict[str, int]:
    """각 노드까지의 홉 수(레벨)"""
    level = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in graph.get(node, []):
            if neighbor not in level:
                level[neighbor] = level[node] + 1
                queue.append(neighbor)
    return level


# ── 실행 ─────────────────────────────────────────────

print("=== 이진 탐색 ===")
arr = sorted([3, 1, 4, 1, 5, 9, 2, 6, 5, 3])
print(f"정렬 배열: {arr}")
print(f"  탐색(5):  인덱스 {binary_search(arr, 5)}")
print(f"  탐색(7):  인덱스 {binary_search(arr, 7)}")
print(f"  lower(3): {lower_bound(arr, 3)}")
print(f"  upper(3): {upper_bound(arr, 3)}")

vlans = [10, 20, 30, 40, 50, 100, 200]
print(f"\n  VLAN 15~50 범위: {vlans_in_range(vlans, 15, 50)}")

# 스위치 토폴로지
topology: Graph = {
    "Core":  ["Dist1", "Dist2"],
    "Dist1": ["Core", "Access1", "Access2"],
    "Dist2": ["Core", "Access3"],
    "Access1": ["Dist1"],
    "Access2": ["Dist1", "Access3"],
    "Access3": ["Dist2", "Access2"],
}

print("\n=== DFS ===")
print(f"  재귀: {dfs_recursive(topology, 'Core')}")
print(f"  반복: {dfs_iterative(topology, 'Core')}")
print(f"  경로 존재(Core→Access3): {has_path_dfs(topology, 'Core', 'Access3')}")
print(f"  모든 경로(Core→Access3): {find_all_paths(topology, 'Core', 'Access3')}")

print("\n=== BFS ===")
print(f"  탐색 순서: {bfs(topology, 'Core')}")
print(f"  최단 경로(Core→Access3): {bfs_shortest_path(topology, 'Core', 'Access3')}")
hops = bfs_levels(topology, 'Core')
print(f"  홉 수: {hops}")
```

---

## 면접 예상 질문

- Q: BFS와 DFS의 시간/공간 복잡도와 선택 기준은?
  A: 둘 다 O(V+E). 공간: BFS O(V) — 한 레벨 노드 큐, DFS O(깊이) — 재귀/스택. 최단 경로(가중치 없음)는 BFS — 처음 도달이 최단 보장. 경로 존재 여부, 모든 경로 탐색, 사이클 감지, 위상 정렬은 DFS. 그래프가 넓고 얕으면 DFS, 깊고 좁으면 BFS가 메모리 효율적.

- Q: 이진 탐색에서 `mid = (lo+hi)//2`의 문제는?
  A: 정수 오버플로우. C/Java에서 lo+hi가 int 범위(2^31-1) 초과 가능. Python은 무한 정수이므로 문제없지만 `lo + (hi-lo)//2`로 쓰는 게 올바른 습관. 또한 `while lo < hi` vs `while lo <= hi` 조건 차이도 자주 실수 — 원소 1개 남았을 때 탐색하려면 `<=`.

- Q: DFS로 사이클을 감지하는 방법은?
  A: 재귀 DFS에서 방문 상태를 3가지로 관리: WHITE(미방문), GRAY(현재 스택에 있음), BLACK(완전히 처리됨). 이웃 노드가 GRAY이면 사이클. 혹은 유니온-파인드(Disjoint Set)로 간선 추가 시 같은 컴포넌트이면 사이클.

---

## 관련 개념

- [03-03 Stack/Queue](./03-03-stack-queue-deque.md) — DFS(스택), BFS(큐) 구현
- [03-09 Graph](./03-09-graph.md) — 그래프 표현 방식
- [03-14 최단 경로](./03-14-shortest-path.md) — 가중치 그래프의 최단 경로
