# 04-08 실행 계획 / 쿼리 최적화

## 개념

**쿼리 옵티마이저**: SQL을 받아 실행 계획(Execution Plan)을 선택하는 DB 내부 컴포넌트. 통계 기반으로 최적 인덱스/조인 방식 선택.

```
SQL → 파서 → 옵티마이저 → 실행 계획 → 실행 엔진 → 결과
                ↑
            테이블 통계 (행 수, 인덱스 분포)
```

---

## 동작 원리

### EXPLAIN 읽는 법

```sql
EXPLAIN SELECT d.hostname, i.name
FROM devices d JOIN interfaces i ON d.id = i.device_id
WHERE d.site_id = 42 AND i.status = 'up';
```

```
MySQL EXPLAIN 출력:
id | select_type | table | type  | possible_keys    | key        | rows | Extra
1  | SIMPLE      | d     | ref   | idx_site         | idx_site   | 15   | Using index condition
1  | SIMPLE      | i     | ref   | idx_device_status| idx_device | 3    | Using where

핵심 컬럼:
  type:          접근 방식 (좋음 → 나쁨 순)
    const        PK/Unique로 1행 조회 (최선)
    eq_ref       조인에서 PK/Unique 1:1 매칭
    ref          인덱스로 여러 행 조회
    range        인덱스 범위 조회 (BETWEEN, >, <)
    index        인덱스 전체 스캔 (풀스캔보다 나음)
    ALL          풀 테이블 스캔 (최악)

  rows:  예상 검사 행 수 — 낮을수록 좋음
  Extra:
    Using index  커버링 인덱스 (테이블 접근 없음)
    Using where  필터링 있음
    Using filesort 정렬 (인덱스 정렬 불가)
    Using temporary 임시 테이블 (GROUP BY/DISTINCT)
```

### 느린 쿼리 패턴과 해결

```
1. Full Table Scan → 인덱스 추가
   WHERE hostname = 'sw-core-01'
   → CREATE INDEX idx_hostname ON devices(hostname)

2. 인덱스 무효화 패턴
   WHERE YEAR(created_at) = 2024   ← 함수 적용
   → WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31'

   WHERE status != 'down'          ← != 연산
   → WHERE status IN ('up', 'degraded')

   WHERE name LIKE '%core%'        ← 앞 와일드카드
   → Full Text Search 사용

3. N+1 문제 → 조인으로 해결
   나쁜 예:
     devices = SELECT * FROM devices WHERE site_id=1
     for each device:
         interfaces = SELECT * FROM interfaces WHERE device_id=?  ← N번!

   좋은 예:
     SELECT d.*, i.*
     FROM devices d
     LEFT JOIN interfaces i ON d.id = i.device_id
     WHERE d.site_id = 1

4. SELECT * → 필요한 컬럼만
   SELECT * FROM devices    ← 불필요 I/O
   SELECT id, hostname FROM devices

5. 페이지네이션 (OFFSET 성능)
   나쁜 예: LIMIT 10 OFFSET 10000  ← 10010행 읽고 앞 10000행 버림
   좋은 예: WHERE id > 마지막_id LIMIT 10  ← Keyset Pagination
```

### 실행 계획 강제 (힌트)

```sql
-- MySQL
SELECT /*+ INDEX(d idx_site) */ hostname FROM devices d WHERE site_id=42

-- PostgreSQL
SET enable_seqscan = OFF;  -- 풀스캔 비활성화 (테스트용)
```

---

## 예시 코드 (Python)

```python
import sqlite3
import time
import random


# ── 테스트 데이터 생성 ────────────────────────────────

def setup(conn, device_cnt=10000, iface_per_device=4):
    conn.executescript("""
        CREATE TABLE devices (
            id       INTEGER PRIMARY KEY,
            hostname TEXT,
            site_id  INTEGER,
            status   TEXT,
            type     TEXT
        );
        CREATE TABLE interfaces (
            id        INTEGER PRIMARY KEY,
            device_id INTEGER,
            name      TEXT,
            status    TEXT,
            speed     INTEGER
        );
    """)
    sites   = list(range(1, 101))
    statuses = ['up', 'down']
    types    = ['switch', 'router', 'ap']
    devices = [
        (i, f"device-{i:05d}", random.choice(sites),
         random.choice(statuses), random.choice(types))
        for i in range(device_cnt)
    ]
    conn.executemany("INSERT INTO devices VALUES (?,?,?,?,?)", devices)

    ifaces = [
        (i * iface_per_device + j, i, f"Gi0/{j}",
         random.choice(statuses), random.choice([100, 1000, 10000]))
        for i in range(device_cnt)
        for j in range(iface_per_device)
    ]
    conn.executemany("INSERT INTO interfaces VALUES (?,?,?,?,?)", ifaces)
    conn.commit()


def benchmark(conn, sql: str, label: str, repeat=50) -> float:
    start = time.perf_counter()
    for _ in range(repeat):
        conn.execute(sql).fetchall()
    ms = (time.perf_counter() - start) / repeat * 1000
    cnt = len(conn.execute(sql).fetchall())
    print(f"  {label:50s}: {ms:6.2f}ms (결과 {cnt}행)")
    return ms


# ── Full Scan vs Index ───────────────────────────────

def full_scan_vs_index(conn):
    q = "SELECT id, hostname FROM devices WHERE site_id = 42"

    print("[Full Scan vs Index 비교]")
    t1 = benchmark(conn, q, "site_id=42 (인덱스 없음)")

    conn.execute("CREATE INDEX idx_site ON devices(site_id)")
    t2 = benchmark(conn, q, "site_id=42 (인덱스 있음)")

    print(f"  → {t1/t2:.0f}x 향상")


# ── 인덱스 무효화 패턴 ───────────────────────────────

def index_invalidation(conn):
    conn.execute("CREATE INDEX idx_status ON devices(status)")
    conn.execute("CREATE INDEX idx_speed  ON interfaces(speed)")
    conn.commit()

    print("\n[인덱스 무효화 패턴]")

    # 나쁜 예: 함수 적용
    benchmark(conn,
        "SELECT id FROM interfaces WHERE speed * 1 = 1000",
        "WHERE speed * 1 = 1000 (함수로 인덱스 무효)")

    # 좋은 예: 함수 제거
    benchmark(conn,
        "SELECT id FROM interfaces WHERE speed = 1000",
        "WHERE speed = 1000 (인덱스 사용)")


# ── N+1 문제 ─────────────────────────────────────────

def n_plus_one_demo(conn):
    print("\n[N+1 문제]")
    devices = conn.execute(
        "SELECT id, hostname FROM devices WHERE site_id=42"
    ).fetchall()

    # N+1 방식 (나쁜 예)
    start = time.perf_counter()
    for dev_id, hostname in devices:
        conn.execute(
            "SELECT COUNT(*) FROM interfaces WHERE device_id=? AND status='up'",
            (dev_id,)
        ).fetchone()
    t_n1 = (time.perf_counter() - start) * 1000

    # 1+1 방식 (좋은 예: JOIN)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_dev_status ON interfaces(device_id, status)")
    start = time.perf_counter()
    conn.execute("""
        SELECT d.id, d.hostname, COUNT(i.id) AS up_cnt
        FROM devices d
        LEFT JOIN interfaces i ON d.id = i.device_id AND i.status='up'
        WHERE d.site_id = 42
        GROUP BY d.id, d.hostname
    """).fetchall()
    t_join = (time.perf_counter() - start) * 1000

    print(f"  N+1 쿼리 ({len(devices)}회): {t_n1:.2f}ms")
    print(f"  JOIN 1회:                  {t_join:.2f}ms")
    print(f"  → {t_n1/max(t_join,0.1):.0f}x 향상")


# ── 페이지네이션: OFFSET vs Keyset ───────────────────

def pagination_demo(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS idx_id ON devices(id)")
    conn.commit()

    print("\n[페이지네이션: OFFSET vs Keyset]")

    # OFFSET 방식 (느려짐)
    offsets = [0, 1000, 5000, 9000]
    for offset in offsets:
        t = time.perf_counter()
        for _ in range(20):
            conn.execute(
                f"SELECT id, hostname FROM devices ORDER BY id LIMIT 10 OFFSET {offset}"
            ).fetchall()
        ms = (time.perf_counter() - t) / 20 * 1000
        print(f"  OFFSET {offset:5d}: {ms:.3f}ms")

    # Keyset 방식 (항상 빠름)
    last_ids = [0, 1000, 5000, 9000]
    print()
    for last_id in last_ids:
        t = time.perf_counter()
        for _ in range(20):
            conn.execute(
                "SELECT id, hostname FROM devices WHERE id > ? ORDER BY id LIMIT 10",
                (last_id,)
            ).fetchall()
        ms = (time.perf_counter() - t) / 20 * 1000
        print(f"  Keyset after {last_id:5d}: {ms:.3f}ms")


# ── 실행 계획 출력 (SQLite EXPLAIN QUERY PLAN) ───────

def explain_demo(conn):
    print("\n[EXPLAIN QUERY PLAN]")
    queries = [
        "SELECT hostname FROM devices WHERE id = 42",
        "SELECT hostname FROM devices WHERE site_id = 42",
        "SELECT hostname FROM devices WHERE status = 'up'",
        "SELECT d.hostname, COUNT(i.id) FROM devices d LEFT JOIN interfaces i ON d.id=i.device_id WHERE d.site_id=42 GROUP BY d.id",
    ]
    for sql in queries:
        plan = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
        detail = plan[0][3] if plan else "?"
        print(f"  SQL: ...{sql[30:60]}...")
        print(f"  Plan: {detail}\n")


# ── 실행 ─────────────────────────────────────────────

conn = sqlite3.connect(":memory:")
setup(conn)

print("=== 쿼리 최적화 시연 ===")
full_scan_vs_index(conn)
index_invalidation(conn)
n_plus_one_demo(conn)
pagination_demo(conn)
explain_demo(conn)
```

---

## 면접 예상 질문

- Q: EXPLAIN에서 type=ALL이 나왔을 때 대처 방법은?
  A: Full Table Scan 발생. ① WHERE 컬럼에 인덱스 추가. ② 인덱스 무효화 패턴 제거(함수 적용, LIKE '%...', != 연산). ③ 복합 인덱스 고려 (최좌 접두사 확인). ④ 통계 갱신(ANALYZE). rows 수가 많고 type=ALL 조합이면 즉시 최적화 필요.

- Q: N+1 문제란? 어떻게 해결하나?
  A: ORM/반복문에서 N개 결과를 조회한 후 각각에 대해 추가 쿼리를 N번 실행하는 문제. 총 N+1번의 DB 왕복. 해결: ① JOIN으로 한 번에 조회. ② ORM의 eager loading(include/prefetch_related). ③ IN 절로 일괄 조회(SELECT WHERE id IN (...)).

- Q: 페이지네이션에서 OFFSET의 문제는?
  A: OFFSET N은 DB가 앞의 N행을 읽고 버린 후 다음 페이지를 반환. 페이지가 뒤로 갈수록 N이 커져 O(N) 성능 저하. 해결: Keyset Pagination (WHERE id > 마지막_id LIMIT N) — 인덱스로 바로 시작점 탐색, 항상 O(log N).

---

## 관련 개념

- [04-05 인덱스](./04-05-index.md) — 실행 계획의 핵심
- [04-03 조인](./04-03-join.md) — 조인 알고리즘
- [04-06 격리 수준](./04-06-isolation-level.md) — 락 대기 문제
