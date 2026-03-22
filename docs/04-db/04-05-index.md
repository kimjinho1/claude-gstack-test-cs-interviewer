# 04-05 인덱스 (B-Tree, 클러스터/논클러스터)

## 개념

**인덱스(Index)**: 데이터 조회 속도를 높이기 위한 별도의 자료구조. 책의 목차처럼 원하는 데이터의 위치를 빠르게 찾음.

```
인덱스 없음: 전체 테이블 스캔 O(N)
인덱스 있음: B-Tree 탐색 O(log N), 해시 O(1)

비용: 인덱스는 추가 저장 공간 + INSERT/UPDATE/DELETE 시 인덱스 유지 비용
```

---

## 동작 원리

### B-Tree 인덱스

```
B-Tree (Balanced Tree): 모든 리프 노드의 깊이 동일 → O(log N) 보장

내부 구조:
       [30 | 60]
      /    |    \
  [10|20] [40|50] [70|80|90]
    ↓↓      ↓↓      ↓↓↓
  (실제 행 포인터 또는 PK)

탐색: id=45 찾기
  루트: 45 > 30, 45 < 60 → 중간 노드
  [40|50]: 45 > 40, 45 < 50 → 리프 노드 사이
  없으면 NULL

B+ Tree (실제 DBMS 사용):
  - 리프 노드에만 실제 데이터 포인터
  - 리프 노드들이 연결 리스트로 연결 → 범위 조회 O(K) 효율적
  - BETWEEN, >, < 등 범위 쿼리에 강점
```

### 클러스터 인덱스 vs 논클러스터 인덱스

```
클러스터 인덱스 (Clustered Index):
  - 인덱스 순서 = 실제 데이터 저장 순서
  - 테이블당 1개만 가능 (InnoDB: PK가 자동으로 클러스터 인덱스)
  - 범위 조회 매우 빠름 (연속 블록 I/O)
  - INSERT 시 물리적 정렬 유지 비용

논클러스터 인덱스 (Non-Clustered / Secondary Index):
  - 인덱스에 PK값만 저장 → 실제 데이터는 PK로 다시 조회
  - 테이블당 여러 개 가능
  - 추가 I/O 1번 더 발생 (인덱스 → PK → 실제 데이터)

InnoDB 예:
  클러스터: PK(id) 기준으로 데이터 파일 정렬
  세컨더리: status 인덱스 → id 값 → 클러스터 인덱스로 재조회
```

### 커버링 인덱스

```
SELECT hostname, status FROM devices WHERE status = 'active'
인덱스: (status, hostname) — 두 컬럼 모두 인덱스에 있음

→ 인덱스만으로 쿼리 완성 (테이블 접근 불필요)
→ 커버링 인덱스 (Covering Index)

vs 일반 인덱스:
  인덱스 (status만) → status로 탐색 → id 찾기 → 테이블에서 hostname 조회 (추가 I/O)
```

### 인덱스를 쓰지 말아야 할 경우

```
1. 카디널리티가 낮은 컬럼: status ('up'/'down') — 전체의 50% → 풀스캔이 나을 수도
2. 자주 수정되는 컬럼: 인덱스 재정렬 비용
3. 소용량 테이블: 풀스캔이 더 빠름
4. 함수/연산 적용 컬럼: WHERE UPPER(name)='X' → 인덱스 무효
5. LIKE '%keyword%': 앞에 와일드카드 → B-Tree 탐색 불가 (LIKE 'keyword%'는 가능)
```

### 복합 인덱스 (Composite Index)

```
INDEX (site_id, status, type)

최좌 접두사 규칙 (Leftmost Prefix):
  ✓ WHERE site_id = 1
  ✓ WHERE site_id = 1 AND status = 'up'
  ✓ WHERE site_id = 1 AND status = 'up' AND type = 'switch'
  ✗ WHERE status = 'up'             ← site_id 없음
  ✗ WHERE site_id = 1 AND type = 'switch'  ← status 건너뜀

순서 중요: 카디널리티 높은 것을 앞에 (site_id > status > type)
```

---

## 예시 코드 (Python)

```python
import sqlite3
import time
import random


# ── 인덱스 성능 비교 시연 ────────────────────────────

def create_test_data(conn, n: int = 10000):
    conn.execute("""
        CREATE TABLE devices (
            id       INTEGER PRIMARY KEY,
            hostname TEXT,
            ip       TEXT,
            status   TEXT,
            site_id  INTEGER,
            type     TEXT
        )
    """)
    statuses = ['up', 'down']
    types    = ['switch', 'router', 'ap', 'firewall']
    batch = [
        (i, f"device-{i:05d}", f"10.{i//256}.{i%256}.1",
         random.choice(statuses), random.randint(1, 100),
         random.choice(types))
        for i in range(n)
    ]
    conn.executemany(
        "INSERT INTO devices VALUES (?,?,?,?,?,?)", batch
    )
    conn.commit()


def measure(conn, sql: str, label: str, repeat: int = 100) -> float:
    start = time.perf_counter()
    for _ in range(repeat):
        conn.execute(sql).fetchall()
    elapsed = (time.perf_counter() - start) / repeat * 1000
    print(f"  {label:40s}: {elapsed:.3f} ms/query")
    return elapsed


def index_performance_demo():
    conn = sqlite3.connect(":memory:")
    create_test_data(conn, 50000)

    q_site  = "SELECT hostname, ip FROM devices WHERE site_id = 42"
    q_range = "SELECT hostname FROM devices WHERE site_id BETWEEN 10 AND 20"
    q_comp  = "SELECT hostname FROM devices WHERE site_id=42 AND status='up'"
    q_cover = "SELECT hostname, status FROM devices WHERE site_id=42 AND status='up'"

    print("[인덱스 없음]")
    t_no_idx = measure(conn, q_site, "site_id = 42 (풀스캔)")

    # 단일 인덱스
    conn.execute("CREATE INDEX idx_site ON devices(site_id)")
    print("\n[단일 인덱스: site_id]")
    t_idx = measure(conn, q_site, "site_id = 42")
    measure(conn, q_range, "site_id BETWEEN 10 AND 20 (범위)")

    # 복합 인덱스
    conn.execute("CREATE INDEX idx_site_status ON devices(site_id, status)")
    print("\n[복합 인덱스: (site_id, status)]")
    measure(conn, q_comp, "site_id=42 AND status='up'")

    # 커버링 인덱스
    conn.execute("CREATE INDEX idx_cover ON devices(site_id, status, hostname)")
    print("\n[커버링 인덱스: (site_id, status, hostname)]")
    measure(conn, q_cover, "커버링 — 테이블 접근 불필요")

    print(f"\n  → 인덱스 효과: {t_no_idx:.3f} ms → {t_idx:.3f} ms "
          f"({t_no_idx/t_idx:.0f}x 빠름)")

    conn.close()


# ── B-Tree 직접 구현 (시각화용) ─────────────────────

class BTreeNode:
    def __init__(self, leaf=False):
        self.keys:     list = []
        self.values:   list = []   # 리프: 실제 rowid, 내부: 자식 포인터
        self.children: list = []
        self.leaf:     bool = leaf

    def __repr__(self):
        return f"BTreeNode(keys={self.keys}, leaf={self.leaf})"


class SimpleBTree:
    """단순화된 B-Tree (시각화 목적, t=2 최소 차수)"""
    T = 2   # 최소 차수 → 각 노드 최대 2T-1=3 키

    def __init__(self):
        self.root = BTreeNode(leaf=True)

    def search(self, key, node=None) -> tuple:
        """O(log N) 탐색"""
        node = node or self.root
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
        if i < len(node.keys) and key == node.keys[i]:
            return (node, i)
        if node.leaf:
            return None
        return self.search(key, node.children[i])

    def insert(self, key, value):
        root = self.root
        if len(root.keys) == 2 * self.T - 1:
            new_root = BTreeNode()
            new_root.children.append(self.root)
            self._split_child(new_root, 0)
            self.root = new_root
        self._insert_non_full(self.root, key, value)

    def _split_child(self, parent, i):
        T = self.T
        child = parent.children[i]
        new_node = BTreeNode(leaf=child.leaf)
        mid = T - 1
        parent.keys.insert(i, child.keys[mid])
        parent.values.insert(i, child.values[mid])
        parent.children.insert(i + 1, new_node)
        new_node.keys   = child.keys[mid + 1:]
        new_node.values = child.values[mid + 1:]
        child.keys   = child.keys[:mid]
        child.values = child.values[:mid]
        if not child.leaf:
            new_node.children = child.children[mid + 1:]
            child.children    = child.children[:mid + 1]

    def _insert_non_full(self, node, key, value):
        i = len(node.keys) - 1
        if node.leaf:
            node.keys.append(None)
            node.values.append(None)
            while i >= 0 and key < node.keys[i]:
                node.keys[i + 1]   = node.keys[i]
                node.values[i + 1] = node.values[i]
                i -= 1
            node.keys[i + 1]   = key
            node.values[i + 1] = value
        else:
            while i >= 0 and key < node.keys[i]:
                i -= 1
            i += 1
            if len(node.children[i].keys) == 2 * self.T - 1:
                self._split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self._insert_non_full(node.children[i], key, value)


def btree_demo():
    btree = SimpleBTree()
    keys = [10, 20, 5, 6, 12, 30, 7, 17]
    for k in keys:
        btree.insert(k, f"row_{k}")

    print("\n[B-Tree 탐색]")
    for k in [6, 17, 99]:
        result = btree.search(k)
        print(f"  key={k}: {'찾음 → ' + result[0].values[result[1]] if result else '없음'}")


# ── 실행 ─────────────────────────────────────────────

print("=== 인덱스 성능 비교 ===")
index_performance_demo()

print("\n=== B-Tree 탐색 ===")
btree_demo()
```

---

## 면접 예상 질문

- Q: 인덱스의 자료구조로 B-Tree를 쓰는 이유는?
  A: ① O(log N) 탐색 보장 (균형 트리). ② B+ Tree의 리프 노드 연결 리스트 → 범위 조회(BETWEEN, >, <) 효율적. ③ 디스크 I/O 최적화 — 각 노드 크기 = 디스크 페이지(4KB~16KB)에 맞춰 한 번 읽기로 많은 키 탐색. ④ Hash 인덱스는 = 조회만 O(1), 범위 불가.

- Q: 클러스터 인덱스와 논클러스터 인덱스의 차이는?
  A: 클러스터 인덱스는 데이터 파일 자체가 인덱스 키 순으로 정렬 (InnoDB에서 PK). 테이블당 1개. 범위 조회 빠름. 논클러스터(세컨더리) 인덱스는 별도 자료구조에 키 + PK 저장 → 조회 시 PK로 클러스터 인덱스 한 번 더 탐색. 테이블당 여러 개 가능.

- Q: 인덱스가 오히려 느릴 수 있는 경우는?
  A: ① 카디널리티 낮은 컬럼(status=up/down) — 어차피 절반 스캔, 인덱스 overhead가 더 큼. ② 소용량 테이블 — 풀스캔이 더 빠름. ③ LIKE '%keyword%' — B-Tree의 좌측 접두사 탐색 불가. ④ 함수 적용(WHERE YEAR(created)=2024) — 인덱스 무효화. ⑤ UPDATE/INSERT 빈번한 컬럼 — 인덱스 유지 비용.

---

## 관련 개념

- [03-07 Tree](../03-data-structure/03-07-tree.md) — B-Tree 기반
- [04-08 쿼리 최적화](./04-08-query-optimization.md) — EXPLAIN으로 인덱스 확인
- [04-06 격리 수준](./04-06-isolation-level.md) — 인덱스 + 락의 관계
