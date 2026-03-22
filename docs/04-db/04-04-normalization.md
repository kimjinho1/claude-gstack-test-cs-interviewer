# 04-04 정규화 / 역정규화

## 개념

**정규화(Normalization)**: 데이터 중복을 제거하고 이상(Anomaly)을 방지하기 위해 테이블을 분해하는 과정.
**역정규화(Denormalization)**: 조회 성능을 위해 의도적으로 중복을 허용하는 과정.

---

## 동작 원리

### 이상(Anomaly) — 정규화가 필요한 이유

```
비정규화 테이블 (employee_project):
emp_id | emp_name | dept    | project | proj_leader
100    | 김철수   | 네트워크 | SNMP개발 | 이영희
100    | 김철수   | 네트워크 | AP개발   | 박민준
101    | 이영희   | 네트워크 | SNMP개발 | 이영희

삽입 이상: 프로젝트 없는 신규 직원 추가 불가 (project 필수)
수정 이상: 김철수 부서 변경 시 2행 모두 수정해야 함 → 누락 시 불일치
삭제 이상: SNMP개발 프로젝트 삭제 시 이영희 정보도 사라짐
```

### 제1 정규형 (1NF)

원자값(Atomic): 각 컬럼은 단일 값만 가짐.

```
위반 예:
  emp_id | projects
  100    | "SNMP개발, AP개발"  ← 다중 값

1NF 준수:
  emp_id | project
  100    | SNMP개발
  100    | AP개발
```

### 제2 정규형 (2NF)

1NF + **부분 함수 종속** 제거. 복합 기본키의 일부에만 종속된 컬럼 분리.

```
(emp_id, project) → emp_name, dept, proj_leader

emp_name은 emp_id에만 종속 (project와 무관) → 부분 종속!

분해:
  employees(emp_id, emp_name, dept)
  projects(project, proj_leader)
  assignments(emp_id, project)    ← 교차 테이블
```

### 제3 정규형 (3NF)

2NF + **이행 함수 종속** 제거. 기본키가 아닌 컬럼이 다른 비기본키 컬럼에 종속.

```
employees(emp_id, emp_name, dept_id, dept_name)

dept_name은 dept_id에 종속 → emp_id → dept_id → dept_name (이행 종속)

분해:
  employees(emp_id, emp_name, dept_id)
  departments(dept_id, dept_name)
```

### BCNF (Boyce-Codd NF)

3NF보다 엄격. 모든 결정자가 후보키여야 함.

```
실무에서 3NF까지가 일반적 목표
BCNF는 너무 엄격해 JOIN 증가 → 성능 저하 우려
```

### 역정규화 — 언제 필요한가

```
정규화의 단점:
  - JOIN 많아짐 → 쿼리 복잡, 성능 저하
  - 집계 쿼리마다 JOIN 필요

역정규화 전략:
  1. 컬럼 중복 (Column Redundancy):
     interfaces에 device_hostname을 직접 저장
     → 장비 조회 없이 인터페이스 테이블만으로 리포트 가능

  2. 파생 컬럼 (Derived Column):
     devices에 interface_count 컬럼 추가
     → 매번 COUNT JOIN 없이 바로 조회

  3. 집계 테이블 (Summary Table):
     hourly_traffic_summary 별도 테이블 유지
     → 실시간 집계 없이 빠른 조회

주의: 역정규화 시 수정 이상 다시 발생 → 트리거/앱 레벨에서 동기화 필요
```

---

## 예시 코드 (Python)

```python
import sqlite3


# ── 정규화 단계 시연 ─────────────────────────────────

def normalization_demo():
    conn = sqlite3.connect(":memory:")
    cur  = conn.cursor()

    # 비정규화 테이블 (1NF 위반: vlans 컬럼에 다중 값)
    cur.execute("""
        CREATE TABLE interfaces_unnormalized (
            id       INTEGER PRIMARY KEY,
            hostname TEXT,
            site     TEXT,          -- 이행 종속: hostname → site
            name     TEXT,
            vlans    TEXT           -- 1NF 위반: "10,20,30"
        )
    """)
    cur.executemany("INSERT INTO interfaces_unnormalized VALUES (?,?,?,?,?)", [
        (1, "sw-core-01", "HQ", "Gi0/0", "10,20"),
        (2, "sw-core-01", "HQ", "Gi0/1", "30"),
        (3, "sw-dist-01", "Branch1", "Gi0/0", "10"),
    ])
    conn.commit()

    print("[비정규화] interfaces_unnormalized:")
    for r in cur.execute("SELECT * FROM interfaces_unnormalized"):
        print(f"  {r}")

    # 3NF 정규화 결과
    cur.executescript("""
        -- 1NF + 2NF + 3NF 적용 결과
        CREATE TABLE devices (
            id       INTEGER PRIMARY KEY,
            hostname TEXT UNIQUE NOT NULL,
            site_id  INTEGER,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        );
        CREATE TABLE sites (
            id   INTEGER PRIMARY KEY,
            name TEXT UNIQUE
        );
        CREATE TABLE interfaces (
            id        INTEGER PRIMARY KEY,
            device_id INTEGER,
            name      TEXT,
            FOREIGN KEY (device_id) REFERENCES devices(id)
        );
        CREATE TABLE interface_vlans (      -- 1NF: 다중 VLAN → 별도 행
            iface_id INTEGER,
            vlan_id  INTEGER,
            PRIMARY KEY (iface_id, vlan_id)
        );

        INSERT INTO sites VALUES (1,'HQ'), (2,'Branch1');
        INSERT INTO devices VALUES (1,'sw-core-01',1), (2,'sw-dist-01',2);
        INSERT INTO interfaces VALUES (1,1,'Gi0/0'), (2,1,'Gi0/1'), (3,2,'Gi0/0');
        INSERT INTO interface_vlans VALUES (1,10),(1,20),(2,30),(3,10);
    """)

    print("\n[3NF 정규화 후] 인터페이스 + VLAN + 장비 + 사이트 JOIN:")
    rows = cur.execute("""
        SELECT s.name AS site, d.hostname, i.name AS iface, iv.vlan_id
        FROM sites s
        JOIN devices d ON s.id = d.site_id
        JOIN interfaces i ON d.id = i.device_id
        JOIN interface_vlans iv ON i.id = iv.iface_id
        ORDER BY s.name, d.hostname, i.name, iv.vlan_id
    """).fetchall()
    for r in rows:
        print(f"  {r[0]:10s} {r[1]:15s} {r[2]:8s} VLAN={r[3]}")

    # 역정규화: 인터페이스 테이블에 hostname 추가 (JOIN 최소화)
    cur.execute("ALTER TABLE interfaces ADD COLUMN hostname_cache TEXT")
    cur.execute("""
        UPDATE interfaces SET hostname_cache = (
            SELECT hostname FROM devices WHERE id = interfaces.device_id
        )
    """)
    conn.commit()

    print("\n[역정규화] hostname_cache 추가 후 JOIN 없이 조회:")
    rows = cur.execute(
        "SELECT hostname_cache, name FROM interfaces ORDER BY hostname_cache, name"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:15s} {r[1]}")

    conn.close()


# ── 파생 컬럼으로 집계 성능 개선 ─────────────────────

def derived_column_demo():
    """
    역정규화: 집계 결과를 별도 컬럼에 미리 계산
    실시간 COUNT JOIN → 캐시된 컬럼 조회로 대체
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE devices (
            id          INTEGER PRIMARY KEY,
            hostname    TEXT,
            iface_count INTEGER DEFAULT 0,    -- 파생 컬럼 (역정규화)
            up_count    INTEGER DEFAULT 0
        );
        CREATE TABLE interfaces (
            id        INTEGER PRIMARY KEY,
            device_id INTEGER,
            name      TEXT,
            status    TEXT DEFAULT 'up'
        );
        INSERT INTO devices (id, hostname) VALUES (1,'sw-core-01'),(2,'sw-dist-01');
        INSERT INTO interfaces VALUES (1,1,'Gi0/0','up'),(2,1,'Gi0/1','down'),
                                       (3,2,'Gi0/0','up'),(4,2,'Gi0/1','up');
    """)

    # 파생 컬럼 업데이트 (트리거로 자동화하는 게 실무)
    conn.execute("""
        UPDATE devices SET
            iface_count = (SELECT COUNT(*) FROM interfaces WHERE device_id = devices.id),
            up_count    = (SELECT COUNT(*) FROM interfaces WHERE device_id = devices.id AND status='up')
    """)
    conn.commit()

    print("\n[파생 컬럼] 집계 정보 바로 조회 (JOIN 없음):")
    for r in conn.execute("SELECT hostname, iface_count, up_count FROM devices"):
        print(f"  {r[0]:15s} 전체={r[1]} UP={r[2]}")

    conn.close()


# ── 실행 ─────────────────────────────────────────────

print("=== 정규화 시연 ===")
normalization_demo()

print("\n=== 역정규화 (파생 컬럼) ===")
derived_column_demo()
```

---

## 면접 예상 질문

- Q: 1NF~3NF를 설명하라.
  A: 1NF — 각 컬럼이 원자값만 가짐 (다중 값 불가). 2NF — 1NF + 부분 함수 종속 제거 (복합키의 일부에만 종속된 컬럼 분리). 3NF — 2NF + 이행 함수 종속 제거 (비기본키 → 비기본키 종속 제거). 실무에서 3NF까지가 목표.

- Q: 정규화와 역정규화를 언제 선택하나?
  A: 정규화 우선 — 데이터 무결성, OLTP (insert/update 빈번). 역정규화 — 읽기 성능 중요, OLAP/리포팅, JOIN 비용이 너무 클 때. 역정규화 시 수정 이상 재발 → 트리거나 앱 레벨에서 동기화 코드 관리 필요. 먼저 정규화하고 성능 문제 발생 시 역정규화 고려.

- Q: 이행 함수 종속이란?
  A: A → B → C 관계. 즉 기본키(A)가 비기본키(B)를 결정하고, B가 또 다른 비기본키(C)를 결정. 예: emp_id → dept_id → dept_name. 3NF 위반. 분해: departments(dept_id, dept_name) 별도 테이블.

---

## 관련 개념

- [04-03 조인](./04-03-join.md) — 정규화로 생기는 JOIN
- [04-05 인덱스](./04-05-index.md) — 역정규화 후 인덱스로 성능 확보
- [04-08 쿼리 최적화](./04-08-query-optimization.md)
