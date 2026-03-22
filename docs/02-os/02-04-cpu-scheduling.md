# 02-04 CPU 스케줄링

## 개념

여러 프로세스/스레드가 하나의 CPU를 나눠 쓸 때 **어떤 순서로 실행할지** 결정하는 OS 기능.

**목표**: CPU 이용률 최대화, 응답 시간 최소화, 처리량 최대화, 기아(Starvation) 방지.

---

## 스케줄링 알고리즘

### 1. FCFS (First Come First Served)

도착 순서대로 실행. 가장 단순.

```
도착 순서: P1(burst=24) → P2(burst=3) → P3(burst=3)
P1────────────────────────P2───P3───
0                         24   27   30

평균 대기 시간: (0 + 24 + 27) / 3 = 17ms
```

**단점**: Convoy Effect — 긴 프로세스 뒤에 짧은 것들이 오래 기다림.

### 2. SJF (Shortest Job First)

실행 시간이 짧은 것 먼저. 평균 대기 시간 최소.

```
P1(burst=6), P2(burst=8), P3(burst=7), P4(burst=3)
정렬 후: P4(3) → P1(6) → P3(7) → P2(8)
P4──P1──────P3───────P2────────
0   3        9         16       24

평균 대기 시간: (3 + 16 + 9 + 0) / 4 = 7ms
```

**단점**: Starvation — 긴 프로세스가 영원히 실행 안 될 수 있음. 실행 시간 미리 알기 어려움.

### 3. Round Robin (RR)

Time Quantum(시간 단위)만큼 돌아가며 실행. 선점형.

```
Time Quantum = 4ms
P1(burst=24), P2(burst=3), P3(burst=3)

P1(4)─P2(3)─P3(3)─P1(4)─P1(4)─P1(4)─P1(4)─P1(4)
0     4      7     10     14    18    22    26    30

평균 응답 시간 ↑ (빠른 응답)
평균 반환 시간 ↑ (Context Switch 오버헤드)
```

**Time Quantum 크기**:
- 너무 작으면: Context Switch 오버헤드 증가
- 너무 크면: FCFS와 같아짐
- 보통 10~100ms

### 4. Priority Scheduling

우선순위 높은 것 먼저. 선점/비선점 둘 다 가능.

```
P1(priority=3), P2(priority=1), P3(priority=4), P4(priority=5), P5(priority=2)
낮을수록 우선: P2 → P5 → P1 → P3 → P4

단점: 낮은 우선순위 프로세스 Starvation
해결: Aging — 오래 기다릴수록 우선순위 점점 높임
```

### 5. MLFQ (Multi-Level Feedback Queue)

실무에서 가장 많이 쓰이는 방식. 여러 큐를 두고 동적으로 우선순위 조정.

```
Queue 1 (높은 우선순위, quantum=8ms)  ← 새 프로세스 진입
Queue 2 (중간 우선순위, quantum=16ms) ← Q1에서 내려옴
Queue 3 (낮은 우선순위, FCFS)         ← Q2에서 내려옴

규칙:
- 새 프로세스: Q1 진입
- Q1 quantum 안에 끝남: 완료 (I/O-bound로 판단, 우선순위 유지)
- Q1 quantum 초과: Q2로 이동 (CPU-bound로 판단)
- Q2 quantum 초과: Q3으로 이동
- Aging: 오래 기다리면 상위 큐로 승격
```

---

## 선점형 vs 비선점형

| 구분 | 설명 | 알고리즘 |
|------|------|---------|
| 비선점(Non-preemptive) | 실행 중인 프로세스가 자발적으로 CPU 반납 | FCFS, 비선점 SJF |
| 선점(Preemptive) | OS가 강제로 CPU 빼앗음 | RR, 선점 Priority, MLFQ |

---

## 스케줄링 성능 지표

```
도착 시간(Arrival Time): 프로세스가 Ready Queue에 들어온 시간
버스트 시간(Burst Time): CPU 실행에 필요한 시간
완료 시간(Completion Time): 실행 완료 시간
반환 시간(Turnaround Time) = 완료 - 도착
대기 시간(Waiting Time) = 반환 - 버스트
응답 시간(Response Time) = 첫 CPU 할당 - 도착
```

---

## 예시 코드 (Python)

```python
from dataclasses import dataclass, field
from collections import deque
from typing import Optional
import heapq


@dataclass
class Process:
    pid: str
    arrival: int    # 도착 시간
    burst: int      # CPU 버스트 시간
    priority: int = 0
    remaining: int = field(init=False)

    def __post_init__(self):
        self.remaining = self.burst

    def __lt__(self, other):
        return self.priority < other.priority


def fcfs(processes: list[Process]) -> dict:
    """FCFS 스케줄링"""
    sorted_procs = sorted(processes, key=lambda p: p.arrival)
    time = 0
    waiting_times = {}

    for p in sorted_procs:
        time = max(time, p.arrival)
        waiting_times[p.pid] = time - p.arrival
        time += p.burst

    avg_wait = sum(waiting_times.values()) / len(waiting_times)
    return {"algorithm": "FCFS", "avg_wait": avg_wait, "details": waiting_times}


def sjf(processes: list[Process]) -> dict:
    """SJF (비선점)"""
    procs = sorted(processes, key=lambda p: p.arrival)
    time = 0
    waiting_times = {}
    done = set()
    heap = []

    while len(done) < len(procs):
        # 현재 시간에 도착한 프로세스를 heap에 추가
        for p in procs:
            if p.pid not in done and p.arrival <= time:
                heapq.heappush(heap, (p.burst, p.pid, p))

        if heap:
            _, _, p = heapq.heappop(heap)
            waiting_times[p.pid] = time - p.arrival
            time += p.burst
            done.add(p.pid)
        else:
            time += 1  # idle

    avg_wait = sum(waiting_times.values()) / len(waiting_times)
    return {"algorithm": "SJF", "avg_wait": avg_wait, "details": waiting_times}


def round_robin(processes: list[Process], quantum: int = 4) -> dict:
    """Round Robin"""
    procs = sorted(processes, key=lambda p: p.arrival)
    remaining = {p.pid: p.burst for p in procs}
    queue = deque()
    time = 0
    first_run = {}
    completion = {}
    i = 0  # 다음 도착 프로세스 인덱스

    # 첫 번째 프로세스 추가
    if procs:
        queue.append(procs[0])
        i = 1

    while queue or i < len(procs):
        if not queue:
            time = procs[i].arrival
            queue.append(procs[i])
            i += 1

        p = queue.popleft()
        if p.pid not in first_run:
            first_run[p.pid] = time

        run_time = min(quantum, remaining[p.pid])
        time += run_time
        remaining[p.pid] -= run_time

        # 실행 중 도착한 프로세스 추가
        while i < len(procs) and procs[i].arrival <= time:
            queue.append(procs[i])
            i += 1

        if remaining[p.pid] > 0:
            queue.append(p)
        else:
            completion[p.pid] = time

    waiting_times = {
        p.pid: completion[p.pid] - p.arrival - p.burst
        for p in procs
    }
    avg_wait = sum(waiting_times.values()) / len(waiting_times)
    return {"algorithm": f"RR(q={quantum})", "avg_wait": avg_wait, "details": waiting_times}


# 시뮬레이션
processes = [
    Process("P1", arrival=0, burst=24, priority=3),
    Process("P2", arrival=0, burst=3,  priority=1),
    Process("P3", arrival=0, burst=3,  priority=4),
]

for result in [fcfs(processes), sjf(processes), round_robin(processes, quantum=4)]:
    print(f"{result['algorithm']:12} 평균 대기: {result['avg_wait']:.1f}ms  {result['details']}")
```

---

## 면접 예상 질문

- Q: Round Robin에서 Time Quantum 크기의 영향은?
  A: 너무 작으면 Context Switch가 자주 발생해 오버헤드 증가. 너무 크면 FCFS와 동일해져 긴 프로세스가 짧은 것을 오래 막음. 일반적으로 Context Switch 시간의 10배 수준(10~100ms)으로 설정.

- Q: SJF의 단점과 해결책은?
  A: 짧은 작업이 계속 들어오면 긴 작업이 영원히 CPU를 못 받는 Starvation 발생. 실행 시간을 미리 알기 어렵다는 문제도 있음. 해결: Aging(오래 기다릴수록 우선순위 높임), MLFQ(과거 CPU 사용 패턴으로 버스트 추정).

- Q: MLFQ란?
  A: 여러 우선순위 큐를 두고, 프로세스의 CPU 사용 패턴에 따라 큐 간 이동. I/O-bound는 상위 큐(높은 우선순위), CPU-bound는 하위 큐로 이동. Aging으로 Starvation 방지. Linux CFS, Windows 스케줄러가 유사한 방식.

- Q: 선점형 스케줄링이 필요한 이유는?
  A: 비선점형은 실행 중인 프로세스가 CPU를 독점할 수 있어 실시간 응답이 필요한 작업이 오래 기다릴 수 있음. 선점형은 OS가 강제로 CPU를 빼앗아 우선순위 높은 작업(인터럽트 처리, 실시간 태스크)을 즉시 실행 가능.

---

## 관련 개념

- [02-03 인터럽트 / 시스템 콜](./02-03-interrupt-syscall.md) — 타이머 인터럽트로 스케줄러 호출
- [02-05 동기화](./02-05-synchronization.md) — 스케줄링과 Race Condition 연관
- [02-06 교착상태](./02-06-deadlock.md) — Priority Inversion
