# 02-05 동기화 (뮤텍스, 세마포어, 모니터)

## 개념

멀티스레드/멀티프로세스 환경에서 **공유 자원에 대한 동시 접근을 제어**해 데이터 일관성 보장.

**Race Condition**: 실행 순서에 따라 결과가 달라지는 상황.
**Critical Section**: 공유 자원을 접근하는 코드 영역.

---

## 동작 원리

### Race Condition 예시

```python
# counter++ 는 사실 3단계 연산
# LOAD counter → 레지스터
# ADD 1
# STORE 레지스터 → counter

Thread A: LOAD (counter=5)
Thread B: LOAD (counter=5)  ← A가 아직 STORE 안 함
Thread A: ADD → 6, STORE
Thread B: ADD → 6, STORE    ← B도 6으로 저장 (7이어야 함)

결과: counter=6 (예상: 7) → 1 손실
```

### 뮤텍스 (Mutex, Mutual Exclusion Lock)

한 번에 **하나의 스레드만** Critical Section 진입 허용.

```
뮤텍스 상태: LOCKED / UNLOCKED

Thread A: lock() → LOCKED → Critical Section 실행 → unlock()
Thread B: lock() → 이미 LOCKED → 대기
Thread A: unlock() → UNLOCKED
Thread B: lock() → LOCKED → Critical Section 실행 → unlock()
```

**특징**:
- 소유권: lock한 스레드만 unlock 가능
- 재귀적 획득 불가 (같은 스레드가 두 번 lock → 데드락)

### 세마포어 (Semaphore)

**카운터 기반**. 정수 값으로 허용 개수 제어.

```
Binary Semaphore (값: 0 또는 1) → 뮤텍스와 유사
Counting Semaphore (값: N)      → N개 동시 접근 허용

wait(P): 카운터 감소, 0이면 대기
signal(V): 카운터 증가, 대기 중인 스레드 깨움

예: DB 연결 풀 최대 10개
sem = Semaphore(10)
sem.wait()   # 연결 하나 사용 (카운터 9)
# DB 작업
sem.signal() # 연결 반납 (카운터 10)
```

**뮤텍스 vs 세마포어**

| 구분 | 뮤텍스 | 세마포어 |
|------|--------|---------|
| 소유권 | lock한 스레드만 unlock | 누구나 signal 가능 |
| 허용 수 | 1 | N |
| 용도 | 상호 배제 | 자원 개수 제한, 이벤트 동기화 |

### 모니터 (Monitor)

**언어 레벨 동기화**. 뮤텍스 + Condition Variable 조합. Java의 `synchronized`, Python의 `with Lock`.

```python
class BoundedBuffer:
    def __init__(self, size):
        self.buffer = []
        self.size = size
        self.lock = threading.Lock()
        self.not_full = threading.Condition(self.lock)
        self.not_empty = threading.Condition(self.lock)

    def put(self, item):
        with self.not_full:
            while len(self.buffer) >= self.size:
                self.not_full.wait()   # 버퍼 꽉 참 → 대기
            self.buffer.append(item)
            self.not_empty.notify()    # 소비자 깨움

    def get(self):
        with self.not_empty:
            while not self.buffer:
                self.not_empty.wait()  # 버퍼 비어있음 → 대기
            item = self.buffer.pop(0)
            self.not_full.notify()     # 생산자 깨움
            return item
```

### Spinlock

대기 중에 CPU를 놓지 않고 계속 확인(busy-waiting). 짧은 대기에서 효율적.

```
while lock.is_locked():
    pass  # CPU 계속 사용하며 대기 (spin)
lock.acquire()
```

- 커널 내부, 멀티코어 환경에서 사용
- 대기 시간이 길면 CPU 낭비

---

## 예시 코드 (Python)

```python
import threading
import time
from collections import deque


# ── Race Condition 재현 ──────────────────────────────

counter = 0

def bad_increment(n: int):
    global counter
    for _ in range(n):
        counter += 1  # race condition


def race_condition_demo():
    global counter
    counter = 0
    threads = [threading.Thread(target=bad_increment, args=(10000,)) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    print(f"Race Condition: expected=50000, got={counter}")


# ── 뮤텍스로 해결 ────────────────────────────────────

mutex = threading.Lock()
safe_counter = 0

def safe_increment(n: int):
    global safe_counter
    for _ in range(n):
        with mutex:  # lock → critical section → unlock
            safe_counter += 1


def mutex_demo():
    global safe_counter
    safe_counter = 0
    threads = [threading.Thread(target=safe_increment, args=(10000,)) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    print(f"Mutex 사용:    expected=50000, got={safe_counter}")


# ── 세마포어: 연결 풀 ────────────────────────────────

class ConnectionPool:
    """DB/장비 연결 풀 (최대 N개 동시 연결)"""
    def __init__(self, max_connections: int):
        self.semaphore = threading.Semaphore(max_connections)
        self.max = max_connections
        self._lock = threading.Lock()
        self._active = 0

    def connect(self, client_id: str) -> bool:
        acquired = self.semaphore.acquire(timeout=2)
        if not acquired:
            print(f"[{client_id}] 연결 거부: 풀 고갈")
            return False
        with self._lock:
            self._active += 1
        print(f"[{client_id}] 연결 획득 (활성: {self._active}/{self.max})")
        return True

    def disconnect(self, client_id: str):
        with self._lock:
            self._active -= 1
        self.semaphore.release()
        print(f"[{client_id}] 연결 반납 (활성: {self._active}/{self.max})")


def semaphore_demo():
    pool = ConnectionPool(max_connections=3)

    def client(cid: str):
        if pool.connect(cid):
            time.sleep(0.3)  # 작업 시뮬레이션
            pool.disconnect(cid)

    threads = [threading.Thread(target=client, args=(f"CLI-{i}",)) for i in range(6)]
    [t.start() for t in threads]
    [t.join() for t in threads]


# ── 스위치 이벤트 처리: 생산자-소비자 (모니터) ──────────

class SwitchEventQueue:
    """스위치 이벤트 큐 (포트 up/down, SNMP trap 등)"""
    def __init__(self, maxsize: int = 100):
        self._queue: deque = deque()
        self._maxsize = maxsize
        self._cond = threading.Condition()

    def publish(self, event: dict):
        with self._cond:
            while len(self._queue) >= self._maxsize:
                self._cond.wait()
            self._queue.append(event)
            self._cond.notify_all()

    def consume(self, timeout: float = 1.0) -> dict | None:
        with self._cond:
            deadline = time.time() + timeout
            while not self._queue:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                self._cond.wait(timeout=remaining)
            event = self._queue.popleft()
            self._cond.notify_all()
            return event


def monitor_demo():
    eq = SwitchEventQueue()

    def producer():
        events = [
            {"type": "port_down", "port": 3},
            {"type": "cpu_high", "value": 90},
            {"type": "ap_disconnect", "ap": "AP-01"},
        ]
        for e in events:
            time.sleep(0.1)
            eq.publish(e)
            print(f"[Producer] 발행: {e}")

    def consumer(cid: int):
        for _ in range(2):
            event = eq.consume(timeout=2)
            if event:
                print(f"[Consumer-{cid}] 처리: {event}")

    prod = threading.Thread(target=producer)
    cons = [threading.Thread(target=consumer, args=(i,)) for i in range(2)]
    prod.start()
    [c.start() for c in cons]
    prod.join()
    [c.join() for c in cons]


race_condition_demo()
mutex_demo()
print("\n=== 세마포어 (연결 풀) ===")
semaphore_demo()
print("\n=== 모니터 (이벤트 큐) ===")
monitor_demo()
```

---

## 면접 예상 질문

- Q: Race Condition이란? 어떻게 해결하나?
  A: 여러 스레드가 공유 자원에 동시 접근할 때 실행 순서에 따라 결과가 달라지는 문제. counter++ 같은 비원자적 연산에서 발생. 해결: 뮤텍스/세마포어/synchronized로 Critical Section 보호, 원자적 연산(Atomic) 사용.

- Q: 뮤텍스와 세마포어의 차이는?
  A: 뮤텍스는 하나의 스레드만 접근 허용, lock한 스레드만 unlock 가능 (소유권). 세마포어는 카운터 기반으로 N개 동시 접근 허용, 누구나 signal 가능. 뮤텍스는 상호 배제에, 세마포어는 자원 개수 제한이나 이벤트 동기화에 적합.

- Q: 데드락과 동기화 문제의 관계는?
  A: 동기화를 위해 락을 사용할 때 잘못된 순서로 여러 락을 획득하면 데드락 발생. 예: Thread A가 lock1 보유 중 lock2 기다리고, Thread B가 lock2 보유 중 lock1 기다리면 서로 영원히 대기.

- Q: Spinlock은 언제 유리한가?
  A: 대기 시간이 매우 짧을 때. 커널 내부나 멀티코어에서 락 경쟁이 드물고 짧은 구간에 사용. 대기 중 Context Switch가 없어 오버헤드 감소. 대기 시간이 길면 CPU를 낭비해 불리.

---

## 관련 개념

- [02-01 프로세스 vs 스레드](./02-01-process-thread.md) — 스레드 공유 메모리
- [02-06 교착상태 (Deadlock)](./02-06-deadlock.md) — 동기화의 부작용
