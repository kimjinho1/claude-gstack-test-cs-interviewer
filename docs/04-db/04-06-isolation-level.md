# 04-06 격리 수준 (Isolation Level)

## 개념

**격리 수준**: 동시 실행 트랜잭션 간의 간섭 허용 범위. 높을수록 안전하지만 성능(동시성) 저하.

---

## 동작 원리

### 격리 문제 3가지

```
① Dirty Read (더티 읽기):
   T1이 수정하고 커밋 전 → T2가 읽음 → T1이 롤백 → T2는 존재하지 않는 데이터 읽은 것

② Non-Repeatable Read (반복 불가능 읽기):
   T1이 동일 쿼리를 두 번 실행 → 사이에 T2가 UPDATE/DELETE 커밋 → 결과 달라짐

③ Phantom Read (팬텀 읽기):
   T1이 범위 조건 쿼리 두 번 실행 → 사이에 T2가 INSERT 커밋 → 행 수 달라짐
```

### 격리 수준 4단계

| 수준 | Dirty Read | Non-Repeatable | Phantom |
|------|-----------|----------------|---------|
| **READ UNCOMMITTED** | 발생 | 발생 | 발생 |
| **READ COMMITTED** | 방지 | 발생 | 발생 |
| **REPEATABLE READ** | 방지 | 방지 | 발생 (InnoDB는 방지) |
| **SERIALIZABLE** | 방지 | 방지 | 방지 |

```
MySQL InnoDB 기본값: REPEATABLE READ
PostgreSQL 기본값: READ COMMITTED

실무:
  대부분의 웹 서비스: READ COMMITTED
  금융/결제: REPEATABLE READ 이상
  SERIALIZABLE: 매우 낮은 동시성 → 거의 미사용
```

### MVCC (Multi-Version Concurrency Control)

```
InnoDB가 Dirty Read 없이 높은 동시성을 유지하는 핵심 메커니즘.

원리:
  - 데이터 변경 시 기존 버전을 Undo Log에 보존
  - 읽기 트랜잭션은 자신의 시작 시점 스냅샷 읽음 → 락 없이 읽기 가능
  - 쓰기 트랜잭션만 락 필요

READ COMMITTED: 매 쿼리마다 최신 커밋 스냅샷
REPEATABLE READ: 트랜잭션 시작 시점 스냅샷 고정 (같은 쿼리 → 같은 결과)

예:
  T1 시작 (트랜잭션 ID=100)
  T2: balance=1000 → 2000 UPDATE + 커밋
  T1 SELECT: READ COMMITTED → 2000 읽음 (최신)
              REPEATABLE READ → 1000 읽음 (T1 시작 시점 스냅샷)
```

### Gap Lock (InnoDB, Phantom 방지)

```
REPEATABLE READ에서 Phantom 방지 메커니즘.

T1: SELECT * FROM devices WHERE site_id BETWEEN 10 AND 20 FOR UPDATE
→ site_id 10~20 범위에 Gap Lock 설정
→ T2: INSERT INTO devices (site_id=15) → 대기 (Gap Lock이 삽입 차단)
→ T1 커밋 후 T2 진행
```

---

## 예시 코드 (Python)

```python
import sqlite3
import threading
import time


# ── 격리 문제 시연 ────────────────────────────────────

def dirty_read_demo():
    """
    Dirty Read: 커밋 안 된 데이터를 읽는 문제
    SQLite는 기본 SERIALIZABLE이므로 시나리오 설명용
    """
    print("[Dirty Read 시나리오]")
    print("  T1: balance=1000 → 2000 UPDATE (커밋 전)")
    print("  T2: SELECT balance → 2000 읽음 (더티 읽기)")
    print("  T1: ROLLBACK")
    print("  T2: 2000이라 믿고 처리 → 실제는 1000 (오류!)")
    print("  방지: READ COMMITTED 이상 사용")


def non_repeatable_read_demo():
    """Non-Repeatable Read 시연"""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE accounts (id INT, balance INT)")
    conn.execute("INSERT INTO accounts VALUES (1, 1000)")
    conn.commit()

    results = []

    def t1_reader():
        """T1: 같은 SELECT를 두 번 실행"""
        cur = conn.cursor()
        # 1번 읽기
        val1 = cur.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        results.append(val1)
        time.sleep(0.05)   # T2에게 시간 허용
        # 2번 읽기 — T2가 수정했으면 다른 값!
        val2 = cur.execute("SELECT balance FROM accounts WHERE id=1").fetchone()[0]
        results.append(val2)

    def t2_writer():
        """T2: T1이 읽는 사이 데이터 변경"""
        time.sleep(0.01)
        conn.execute("UPDATE accounts SET balance=2000 WHERE id=1")
        conn.commit()

    t1 = threading.Thread(target=t1_reader)
    t2 = threading.Thread(target=t2_writer)
    t1.start(); t2.start()
    t1.join();  t2.join()

    print(f"\n[Non-Repeatable Read]")
    print(f"  T1 1번 읽기: {results[0]}")
    print(f"  T1 2번 읽기: {results[1]}")
    if results[0] != results[1]:
        print(f"  → Non-Repeatable Read 발생! (T2가 중간에 수정)")
    else:
        print(f"  → 동일 (격리 성공)")

    conn.close()


# ── MVCC 스냅샷 시뮬레이션 ───────────────────────────

class MVCCSimulator:
    """
    MVCC(Multi-Version Concurrency Control) 동작 시뮬레이션
    실제 InnoDB는 Undo Log 기반이지만 원리 이해용
    """

    def __init__(self):
        # { row_id: [(txn_id, value), ...] }  — 버전 히스토리
        self._versions: dict[int, list] = {}
        self._txn_counter = 0
        self._active_txns: dict[int, int] = {}   # txn_id → snapshot_time

    def begin(self) -> int:
        """트랜잭션 시작 — 스냅샷 시점 기록"""
        self._txn_counter += 1
        txn_id = self._txn_counter
        self._active_txns[txn_id] = txn_id   # snapshot = 시작 시 txn_id
        return txn_id

    def write(self, txn_id: int, row_id: int, value):
        """데이터 변경 — 새 버전 추가"""
        if row_id not in self._versions:
            self._versions[row_id] = []
        self._versions[row_id].append((txn_id, value))

    def read_committed(self, row_id: int) -> any:
        """READ COMMITTED: 최신 커밋된 버전"""
        versions = self._versions.get(row_id, [])
        if not versions:
            return None
        # 아직 활성 트랜잭션(커밋 전)은 제외
        committed = [(t, v) for t, v in versions if t not in self._active_txns]
        return committed[-1][1] if committed else None

    def repeatable_read(self, txn_id: int, row_id: int) -> any:
        """REPEATABLE READ: 트랜잭션 시작 시점 스냅샷"""
        snapshot = self._active_txns[txn_id]
        versions = self._versions.get(row_id, [])
        # 내 스냅샷 시점 이전에 커밋된 버전만
        visible = [(t, v) for t, v in versions
                   if t < snapshot or t == txn_id]  # 자신이 쓴 것은 보임
        return visible[-1][1] if visible else None

    def commit(self, txn_id: int):
        """커밋: 활성 트랜잭션에서 제거"""
        self._active_txns.pop(txn_id, None)


def mvcc_demo():
    mvcc = MVCCSimulator()

    # 초기 데이터 (txn 0이 커밋)
    mvcc._versions[1] = [(0, 1000)]   # account id=1, balance=1000

    t1 = mvcc.begin()   # T1 시작 (snapshot=t1)
    t2 = mvcc.begin()   # T2 시작

    # T2: balance 수정
    mvcc.write(t2, 1, 2000)
    mvcc.commit(t2)   # T2 커밋

    print("\n[MVCC 시뮬레이션]")
    rc  = mvcc.read_committed(1)
    rr  = mvcc.repeatable_read(t1, 1)
    print(f"  READ COMMITTED (최신):       {rc}")   # 2000 (T2 커밋됨)
    print(f"  REPEATABLE READ (T1 스냅샷): {rr}")   # 1000 (T1 시작 전 값)
    print(f"  → T1의 2번째 SELECT도 동일: {rr}")


# ── SELECT FOR UPDATE (비관적 락) ────────────────────

def select_for_update_demo():
    """
    SELECT FOR UPDATE: 읽으면서 락 획득
    Lost Update 방지에 사용
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE counters (name TEXT PRIMARY KEY, value INTEGER)")
    conn.execute("INSERT INTO counters VALUES ('poll_count', 0)")
    conn.commit()

    lock = threading.Lock()

    def safe_increment(n: int):
        for _ in range(n):
            with lock:
                conn.execute("BEGIN IMMEDIATE")   # 쓰기 락 획득
                val = conn.execute(
                    "SELECT value FROM counters WHERE name='poll_count'"
                ).fetchone()[0]
                conn.execute(
                    "UPDATE counters SET value=? WHERE name='poll_count'",
                    (val + 1,)
                )
                conn.execute("COMMIT")

    threads = [threading.Thread(target=safe_increment, args=(100,)) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    final = conn.execute(
        "SELECT value FROM counters WHERE name='poll_count'"
    ).fetchone()[0]
    print(f"\n[SELECT FOR UPDATE] 기대=300, 실제={final}")
    conn.close()


# ── 실행 ─────────────────────────────────────────────

print("=== 격리 수준 시연 ===")
dirty_read_demo()
non_repeatable_read_demo()
mvcc_demo()
select_for_update_demo()
```

---

## 면접 예상 질문

- Q: 격리 수준 4가지를 설명하라.
  A: READ UNCOMMITTED — 커밋 안 된 데이터 읽기 가능, 더티 리드 발생. READ COMMITTED — 커밋된 데이터만 읽음, Non-Repeatable Read 가능. REPEATABLE READ — 트랜잭션 내 같은 쿼리 항상 같은 결과 (InnoDB 기본값). SERIALIZABLE — 완전 직렬화, 가장 안전하지만 동시성 최저.

- Q: MVCC란? 왜 락 없이 읽기가 가능한가?
  A: Multi-Version Concurrency Control. 데이터 변경 시 기존 버전을 Undo Log에 유지. 읽기 트랜잭션은 자신의 시작 시점 스냅샷을 읽으므로 쓰기 락과 충돌 없음. 읽기-쓰기 동시성 향상. InnoDB에서 READ COMMITTED/REPEATABLE READ 구현 방식.

- Q: REPEATABLE READ에서 Phantom Read가 발생하는 이유는?
  A: Non-Repeatable Read는 기존 행의 수정이지만, Phantom Read는 새 행의 삽입. MVCC 스냅샷은 기존 행 버전을 관리하지만, 새로 삽입된 행은 스냅샷에 없음. InnoDB는 Gap Lock으로 범위에 삽입을 차단해 REPEATABLE READ에서도 Phantom Read 방지.

---

## 관련 개념

- [04-07 락](./04-07-lock.md) — 격리 수준 구현 메커니즘
- [04-02 트랜잭션/ACID](./04-02-transaction-acid.md) — Isolation 기초
- [04-08 쿼리 최적화](./04-08-query-optimization.md) — 락 대기 분석
