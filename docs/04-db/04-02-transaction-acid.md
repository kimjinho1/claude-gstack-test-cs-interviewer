# 04-02 트랜잭션 / ACID

## 개념

**트랜잭션(Transaction)**: 하나의 논리적 작업 단위. 모두 성공하거나 모두 실패해야 함.

**ACID**: 트랜잭션의 신뢰성을 보장하는 4가지 속성.

```
A — Atomicity    (원자성): 전부 성공 or 전부 롤백
C — Consistency  (일관성): 트랜잭션 전후 DB 무결성 유지
I — Isolation    (격리성): 동시 트랜잭션이 서로 간섭 안 함
D — Durability   (지속성): 커밋된 데이터는 장애 후에도 보존
```

---

## 동작 원리

### Atomicity — 원자성

```
계좌 이체 예시:
  BEGIN TRANSACTION
    UPDATE accounts SET balance = balance - 1000 WHERE id = 'A'  ← 성공
    UPDATE accounts SET balance = balance + 1000 WHERE id = 'B'  ← 실패!
  ROLLBACK  ← A에서 차감된 것도 원상복구

구현: Undo Log
  변경 전 데이터를 Undo Log에 기록
  실패 시 Undo Log로 되돌림
```

### Consistency — 일관성

```
무결성 제약 조건 (DB 레벨):
  - NOT NULL: 필수 컬럼
  - UNIQUE: 중복 금지
  - FOREIGN KEY: 참조 무결성
  - CHECK: 값 범위 제약

트랜잭션이 이 제약을 위반하면 자동 롤백
예: 잔액이 음수가 되면 CHECK 제약으로 실패 → 롤백
```

### Isolation — 격리성

동시 실행 트랜잭션 간의 간섭 수준. → 04-06 격리 수준에서 상세.

```
격리 문제:
  Dirty Read:      커밋되지 않은 변경 읽기
  Non-Repeatable: 같은 쿼리 두 번 실행 시 다른 결과
  Phantom Read:    조건에 맞는 행 수가 달라짐

격리 수준 (높을수록 안전, 성능 낮음):
  READ UNCOMMITTED → READ COMMITTED → REPEATABLE READ → SERIALIZABLE
```

### Durability — 지속성

```
WAL (Write-Ahead Logging):
  1. 데이터 변경 전 Redo Log에 먼저 기록
  2. 커밋 = 로그 디스크 동기화 완료
  3. 실제 데이터 파일 변경 (비동기)
  4. 장애 → Redo Log로 복구

InnoDB 예:
  - ib_logfile0, ib_logfile1: Redo Log
  - 커밋 시 fsync() 호출 → 디스크 동기화
  - innodb_flush_log_at_trx_commit=1 (기본값): 매 커밋마다 fsync
```

### 트랜잭션 상태 전이

```
  Active ──실행 중──▶ Partially Committed ──성공──▶ Committed
    │                         │
    │                    무결성 위반/오류
    │                         ↓
    └────────────────────▶ Failed ──▶ Aborted (Rollback)
```

---

## 예시 코드 (Python)

```python
import sqlite3
import threading
import time
from contextlib import contextmanager


# ── 기본 트랜잭션 ACID 시연 ──────────────────────────

def setup_db(conn):
    conn.execute("""
        CREATE TABLE accounts (
            id      TEXT PRIMARY KEY,
            name    TEXT,
            balance INTEGER CHECK(balance >= 0)  -- Consistency 제약
        )
    """)
    conn.execute("INSERT INTO accounts VALUES ('A', '송신자', 5000)")
    conn.execute("INSERT INTO accounts VALUES ('B', '수신자', 1000)")
    conn.commit()


def transfer(conn, from_id: str, to_id: str, amount: int) -> bool:
    """
    계좌 이체 — Atomicity 시연
    둘 다 성공하거나 둘 다 실패
    """
    try:
        with conn:   # Python sqlite3: with 블록 = 자동 commit/rollback
            # 잔액 확인
            row = conn.execute(
                "SELECT balance FROM accounts WHERE id=?", (from_id,)
            ).fetchone()
            if not row or row[0] < amount:
                raise ValueError(f"잔액 부족: {row[0] if row else 0} < {amount}")

            conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id=?",
                (amount, from_id)
            )
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id=?",
                (amount, to_id)
            )
            return True
    except Exception as e:
        print(f"  이체 실패 → 롤백: {e}")
        return False


def show_balances(conn, label: str):
    rows = conn.execute(
        "SELECT id, name, balance FROM accounts ORDER BY id"
    ).fetchall()
    print(f"  [{label}] ", end="")
    for row in rows:
        print(f"{row[1]}={row[2]}원", end="  ")
    print()


# ── Isolation: Lost Update 시연 ──────────────────────

def lost_update_demo():
    """
    격리 없이 동시 업데이트 시 Lost Update 발생
    T1, T2가 동시에 balance 읽고 업데이트
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE counters (name TEXT, value INTEGER)")
    conn.execute("INSERT INTO counters VALUES ('snmp_poll', 0)")
    conn.commit()

    errors = []

    def increment(conn, n: int, name: str):
        for _ in range(n):
            try:
                # 잘못된 방법: 읽기-수정-쓰기 간 경쟁
                val = conn.execute(
                    "SELECT value FROM counters WHERE name='snmp_poll'"
                ).fetchone()[0]
                time.sleep(0.0001)   # 의도적 지연으로 경쟁 유발
                conn.execute(
                    "UPDATE counters SET value=? WHERE name='snmp_poll'",
                    (val + 1,)
                )
                conn.commit()
            except Exception as e:
                errors.append(str(e))

    threads = [threading.Thread(target=increment, args=(conn, 100, f"T{i}"))
               for i in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    final = conn.execute(
        "SELECT value FROM counters WHERE name='snmp_poll'"
    ).fetchone()[0]
    print(f"  Lost Update: 기대값=300, 실제값={final} (차이={300-final})")

    # 올바른 방법: DB 레벨 원자적 업데이트
    conn.execute("UPDATE counters SET value=0 WHERE name='snmp_poll'")
    conn.commit()

    def atomic_increment(conn, n: int):
        for _ in range(n):
            try:
                conn.execute(
                    "UPDATE counters SET value=value+1 WHERE name='snmp_poll'"
                )
                conn.commit()
            except Exception:
                pass

    threads = [threading.Thread(target=atomic_increment, args=(conn, 100))
               for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    final = conn.execute(
        "SELECT value FROM counters WHERE name='snmp_poll'"
    ).fetchone()[0]
    print(f"  원자적 업데이트: 기대값=300, 실제값={final}")


# ── Savepoint (중간 롤백) ────────────────────────────

def savepoint_demo(conn):
    """
    Savepoint: 트랜잭션 내 부분 롤백
    배치 작업 중 일부 실패 시 전체 롤백 없이 처리
    """
    print("\n  Savepoint 시연:")
    cur = conn.cursor()
    cur.execute("BEGIN")
    try:
        cur.execute("UPDATE accounts SET balance=balance-100 WHERE id='A'")
        cur.execute("SAVEPOINT sp1")   # 중간 저장점

        cur.execute("UPDATE accounts SET balance=balance-200 WHERE id='A'")
        cur.execute("SAVEPOINT sp2")

        # 의도적 실패 시뮬레이션
        cur.execute("UPDATE accounts SET balance=balance-9999 WHERE id='A'")
        # CHECK 제약 위반 확인
        row = cur.execute("SELECT balance FROM accounts WHERE id='A'").fetchone()
        if row[0] < 0:
            cur.execute("ROLLBACK TO sp2")   # sp2 이후만 롤백
            print("    sp2 이후 롤백 (큰 인출 취소)")

        cur.execute("COMMIT")
    except Exception as e:
        cur.execute("ROLLBACK")
        print(f"    전체 롤백: {e}")


# ── 실행 ─────────────────────────────────────────────

conn = sqlite3.connect(":memory:")
setup_db(conn)

print("=== ACID 트랜잭션 시연 ===")
show_balances(conn, "초기")
transfer(conn, "A", "B", 2000)
show_balances(conn, "이체 후")

# Consistency 위반 시도
print("\n  잔액 초과 이체 시도:")
transfer(conn, "A", "B", 9999)    # CHECK(balance >= 0) 위반
show_balances(conn, "실패 후")     # 변화 없음

savepoint_demo(conn)
show_balances(conn, "Savepoint 후")

print("\n=== Lost Update 시연 ===")
lost_update_demo()
```

---

## 면접 예상 질문

- Q: ACID 각 속성을 설명하라.
  A: Atomicity(원자성) — 트랜잭션 내 모든 작업이 전부 성공하거나 전부 롤백. 계좌 이체에서 출금만 되고 입금 안 되는 상황 방지. Consistency(일관성) — 트랜잭션 전후 DB 무결성 제약 유지. Isolation(격리성) — 동시 실행 트랜잭션 간 간섭 없음. Durability(지속성) — 커밋된 데이터는 장애 후에도 유지 (WAL로 구현).

- Q: Atomicity는 어떻게 구현되나?
  A: Undo Log (롤백 세그먼트). 변경 전 데이터를 Undo Log에 기록 → 장애나 롤백 시 Undo Log로 원상복구. Durability는 Redo Log(WAL) — 변경 내용을 먼저 로그에 기록 → 커밋 시 로그 디스크 동기화 → 이후 실제 데이터 파일 반영.

- Q: 트랜잭션에서 Lost Update란?
  A: 두 트랜잭션이 같은 데이터를 읽어 수정할 때 하나의 변경이 덮어써지는 문제. 해결: ① DB 레벨 원자적 연산(UPDATE SET val=val+1), ② SELECT FOR UPDATE (비관적 락), ③ 낙관적 락 (버전 컬럼 이용).

---

## 관련 개념

- [04-06 격리 수준](./04-06-isolation-level.md) — Isolation 상세
- [04-07 락](./04-07-lock.md) — Isolation 구현 메커니즘
- [04-01 RDBMS vs NoSQL](./04-01-rdbms-nosql.md) — ACID vs BASE
