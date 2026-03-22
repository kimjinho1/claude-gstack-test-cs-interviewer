# 02-01 프로세스 vs 스레드

## 개념

**프로세스(Process)**: OS가 프로그램을 실행하는 독립적인 단위. 각자 독립된 메모리 공간을 가짐.
**스레드(Thread)**: 프로세스 안에서 실행되는 작업 단위. 같은 프로세스의 메모리를 공유.

---

## 동작 원리

### 프로세스 메모리 구조

```
프로세스 (예: 스위치 관리 데몬 snmpd)
┌─────────────────┐  높은 주소
│     Stack       │  ← 함수 호출, 지역 변수 (스레드마다 독립)
│        ↓        │
│                 │
│        ↑        │
│      Heap       │  ← 동적 할당 (malloc/new) → 스레드 공유
│─────────────────│
│  Data / BSS     │  ← 전역 변수, 정적 변수 → 스레드 공유
│─────────────────│
│      Code       │  ← 실행 코드 (읽기 전용) → 스레드 공유
└─────────────────┘  낮은 주소
```

스레드는 Stack만 독립, 나머지(Code, Data, Heap)는 프로세스 내 공유.

### PCB vs TCB

**PCB(Process Control Block)**: OS가 프로세스 관리에 사용하는 자료구조.
```
PCB:
  - PID (프로세스 ID)
  - 상태 (Running, Ready, Blocked, ...)
  - PC (Program Counter): 다음 실행할 명령어 주소
  - 레지스터 값
  - 메모리 정보 (페이지 테이블 포인터)
  - 열린 파일 목록
  - 우선순위
```

**TCB(Thread Control Block)**: 스레드별 상태 저장.
```
TCB:
  - TID (스레드 ID)
  - PC, 레지스터 값
  - 스택 포인터
  - 상태
  (메모리 정보는 PCB 공유)
```

### Context Switch (문맥 전환)

CPU가 현재 실행 중인 프로세스/스레드를 바꿀 때 발생. **순수 오버헤드**.

```
프로세스 A 실행 중
→ 타임슬라이스 만료 or 인터럽트 발생
→ A의 레지스터/PC → A의 PCB에 저장
→ B의 PCB에서 레지스터/PC 복원
→ 프로세스 B 실행

프로세스 간 전환: TLB 플러시 + 페이지 테이블 교체 → 비쌈
스레드 간 전환: 같은 메모리 공간 → TLB 플러시 없음 → 저렴
```

### 프로세스 상태

```
New ──fork()──▶ Ready ◀──────────── Running
                  │         스케줄러    │    │
                  │         선택 ──────▶│    │
                  │                       │    ↓
                  │              I/O 완료  │  Blocked (I/O 대기)
                  ◀──────────────────────      │
                                               ↓
                                            Terminated
```

### 프로세스 간 통신 (IPC)

프로세스는 메모리가 분리되어 있어 직접 데이터를 공유할 수 없음. IPC 필요.

| IPC 방식 | 특징 | 용도 |
|---------|------|------|
| 파이프 (Pipe) | 단방향, 부모-자식 간 | 쉘 명령어 파이프라인 |
| 소켓 (Socket) | 양방향, 네트워크 가능 | 프로세스 간 네트워크 통신 |
| 공유 메모리 | 가장 빠름, 동기화 필요 | 대용량 데이터 공유 |
| 메시지 큐 | 비동기, 버퍼링 | 이벤트 처리 |
| 세마포어 | 동기화 목적 | 공유 자원 접근 제어 |

### 스위치/AP 관점

```
스위치 OS 프로세스 구조 (예시):
  snmpd       ← SNMP 에이전트 프로세스
  sshd        ← SSH 데몬 프로세스
  syslogd     ← Syslog 프로세스
  spanning-tree-daemon
  ...

snmpd 내부 스레드:
  Thread-1: SNMP GET/SET 요청 처리
  Thread-2: Trap 전송
  Thread-3: MIB 테이블 업데이트
  Thread-4: 헬스 체크

→ 각 데몬은 독립 프로세스 → 하나 crash해도 다른 기능 살아있음
→ snmpd 내부는 스레드로 병렬 처리
```

---

## 비교 정리

| 구분 | 프로세스 | 스레드 |
|------|---------|-------|
| 메모리 | 독립 (Code/Data/Heap/Stack 모두) | Stack만 독립, 나머지 공유 |
| 생성 비용 | 높음 (메모리 복사, fork) | 낮음 (Stack만 생성) |
| 통신 | IPC 필요 (복잡, 느림) | 공유 메모리 (간단, 빠름, 위험) |
| 장애 격리 | 높음 (독립 메모리) | 낮음 (하나 crash → 전체 위험) |
| Context Switch | 비쌈 (TLB 플러시 등) | 저렴 |
| 적합한 경우 | 안전성 중요, 독립 실행 | 성능 중요, 데이터 공유 많을 때 |

---

## 예시 코드 (Python)

```python
import os
import threading
import multiprocessing
import time


# ── 스레드: 메모리 공유 ─────────────────────────────────

shared_counter = 0  # 전역 변수 (스레드 간 공유)


def thread_worker(name: str, count: int):
    global shared_counter
    for _ in range(count):
        shared_counter += 1  # 공유 메모리 접근 (race condition 위험!)
    print(f"[Thread-{name}] 완료, counter={shared_counter}")


# 스레드 생성 및 실행
threads = []
for i in range(3):
    t = threading.Thread(target=thread_worker, args=(i, 1000))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"최종 counter={shared_counter}")  # 3000이어야 하지만 race condition으로 다를 수 있음


# ── 프로세스: 독립 메모리 ───────────────────────────────

def process_worker(name: str, queue: multiprocessing.Queue):
    pid = os.getpid()
    result = sum(range(10000))
    queue.put({"name": name, "pid": pid, "result": result})
    print(f"[Process-{name}] PID={pid} 완료")


# 프로세스 간 통신: Queue (IPC)
result_queue = multiprocessing.Queue()
processes = []

for i in range(3):
    p = multiprocessing.Process(target=process_worker, args=(i, result_queue))
    processes.append(p)
    p.start()

for p in processes:
    p.join()

while not result_queue.empty():
    print(f"  결과: {result_queue.get()}")


# ── Context Switch 오버헤드 비교 ────────────────────────

def measure_thread_switch(n: int) -> float:
    """스레드 전환 시간 측정"""
    results = []
    barrier = threading.Barrier(2)

    def worker():
        barrier.wait()
        start = time.perf_counter()
        for _ in range(n):
            pass
        results.append(time.perf_counter() - start)

    ts = [threading.Thread(target=worker) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return sum(results) / len(results)


# PCB 정보 확인 (실제)
import psutil

proc = psutil.Process(os.getpid())
print(f"\n[현재 프로세스 PCB 정보]")
print(f"  PID:    {proc.pid}")
print(f"  상태:   {proc.status()}")
print(f"  스레드: {proc.num_threads()}개")
print(f"  메모리: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
print(f"  CPU:    {proc.cpu_percent()}%")
```

---

## 면접 예상 질문

- Q: 프로세스와 스레드의 차이는?
  A: 프로세스는 독립된 메모리 공간(Code/Data/Heap/Stack)을 가진 실행 단위. 스레드는 프로세스 내에서 Stack만 독립적으로 가지고 나머지 메모리를 공유하는 실행 단위. 스레드가 생성 비용이 낮고 통신이 빠르지만 하나의 스레드 오류가 프로세스 전체에 영향을 줄 수 있음.

- Q: Context Switch란? 비용이 왜 발생하나?
  A: CPU가 실행 중인 프로세스/스레드를 전환할 때 현재 상태(레지스터, PC 등)를 PCB에 저장하고 다음 것의 상태를 복원하는 과정. 프로세스 전환은 페이지 테이블 교체와 TLB 플러시가 필요해 비쌈. 스레드 전환은 같은 주소 공간이라 TLB 플러시 없어 저렴.

- Q: 스레드 간 공유 메모리의 위험성은?
  A: Race Condition(경쟁 상태). 여러 스레드가 동시에 공유 변수를 읽고 쓰면 예상치 못한 결과 발생. 예: counter++는 읽기-수정-쓰기 3단계 연산이라 스레드 A와 B가 동시에 실행하면 하나의 증가가 사라질 수 있음. 뮤텍스/세마포어로 동기화 필요.

- Q: 프로세스가 스레드보다 유리한 경우는?
  A: 장애 격리가 중요할 때. 스위치 데몬들처럼 각 기능을 독립 프로세스로 분리하면 하나가 크래시해도 다른 기능은 영향 없음. Chrome 탭마다 별도 프로세스를 쓰는 것도 같은 이유.

---

## 관련 개념

- [02-02 멀티프로세스 vs 멀티스레드](./02-02-multiprocess-multithread.md)
- [02-03 인터럽트 / 시스템 콜](./02-03-interrupt-syscall.md)
- [02-05 동기화](./02-05-synchronization.md) — 스레드 공유 메모리의 Race Condition 해결
