# 03-09 Graph (그래프)

## 개념

**그래프**: 정점(Vertex)과 간선(Edge)으로 이루어진 자료구조. 트리는 그래프의 특수한 형태.

```
방향 그래프 (Directed):  A → B (단방향)
무방향 그래프 (Undirected): A — B (양방향)
가중치 그래프 (Weighted): 간선에 비용/거리 포함
```

---

## 동작 원리

### 그래프 표현 방식

#### 인접 행렬 (Adjacency Matrix)

```
정점 4개: A=0, B=1, C=2, D=3

     A  B  C  D
A  [ 0, 1, 0, 1 ]
B  [ 1, 0, 1, 0 ]
C  [ 0, 1, 0, 1 ]
D  [ 1, 0, 1, 0 ]

공간: O(V²)
간선 확인: O(1)  — matrix[u][v]
이웃 탐색: O(V)  — 행 전체 순회
적합: 정점 수 적고, 간선 많은 Dense 그래프
```

#### 인접 리스트 (Adjacency List)

```
A: [B, D]
B: [A, C]
C: [B, D]
D: [A, C]

공간: O(V + E)
간선 확인: O(차수)  — 리스트 순회
이웃 탐색: O(차수)  — 해당 리스트만
적합: 정점 많고, 간선 적은 Sparse 그래프 (대부분의 실무)
```

### 위상 정렬 (Topological Sort)

방향 비순환 그래프(DAG)에서 선행 관계를 지키며 나열.

```
작업 의존성:
  A → C (A 완료 후 C 가능)
  B → C, B → D
  C → E
  D → E

위상 정렬: A, B, C, D, E  또는  B, A, C, D, E  (여러 답 가능)
           (단, A/B가 C보다, C/D가 E보다 먼저)

방법: Kahn's Algorithm (BFS, 진입차수 사용)
```

### 유니온-파인드 (Union-Find / Disjoint Set)

연결 여부 판단, 사이클 감지에 특화. O(α(N)) ≈ O(1).

```
{ {A, B, C}, {D, E} }  두 컴포넌트

find(A) = A의 루트
find(D) = D의 루트

union(C, D):
  두 루트를 합침 → { {A, B, C, D, E} }

사이클 감지:
  간선 (u, v) 추가 시 find(u) == find(v) → 사이클!
```

---

## 예시 코드 (Python)

```python
from collections import defaultdict, deque
from typing import Optional


# ── 그래프 클래스 ─────────────────────────────────────

class Graph:
    def __init__(self, directed: bool = False):
        self.directed = directed
        self._adj: dict[str, list[tuple]] = defaultdict(list)
        self._vertices: set = set()

    def add_edge(self, u: str, v: str, weight: float = 1.0):
        self._adj[u].append((v, weight))
        self._vertices.update([u, v])
        if not self.directed:
            self._adj[v].append((u, weight))

    def neighbors(self, u: str) -> list[tuple]:
        return self._adj.get(u, [])

    @property
    def vertices(self) -> set:
        return self._vertices

    def degree(self, u: str) -> int:
        return len(self._adj.get(u, []))


# ── 위상 정렬 (Kahn's Algorithm) ──────────────────────

def topological_sort(graph: Graph) -> Optional[list]:
    """
    BFS 기반 위상 정렬 — O(V+E)
    사이클 있으면 None 반환

    활용: 네트워크 장비 설정 순서, 빌드 의존성, 배포 순서
    """
    in_degree = {v: 0 for v in graph.vertices}
    for u in graph.vertices:
        for v, _ in graph.neighbors(u):
            in_degree[v] += 1

    # 진입차수 0인 노드부터 시작
    queue = deque([v for v, d in in_degree.items() if d == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor, _ in graph.neighbors(node):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(graph.vertices):
        return None  # 사이클 존재
    return result


# ── 유니온-파인드 ─────────────────────────────────────

class UnionFind:
    """
    경로 압축 + 랭크 기반 합병 → O(α(N)) ≈ O(1)

    활용:
      - 네트워크 연결 컴포넌트
      - MST (Kruskal)
      - 사이클 감지
    """
    def __init__(self, nodes):
        self.parent = {n: n for n in nodes}
        self.rank   = {n: 0 for n in nodes}
        self._components = len(nodes)

    def find(self, x) -> str:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # 경로 압축
        return self.parent[x]

    def union(self, x, y) -> bool:
        """합병. 이미 같은 그룹이면 False (사이클)"""
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        # 랭크 기반 합병 (작은 트리를 큰 트리 아래로)
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        self._components -= 1
        return True

    def connected(self, x, y) -> bool:
        return self.find(x) == self.find(y)

    @property
    def num_components(self) -> int:
        return self._components


# ── 연결 컴포넌트 분석 ────────────────────────────────

def find_connected_components(graph: Graph) -> list[set]:
    """무방향 그래프의 연결 컴포넌트 — O(V+E)"""
    visited = set()
    components = []

    def bfs(start):
        component = set()
        queue = deque([start])
        visited.add(start)
        while queue:
            node = queue.popleft()
            component.add(node)
            for neighbor, _ in graph.neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return component

    for v in graph.vertices:
        if v not in visited:
            components.append(bfs(v))
    return components


# ── 실행 ─────────────────────────────────────────────

print("=== 스위치 토폴로지 그래프 ===")
g = Graph(directed=False)
edges = [
    ("Core1", "Dist1", 1), ("Core1", "Dist2", 1),
    ("Core2", "Dist1", 1), ("Core2", "Dist2", 1),
    ("Dist1", "Access1", 1), ("Dist1", "Access2", 1),
    ("Dist2", "Access3", 1),
]
for u, v, w in edges:
    g.add_edge(u, v, w)

print(f"  정점: {sorted(g.vertices)}")
print(f"  Core1 이웃: {[n for n,_ in g.neighbors('Core1')]}")

print("\n=== 연결 컴포넌트 ===")
# 독립 섬 추가
g2 = Graph(directed=False)
for u, v, w in edges:
    g2.add_edge(u, v, w)
g2.add_edge("Island-SW1", "Island-SW2", 1)  # 분리된 세그먼트

components = find_connected_components(g2)
print(f"  컴포넌트 수: {len(components)}")
for i, comp in enumerate(components):
    print(f"  컴포넌트 {i+1}: {sorted(comp)}")

print("\n=== 위상 정렬 (설정 의존성) ===")
dag = Graph(directed=True)
# 스위치 설정 순서: VLAN 먼저, 그 후 포트, 그 후 라우팅
deps = [
    ("VLAN설정", "포트설정"),
    ("VLAN설정", "SVI설정"),
    ("포트설정", "스패닝트리"),
    ("SVI설정", "라우팅"),
    ("스패닝트리", "라우팅"),
]
for u, v in deps:
    dag.add_edge(u, v)

order = topological_sort(dag)
print(f"  설정 순서: {' → '.join(order)}")

print("\n=== 유니온-파인드 (네트워크 분리 감지) ===")
switches = ["SW1", "SW2", "SW3", "SW4", "SW5"]
uf = UnionFind(switches)
links = [("SW1","SW2"), ("SW2","SW3"), ("SW4","SW5")]
for u, v in links:
    uf.union(u, v)

print(f"  연결 컴포넌트 수: {uf.num_components}")
print(f"  SW1-SW3 연결?: {uf.connected('SW1','SW3')}")
print(f"  SW1-SW4 연결?: {uf.connected('SW1','SW4')}")

# 링크 추가 시 사이클 감지
uf2 = UnionFind(["A","B","C"])
print(f"\n  A-B 연결: {uf2.union('A','B')}")
print(f"  B-C 연결: {uf2.union('B','C')}")
print(f"  A-C 연결 시도: {uf2.union('A','C')} ← False = 사이클 감지!")
```

---

## 면접 예상 질문

- Q: 인접 행렬과 인접 리스트의 선택 기준은?
  A: 정점 수 V, 간선 수 E. 인접 행렬은 O(V²) 공간이지만 간선 확인 O(1). 간선이 많은 Dense 그래프나 간선 존재 여부를 자주 확인할 때. 인접 리스트는 O(V+E) 공간. 간선이 적은 Sparse 그래프(소셜 네트워크, 라우팅 테이블)에 적합. 실무 대부분의 그래프는 Sparse → 인접 리스트.

- Q: 위상 정렬이란? 어떻게 구현하나?
  A: DAG(방향 비순환 그래프)에서 모든 간선 u→v에 대해 u가 v보다 앞에 오는 순서. Kahn's Algorithm: 진입차수(in-degree) 0인 노드를 큐에 넣고, 꺼내면서 이웃 진입차수를 줄임. 결과 길이가 V보다 작으면 사이클 존재. 배포 순서, 빌드 의존성, 수강 순서 등에 활용.

- Q: 유니온-파인드의 시간 복잡도 O(α(N))이란?
  A: α는 역아커만 함수. 실용적으로는 상수(5 이하). 경로 압축(find 시 루트까지 직결)과 랭크 기반 합병(작은 트리를 큰 트리 아래)을 결합 시 나타남. 사이클 감지, MST(Kruskal), 네트워크 연결성 확인에 표준적으로 사용.

---

## 관련 개념

- [03-06 탐색 BFS/DFS](./03-06-search.md) — 그래프 탐색
- [03-14 최단 경로](./03-14-shortest-path.md) — 가중치 그래프 탐색
- [03-15 MST](./03-15-mst.md) — 유니온-파인드로 Kruskal 구현
