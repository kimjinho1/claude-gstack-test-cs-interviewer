# 03-03 Stack / Queue / Deque

## 개념

**Stack**: LIFO(Last In First Out). 마지막에 넣은 것을 먼저 꺼냄.
**Queue**: FIFO(First In First Out). 먼저 넣은 것을 먼저 꺼냄.
**Deque**: Double-Ended Queue. 양쪽 끝에서 삽입/삭제.

---

## 동작 원리

### Stack

```
push(A) → [A]
push(B) → [A, B]
push(C) → [A, B, C]
pop()   → C,  [A, B]
pop()   → B,  [A]
peek()  → A   (꺼내지 않고 확인)

실제 사용처:
  - 함수 호출 스택 (Call Stack): 재귀 함수 → 스택 프레임 쌓임
  - 괄호 유효성 검사
  - DFS (깊이 우선 탐색)
  - 실행 취소 (Undo)
  - 역순 출력
```

### Queue

```
enqueue(A) → [A]
enqueue(B) → [A, B]
enqueue(C) → [A, B, C]
dequeue()  → A,  [B, C]
dequeue()  → B,  [C]

실제 사용처:
  - BFS (너비 우선 탐색)
  - 프린터 작업 큐
  - CPU 스케줄링 Ready Queue
  - 이벤트 처리 큐 (스위치 SNMP trap 큐)
  - 메시지 브로커 (Kafka, RabbitMQ 개념)
```

### Deque

```
appendleft(A) → [A]
append(B)     → [A, B]
appendleft(C) → [C, A, B]
popleft()     → C,  [A, B]
pop()         → B,  [A]

실제 사용처:
  - 슬라이딩 윈도우 (최솟값/최댓값)
  - BFS + 우선순위 혼합 (0-1 BFS)
  - LRU 캐시 (최근 접근 이동)
  - 브라우저 앞/뒤로 가기
```

### 구현 방식

```
Stack:  Python list (append/pop 모두 O(1))
Queue:  collections.deque (popleft() O(1))
        list를 Queue로 쓰면 popleft() = O(N) → 비효율!

왜 list의 pop(0)이 O(N)인가:
  [1, 2, 3, 4, 5]
  pop(0) 후 → [2, 3, 4, 5]
  → 뒤 원소를 전부 한 칸씩 앞으로 이동 → O(N)

deque의 popleft()가 O(1)인 이유:
  이중 연결 리스트 기반 → head 포인터만 이동
```

---

## 예시 코드 (Python)

```python
from collections import deque
from typing import Optional


# ── Stack 구현 ───────────────────────────────────────

class Stack:
    def __init__(self):
        self._data: list = []

    def push(self, item):           # O(1) amortized
        self._data.append(item)

    def pop(self):                  # O(1)
        if self.is_empty():
            raise IndexError("Stack underflow")
        return self._data.pop()

    def peek(self):                 # O(1)
        if self.is_empty():
            raise IndexError("Stack is empty")
        return self._data[-1]

    def is_empty(self) -> bool: return len(self._data) == 0
    def __len__(self):          return len(self._data)
    def __repr__(self):         return f"Stack{self._data}"


# 활용 1: 괄호 유효성 검사
def is_valid_brackets(s: str) -> bool:
    stack = Stack()
    pairs = {')': '(', ']': '[', '}': '{'}
    for ch in s:
        if ch in '([{':
            stack.push(ch)
        elif ch in ')]}':
            if stack.is_empty() or stack.pop() != pairs[ch]:
                return False
    return stack.is_empty()


# 활용 2: 후위 표기법 계산
def eval_postfix(expr: str) -> float:
    stack = Stack()
    for token in expr.split():
        if token in '+-*/':
            b, a = stack.pop(), stack.pop()
            if token == '+': stack.push(a + b)
            elif token == '-': stack.push(a - b)
            elif token == '*': stack.push(a * b)
            elif token == '/': stack.push(a / b)
        else:
            stack.push(float(token))
    return stack.pop()


# 활용 3: DFS 경로 탐색 (스위치 토폴로지)
def dfs_path(graph: dict, start: str, end: str) -> Optional[list]:
    stack = [(start, [start])]
    visited = set()
    while stack:
        node, path = stack.pop()
        if node == end:
            return path
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                stack.append((neighbor, path + [neighbor]))
    return None


# ── Queue 구현 ───────────────────────────────────────

class Queue:
    def __init__(self):
        self._data: deque = deque()  # deque 사용 → popleft O(1)

    def enqueue(self, item):        # O(1)
        self._data.append(item)

    def dequeue(self):              # O(1)
        if self.is_empty():
            raise IndexError("Queue underflow")
        return self._data.popleft()

    def front(self):
        if self.is_empty():
            raise IndexError("Queue is empty")
        return self._data[0]

    def is_empty(self) -> bool: return len(self._data) == 0
    def __len__(self):          return len(self._data)


# 활용: BFS 최단 경로 (스위치 홉 수)
def bfs_shortest(graph: dict, start: str, end: str) -> Optional[list]:
    queue = Queue()
    queue.enqueue((start, [start]))
    visited = {start}
    while not queue.is_empty():
        node, path = queue.dequeue()
        if node == end:
            return path
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.enqueue((neighbor, path + [neighbor]))
    return None


# ── Deque 활용: 슬라이딩 윈도우 최솟값 ───────────────

def sliding_window_min(arr: list[int], k: int) -> list[int]:
    """
    크기 k인 윈도우의 최솟값 — O(N)
    deque에 인덱스 저장, 앞은 현재 윈도우 최솟값 인덱스

    활용: 최근 k개 SNMP 패킷 중 최솟값 트래픽 추적
    """
    dq: deque[int] = deque()  # 인덱스 저장
    result = []

    for i, val in enumerate(arr):
        # 윈도우 벗어난 인덱스 제거
        while dq and dq[0] < i - k + 1:
            dq.popleft()
        # 현재 값보다 큰 뒤쪽 인덱스 제거 (쓸모없음)
        while dq and arr[dq[-1]] >= val:
            dq.pop()
        dq.append(i)

        if i >= k - 1:
            result.append(arr[dq[0]])
    return result


# ── 실전: 스위치 이벤트 처리 큐 ─────────────────────

class SwitchEventQueue:
    """우선순위 없는 이벤트 순차 처리 큐"""
    def __init__(self, maxsize: int = 1000):
        self._q: deque = deque(maxlen=maxsize)  # maxlen 초과 시 오래된 것 자동 제거

    def push(self, event: dict):
        self._q.append(event)

    def process_all(self):
        while self._q:
            event = self._q.popleft()
            print(f"  처리: {event['type']} (port={event.get('port', '-')})")


# ── 실행 ─────────────────────────────────────────────

print("=== 괄호 유효성 ===")
for s in ["({[]})", "([)]", "{{}}", "((("]:
    print(f"  {s!r}: {is_valid_brackets(s)}")

print("\n=== 후위 표기법 ===")
print(f"  '3 4 + 2 *' = {eval_postfix('3 4 + 2 *')}")  # (3+4)*2 = 14

print("\n=== 스위치 토폴로지 탐색 ===")
topology = {
    "SW1": ["SW2", "SW3"],
    "SW2": ["SW1", "SW4"],
    "SW3": ["SW1", "SW4"],
    "SW4": ["SW2", "SW3", "SW5"],
    "SW5": ["SW4"],
}
print(f"  DFS SW1→SW5: {dfs_path(topology, 'SW1', 'SW5')}")
print(f"  BFS SW1→SW5: {bfs_shortest(topology, 'SW1', 'SW5')}")

print("\n=== 슬라이딩 윈도우 최솟값 ===")
traffic = [3, 1, 2, 5, 2, 4, 1, 3]
print(f"  트래픽:     {traffic}")
print(f"  k=3 최솟값: {sliding_window_min(traffic, 3)}")

print("\n=== 이벤트 큐 ===")
eq = SwitchEventQueue()
eq.push({"type": "port_down", "port": 3})
eq.push({"type": "cpu_high",  "value": 90})
eq.push({"type": "ap_disconnect", "ap": "AP-01"})
eq.process_all()
```

---

## 면접 예상 질문

- Q: Python list를 Queue로 쓰면 안 되는 이유는?
  A: `list.pop(0)`이 O(N). 첫 번째 원소를 제거하면 뒤 원소 전체를 한 칸씩 앞으로 이동해야 함. `collections.deque`는 이중 연결 리스트 기반으로 `popleft()` O(1). N=100만이면 list Queue는 10억 번 연산, deque는 1번.

- Q: Stack으로 재귀를 반복문으로 바꿀 수 있는 이유는?
  A: 재귀 함수는 내부적으로 콜 스택(Call Stack)을 사용. 재귀 함수 호출 = 스택에 프레임 push, 반환 = pop. 따라서 명시적 스택 자료구조로 같은 동작을 시뮬레이션 가능. DFS가 대표적 — 재귀/스택 두 방식 모두 가능.

- Q: 슬라이딩 윈도우 최솟값을 O(N)으로 풀 수 있는 이유는?
  A: Monotonic Deque(단조 덱) 활용. deque에 인덱스를 저장하되, 현재 값보다 크거나 같은 뒤쪽 인덱스를 미리 제거. deque의 앞은 항상 현재 윈도우의 최솟값 인덱스. 각 원소는 push/pop 각 1번씩만 → O(N). 브루트포스 O(NK) 대비 압도적.

---

## 관련 개념

- [03-02 Array/LinkedList](./03-02-array-linkedlist.md) — deque의 내부 구현
- [03-06 탐색 (BFS/DFS)](./03-06-search.md) — Queue(BFS), Stack(DFS)
- [03-08 Heap](./03-08-heap.md) — 우선순위 Queue
