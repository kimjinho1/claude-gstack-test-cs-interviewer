# 02-06 교착상태 (Deadlock)

## 개념

두 개 이상의 프로세스/스레드가 서로 상대방이 보유한 자원을 기다리며 **영원히 대기**하는 상태.

```
Thread A: lock1 보유, lock2 기다림
Thread B: lock2 보유, lock1 기다림
→ 서로 영원히 대기 → 교착상태
```

---

## 교착상태 4가지 조건 (모두 만족해야 발생)

| 조건 | 설명 |
|------|------|
| **상호 배제** (Mutual Exclusion) | 자원은 한 번에 하나만 사용 |
| **점유 대기** (Hold & Wait) | 자원 보유하면서 다른 자원 대기 |
| **비선점** (No Preemption) | 자원을 강제로 빼앗을 수 없음 |
| **순환 대기** (Circular Wait) | A→B→C→A 형태로 대기 사이클 |

**4가지 중 하나라도 깨면 교착상태 방지 가능.**

---

## 동작 원리

### 교착상태 발생 예시

```
자원: lock1, lock2

Thread A:
  lock1.acquire()
  time.sleep(0.1)   ← 이 사이에 B가 lock2 획득
  lock2.acquire()   ← 대기
  ...

Thread B:
  lock2.acquire()
  time.sleep(0.1)
  lock1.acquire()   ← 대기
  ...

A: lock1 보유, lock2 기다림
B: lock2 보유, lock1 기다림
→ 교착상태
```

### 교착상태 처리 방법

**1. 예방 (Prevention)** — 4가지 조건 중 하나를 원천 차단

```
순환 대기 제거: 모든 스레드가 자원을 같은 순서로 획득
  나쁜 예: A는 lock1→lock2, B는 lock2→lock1
  좋은 예: A, B 모두 lock1→lock2 순서로 획득

점유 대기 제거: 필요한 자원을 한 번에 모두 획득
  단점: 자원 낭비, 기아 가능
```

**2. 회피 (Avoidance)** — 실행 전 안전 상태 여부 확인

```
Banker's Algorithm:
  자원 할당 전 "이 상태에서 모든 프로세스가 완료될 수 있나?" 검사
  가능하면 할당, 불가능하면 대기
  단점: 최대 자원 요구량 미리 알아야 함, 오버헤드 큼
```

**3. 탐지 및 복구 (Detection & Recovery)**

```
탐지: 주기적으로 자원 할당 그래프에서 사이클 검사
복구:
  - 교착상태 프로세스 중 하나 강제 종료
  - 자원 강제 선점 후 롤백
  단점: 작업 손실 가능
```

**4. 무시 (Ostrich Algorithm)**

```
교착상태 발생 확률이 낮고, 처리 비용이 크면 그냥 무시.
사람이 직접 프로세스 kill.
Linux, Windows 일반적으로 이 방식.
```

### 실무에서 교착상태 방지 패턴

```python
# 락 획득 순서 통일 (순환 대기 제거)
locks = [lock1, lock2, lock3]
for lock in sorted(locks, key=id):  # 항상 메모리 주소 순서로
    lock.acquire()

# 타임아웃으로 교착 탐지
acquired = lock.acquire(timeout=5)
if not acquired:
    # 교착상태 의심 → 로그, 경보, 재시도
    logger.error("Lock 획득 타임아웃 → 교착상태 의심")
```

---

## 예시 코드 (Python)

```python
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(threadName)s: %(message)s")


# ── 교착상태 재현 ─────────────────────────────────────

def deadlock_demo():
    lock1 = threading.Lock()
    lock2 = threading.Lock()

    def thread_a():
        lock1.acquire()
        logging.info("lock1 획득, lock2 기다리는 중...")
        time.sleep(0.1)
        # lock2.acquire()  # 이걸 실행하면 교착상태!
        logging.info("(교착상태 시연은 타임아웃으로 대체)")
        lock1.release()

    def thread_b():
        lock2.acquire()
        logging.info("lock2 획득, lock1 기다리는 중...")
        time.sleep(0.1)
        lock2.release()

    ta = threading.Thread(target=thread_a, name="Thread-A")
    tb = threading.Thread(target=thread_b, name="Thread-B")
    ta.start(); tb.start()
    ta.join(); tb.join()


# ── 교착상태 방지: 순서 통일 ──────────────────────────

def ordered_lock_demo():
    lock1 = threading.Lock()
    lock2 = threading.Lock()

    def safe_thread(name: str, first, second):
        # 두 스레드 모두 id 순서로 획득
        locks_ordered = sorted([first, second], key=id)
        with locks_ordered[0]:
            logging.info(f"첫 번째 락 획득")
            time.sleep(0.05)
            with locks_ordered[1]:
                logging.info(f"두 번째 락 획득 → 작업 수행")

    ta = threading.Thread(target=safe_thread, args=("A", lock1, lock2), name="Thread-A")
    tb = threading.Thread(target=safe_thread, args=("B", lock2, lock1), name="Thread-B")
    ta.start(); tb.start()
    ta.join(); tb.join()
    print("교착상태 없이 완료!")


# ── 타임아웃으로 교착 탐지 ────────────────────────────

class SafeLock:
    """타임아웃 있는 락 래퍼"""
    def __init__(self, name: str, timeout: float = 3.0):
        self.name = name
        self.timeout = timeout
        self._lock = threading.Lock()

    def __enter__(self):
        acquired = self._lock.acquire(timeout=self.timeout)
        if not acquired:
            raise TimeoutError(f"락 '{self.name}' 획득 타임아웃 → 교착상태 의심")
        return self

    def __exit__(self, *args):
        self._lock.release()


def timeout_demo():
    lock_a = SafeLock("switch_config", timeout=1.0)
    lock_b = SafeLock("vlan_table", timeout=1.0)

    def update_switch():
        try:
            with lock_a:
                time.sleep(0.5)
                with lock_b:
                    print("스위치 설정 업데이트 완료")
        except TimeoutError as e:
            print(f"[경보] {e}")

    t = threading.Thread(target=update_switch)
    t.start()
    t.join()


print("=== 교착상태 방지: 순서 통일 ===")
ordered_lock_demo()

print("\n=== 타임아웃 탐지 ===")
timeout_demo()
```

---

## 면접 예상 질문

- Q: 교착상태의 4가지 조건은?
  A: 상호 배제(자원은 하나의 프로세스만 사용), 점유 대기(자원 보유 중 다른 자원 대기), 비선점(자원 강제 회수 불가), 순환 대기(A→B→C→A 형태의 대기 사이클). 4가지 모두 성립할 때 교착상태 발생.

- Q: 교착상태 방지와 회피의 차이는?
  A: 방지(Prevention)는 4가지 조건 중 하나를 원천 차단. 예: 자원 획득 순서 통일로 순환 대기 제거. 회피(Avoidance)는 자원 할당 전 안전 상태를 확인해 교착상태로 이어질 수 있는 할당 거부(Banker's Algorithm). 방지는 단순하지만 비효율적, 회피는 유연하지만 오버헤드 있음.

- Q: 실무에서 교착상태를 어떻게 처리하나?
  A: 대부분의 OS(Linux, Windows)는 무시(Ostrich Algorithm) 채택. 발생 확률이 낮고 처리 비용이 크기 때문. 개발자는 락 획득 순서 통일, 타임아웃 설정, 락 보유 시간 최소화로 예방. 탐지 시 로그/경보 후 프로세스 재시작.

---

## 관련 개념

- [02-05 동기화](./02-05-synchronization.md) — 뮤텍스/세마포어 사용 시 주의
- [02-04 CPU 스케줄링](./02-04-cpu-scheduling.md) — Priority Inversion (우선순위 역전)
