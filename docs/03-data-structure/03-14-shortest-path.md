# 03-14 최단 경로 (Dijkstra, Bellman-Ford, Floyd)

## 개념

| 알고리즘 | 음수 가중치 | 음수 사이클 감지 | 복잡도 | 용도 |
|---------|-----------|---------------|-------|------|
| **Dijkstra** | 불가 | 불가 | O((V+E) log V) | 단일 출발, 양수 가중치 |
| **Bellman-Ford** | 가능 | 가능 | O(VE) | 단일 출발, 음수 간선 |
| **Floyd-Warshall** | 가능 | 가능 | O(V³) | 모든 쌍 최단 경로 |

---

## 동작 원리

### Dijkstra

그리디 + Min Heap. 항상 현재 가장 짧은 거리의 노드를 처리.

```
그래프:
  A --1-- B --2-- D
  |       |
  4       3
  |       |
  C --1-- E

dist 초기: A=0, 나머지 ∞

1. A 처리: B=1, C=4  Heap: [(1,B),(4,C)]
2. B 처리(dist=1): D=1+2=3, E=1+3=4  Heap: [(3,D),(4,C),(4,E)]
3. D 처리(dist=3): (이웃 없음)
4. C 처리(dist=4): (E=4+1=5 > 기존 4)
5. E 처리(dist=4): (완료)

결과: A→D 최단 = A→B→D = 3
```

**왜 음수 가중치에서 실패하는가**:
```
A --2-- B --(-3)-- C
|
3
|
D

Dijkstra: A 처리 후 B(dist=2)를 먼저 처리.
하지만 A→B→C = 2+(-3) = -1인데
이미 B를 처리했으므로 C의 최단 경로를 놓칠 수 있음.
```

### Bellman-Ford

모든 간선을 V-1번 완화(Relaxation). 음수 사이클: V번째도 완화되면 감지.

```
V-1번 반복 이유:
  최단 경로는 최대 V-1개 간선을 포함
  → V-1번 완화하면 모든 최단 경로 반드시 발견

완화 (Relaxation):
  if dist[v] > dist[u] + weight(u,v):
      dist[v] = dist[u] + weight(u,v)
```

### Floyd-Warshall

모든 노드 쌍의 최단 경로. 중간 경유 노드를 하나씩 추가.

```
dp[k][i][j] = 노드 1~k를 경유해 i→j 최단 거리
dp[k][i][j] = min(dp[k-1][i][j],
                  dp[k-1][i][k] + dp[k-1][k][j])
→ k를 경유하는 게 나은지 아닌지

공간 최적화: dp[i][j]만 유지 (k 차원 압축)
```

---

## 예시 코드 (Python)

```python
import heapq
from collections import defaultdict

INF = float('inf')
Graph = dict[str, list[tuple]]  # {node: [(neighbor, weight), ...]}


# ── Dijkstra ─────────────────────────────────────────

def dijkstra(graph: Graph, start: str) -> tuple[dict, dict]:
    """
    단일 출발 최단 경로 — O((V+E) log V)
    returns: (거리 dict, 이전 노드 dict)
    """
    dist = defaultdict(lambda: INF)
    prev = {}
    dist[start] = 0
    heap = [(0, start)]   # (거리, 노드)

    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:   # 이미 더 짧은 경로로 처리됨
            continue
        for v, w in graph.get(u, []):
            new_dist = dist[u] + w
            if new_dist < dist[v]:
                dist[v] = new_dist
                prev[v] = u
                heapq.heappush(heap, (new_dist, v))

    return dict(dist), prev


def reconstruct_path(prev: dict, start: str, end: str) -> list:
    path = []
    node = end
    while node != start:
        if node not in prev:
            return []
        path.append(node)
        node = prev[node]
    path.append(start)
    return path[::-1]


# ── Bellman-Ford ──────────────────────────────────────

def bellman_ford(edges: list[tuple], vertices: list, start: str) -> tuple:
    """
    단일 출발, 음수 간선 허용 — O(VE)
    edges: [(u, v, weight), ...]
    returns: (dist dict, 음수 사이클 여부)
    """
    dist = {v: INF for v in vertices}
    dist[start] = 0

    # V-1번 완화
    for _ in range(len(vertices) - 1):
        updated = False
        for u, v, w in edges:
            if dist[u] != INF and dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                updated = True
        if not updated:
            break

    # V번째 완화 시도 → 음수 사이클 감지
    has_negative_cycle = False
    for u, v, w in edges:
        if dist[u] != INF and dist[u] + w < dist[v]:
            has_negative_cycle = True
            break

    return dist, has_negative_cycle


# ── Floyd-Warshall ────────────────────────────────────

def floyd_warshall(vertices: list, edges: list[tuple]) -> dict:
    """
    모든 쌍 최단 경로 — O(V³)
    edges: [(u, v, weight), ...]
    """
    dist = {v: {u: INF for u in vertices} for v in vertices}
    for v in vertices:
        dist[v][v] = 0
    for u, v, w in edges:
        dist[u][v] = min(dist[u][v], w)

    for k in vertices:        # 경유 노드
        for i in vertices:    # 출발
            for j in vertices:  # 도착
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]

    return dist


# ── 실전: 스위치 네트워크 최단 경로 ──────────────────

def network_shortest_paths():
    # 가중치 = 링크 비용 (지연, 홉 수 등)
    topology: Graph = {
        "Core1":   [("Dist1", 1), ("Dist2", 2)],
        "Dist1":   [("Core1", 1), ("Access1", 3), ("Access2", 2)],
        "Dist2":   [("Core1", 2), ("Access3", 1), ("Access2", 3)],
        "Access1": [("Dist1", 3)],
        "Access2": [("Dist1", 2), ("Dist2", 3)],
        "Access3": [("Dist2", 1)],
    }

    dist, prev = dijkstra(topology, "Core1")
    print("  Core1에서의 최단 거리:")
    for node, d in sorted(dist.items()):
        path = reconstruct_path(prev, "Core1", node)
        print(f"    {node:10s}: {d}  경로={' → '.join(path)}")

    # 링크 비용 포함 전체 쌍 (Floyd)
    vertices = list(topology.keys())
    edges = [(u, v, w) for u, neighbors in topology.items()
             for v, w in neighbors]
    fw = floyd_warshall(vertices, edges)
    print(f"\n  Access1 → Access3 최단: {fw['Access1']['Access3']}")


# ── 실행 ─────────────────────────────────────────────

print("=== 스위치 네트워크 최단 경로 (Dijkstra) ===")
network_shortest_paths()

print("\n=== Bellman-Ford (음수 간선 포함) ===")
vertices = ["A", "B", "C", "D"]
edges = [("A","B",4), ("A","C",2), ("B","C",-1), ("B","D",5), ("C","D",3)]
dist, neg_cycle = bellman_ford(edges, vertices, "A")
print(f"  음수 사이클: {neg_cycle}")
for v, d in sorted(dist.items()):
    print(f"  A → {v}: {d}")
```

---

## 면접 예상 질문

- Q: Dijkstra가 음수 가중치에서 실패하는 이유는?
  A: 그리디 가정 위반. Dijkstra는 "처리된 노드의 거리가 최종"이라 가정. 음수 간선이 있으면 이미 처리한 노드에 더 짧은 경로가 나중에 발견될 수 있음. Bellman-Ford는 V-1번 모든 간선을 완화해 이를 처리.

- Q: Floyd-Warshall은 언제 사용하나?
  A: 모든 쌍의 최단 경로가 필요할 때. V가 작고(수백 이하) 간선이 많은 Dense 그래프에서 유리. O(V³)이므로 V=1000이면 10억 연산 → 실용적으로 V≤500 정도. 라우팅 프로토콜 OSPF에서 링크 상태 정보로 모든 경로 계산 시 유사한 원리 사용.

- Q: 네트워크 라우팅 프로토콜과 최단 경로 알고리즘의 관계는?
  A: OSPF(Link State): 각 라우터가 전체 토폴로지를 파악 후 Dijkstra로 최단 경로 계산. RIP(Distance Vector): Bellman-Ford 기반, 이웃과 거리 정보 교환. BGP: 정책 기반으로 단순 최단 경로 아님.

---

## 관련 개념

- [03-08 Heap](./03-08-heap.md) — Dijkstra의 Min Heap
- [03-09 Graph](./03-09-graph.md) — 그래프 표현
- [03-15 MST](./03-15-mst.md) — 최단 경로 vs 최소 신장 트리
