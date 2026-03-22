# 02-02 멀티프로세스 vs 멀티스레드

## 개념

**멀티프로세스**: 여러 프로세스를 동시에 실행. 독립 메모리.
**멀티스레드**: 하나의 프로세스 안에 여러 스레드. 메모리 공유.

둘 다 "동시에 여러 작업"이 목적이지만 접근 방식과 트레이드오프가 다름.

---

## 동작 원리

### 멀티프로세스

```
OS
├── Process A (snmpd)   → 독립 메모리
├── Process B (sshd)    → 독립 메모리
├── Process C (syslogd) → 독립 메모리
└── Process D (web UI)  → 독립 메모리

장점: A가 crash해도 B, C, D 영향 없음
단점: 프로세스 생성 비용 높음, IPC 복잡
```

**fork()**: 부모 프로세스를 복사해 자식 프로세스 생성.
```
parent = fork()
if parent == 0:  # 자식 프로세스
    exec("snmpd")
else:            # 부모 프로세스
    wait(parent)
```

**Copy-on-Write (CoW)**: fork() 시 메모리를 즉시 복사하지 않고, 수정이 발생할 때만 복사. 효율적.

### 멀티스레드

```
Process: snmpd
├── Thread-1: SNMP 요청 처리
├── Thread-2: Trap 이벤트 발송
├── Thread-3: MIB 테이블 갱신
└── Thread-4: 헬스 체크

장점: 메모리 공유로 통신 빠름, 스레드 생성 저렴
단점: 하나가 Segfault → 프로세스 전체 종료
```

### 동시성 vs 병렬성

```
동시성(Concurrency): CPU 1개가 빠르게 번갈아 실행 → 동시처럼 보임
병렬성(Parallelism): CPU 여러 개가 진짜로 동시 실행

싱글 코어:  동시성 O, 병렬성 X (시분할)
멀티 코어:  동시성 O, 병렬성 O
```

### Python GIL 문제

Python은 **GIL(Global Interpreter Lock)** 때문에 멀티스레드로 CPU 연산을 병렬화할 수 없음.

```
GIL: 한 번에 하나의 스레드만 Python 코드 실행 가능
→ CPU-bound 작업: 멀티스레드 소용없음 → 멀티프로세스 사용
→ I/O-bound 작업: I/O 대기 중엔 GIL 해제 → 멀티스레드 효과 있음
```

| 작업 유형 | 예시 | 권장 |
|---------|------|------|
| CPU-bound | 이미지 처리, 암호화, 계산 | 멀티프로세스 |
| I/O-bound | HTTP 요청, DB 쿼리, 파일 읽기 | 멀티스레드 or 비동기 |

---

## 비교 정리

| 구분 | 멀티프로세스 | 멀티스레드 |
|------|------------|---------|
| 메모리 | 독립 | 공유 |
| 통신 | IPC (느림, 복잡) | 공유 메모리 (빠름) |
| 생성 비용 | 높음 | 낮음 |
| 장애 격리 | 강함 | 약함 |
| 동기화 | 불필요 | 필요 (뮤텍스 등) |
| 사용 예 | Chrome 탭, 스위치 데몬 | 웹서버 요청 처리, snmpd 내부 |

---

## 예시 코드 (Python)

```python
import time
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


# ── CPU-bound: 멀티프로세스가 유리 ──────────────────────

def cpu_heavy(n: int) -> int:
    """CPU 집중 작업 (소수 판별)"""
    count = 0
    for i in range(2, n):
        if all(i % j != 0 for j in range(2, int(i**0.5) + 1)):
            count += 1
    return count


def benchmark_cpu(n: int = 50000):
    # 순차
    start = time.time()
    cpu_heavy(n)
    print(f"순차:         {time.time() - start:.2f}s")

    # 멀티스레드 (GIL 때문에 느릴 수 있음)
    start = time.time()
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(cpu_heavy, [n//4]*4))
    print(f"멀티스레드:   {time.time() - start:.2f}s  (GIL 영향)")

    # 멀티프로세스 (진짜 병렬)
    start = time.time()
    with ProcessPoolExecutor(max_workers=4) as ex:
        list(ex.map(cpu_heavy, [n//4]*4))
    print(f"멀티프로세스: {time.time() - start:.2f}s  (병렬 실행)")


# ── I/O-bound: 멀티스레드가 유리 ────────────────────────

def io_task(device_ip: str) -> dict:
    """네트워크 장비 상태 조회 시뮬레이션"""
    time.sleep(0.5)  # 네트워크 I/O 대기 시뮬레이션
    return {"ip": device_ip, "status": "up"}


def benchmark_io():
    devices = [f"192.168.99.{i}" for i in range(1, 21)]  # 20개 장비

    # 순차
    start = time.time()
    [io_task(d) for d in devices]
    print(f"순차 조회:        {time.time() - start:.2f}s")

    # 멀티스레드 (I/O 대기 중 GIL 해제 → 병렬 효과)
    start = time.time()
    with ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(io_task, devices))
    print(f"멀티스레드 조회:  {time.time() - start:.2f}s")


# ── 스위치 데몬 멀티프로세스 구조 ────────────────────────

class SwitchDaemon:
    """스위치 관리 데몬 (독립 프로세스)"""
    def __init__(self, name: str):
        self.name = name

    def run(self, event_queue: multiprocessing.Queue):
        print(f"[{self.name}] PID={multiprocessing.current_process().pid} 시작")
        while True:
            try:
                event = event_queue.get(timeout=1)
                if event == "STOP":
                    break
                print(f"[{self.name}] 이벤트 처리: {event}")
            except:
                pass


if __name__ == "__main__":
    print("=== CPU-bound 벤치마크 ===")
    benchmark_cpu()

    print("\n=== I/O-bound 벤치마크 (20개 장비 동시 조회) ===")
    benchmark_io()

    # 멀티프로세스 데몬
    print("\n=== 스위치 데몬 멀티프로세스 ===")
    queues = {}
    processes = {}

    daemons = ["snmpd", "sshd", "syslogd"]
    for name in daemons:
        q = multiprocessing.Queue()
        daemon = SwitchDaemon(name)
        p = multiprocessing.Process(target=daemon.run, args=(q,))
        p.start()
        queues[name] = q
        processes[name] = p

    # 이벤트 전송
    queues["snmpd"].put("GET ifTable")
    queues["sshd"].put("new connection from 192.168.99.10")

    time.sleep(0.5)
    for q in queues.values():
        q.put("STOP")
    for p in processes.values():
        p.join()
```

---

## 면접 예상 질문

- Q: 멀티프로세스와 멀티스레드의 선택 기준은?
  A: 장애 격리와 안전성이 중요하면 멀티프로세스(스위치 데몬, Chrome 탭). CPU 집중 작업 병렬화도 멀티프로세스. I/O 대기가 많고 데이터 공유가 빈번하면 멀티스레드(웹서버 요청 처리). Python은 GIL 때문에 CPU-bound는 멀티프로세스 필수.

- Q: Python의 GIL이란?
  A: Global Interpreter Lock. CPython에서 한 번에 하나의 스레드만 Python 코드를 실행하도록 제한. CPU-bound 멀티스레드는 병렬 실행이 안 됨. I/O-bound는 I/O 대기 중 GIL을 해제하므로 멀티스레드 효과 있음. CPU-bound 병렬화는 multiprocessing 모듈 사용.

- Q: 동시성과 병렬성의 차이는?
  A: 동시성(Concurrency)은 여러 작업이 번갈아가며 실행되어 동시처럼 보이는 것 (싱글 코어도 가능). 병렬성(Parallelism)은 여러 작업이 물리적으로 동시에 실행되는 것 (멀티 코어 필요). 멀티스레드는 동시성, 멀티프로세스는 병렬성을 제공.

- Q: Copy-on-Write란?
  A: fork() 시 부모 프로세스 메모리를 즉시 복사하지 않고, 자식이 해당 메모리를 수정할 때만 복사하는 최적화 기법. 자식 프로세스가 exec()로 바로 다른 프로그램을 실행하면 복사 비용 없음.

---

## 관련 개념

- [02-01 프로세스 vs 스레드](./02-01-process-thread.md)
- [02-04 CPU 스케줄링](./02-04-cpu-scheduling.md) — 멀티프로세스/스레드 스케줄링
- [02-05 동기화](./02-05-synchronization.md) — 멀티스레드 공유 자원 문제
