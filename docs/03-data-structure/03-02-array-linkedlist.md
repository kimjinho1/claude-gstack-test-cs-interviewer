# 03-02 Array / LinkedList

## 개념

**Array(배열)**: 메모리에 **연속**으로 저장된 같은 타입의 원소 집합. 인덱스로 O(1) 접근.
**LinkedList(연결 리스트)**: 각 노드가 데이터 + 다음 노드 포인터를 가짐. 메모리 비연속.

---

## 동작 원리

### Array — 왜 인덱스 접근이 O(1)인가

```
메모리 주소 계산:
  arr[i] 주소 = 배열 시작 주소 + i × 원소 크기
  arr[3] = 0x1000 + 3 × 4 = 0x100C  (int = 4바이트)

→ 곱셈 1번, 덧셈 1번 → 항상 O(1)
→ i가 1이든 1000이든 동일한 비용
```

배열 연산 복잡도:

```
접근   arr[i]        O(1)   — 주소 계산
탐색   값 찾기       O(N)   — 최악 끝까지 순회
삽입   맨 앞         O(N)   — 기존 원소 전부 오른쪽으로 이동
삽입   맨 뒤         O(1)   — 빈 자리에 바로 쓰기 (amortized)
삭제   중간          O(N)   — 뒤 원소 전부 왼쪽으로 이동
```

**Dynamic Array (Python list, Java ArrayList)**:
```
내부적으로 고정 크기 배열 사용.
꽉 차면 → 2배 크기 새 배열 할당 → 전체 복사 → O(N) 발생
하지만 분할 상환(amortized) 분석: 평균 O(1) (가끔만 O(N))

Python list의 append():
  99번은 O(1), 100번째(버퍼 초과)만 O(N) → 평균 O(1)
```

### LinkedList — 삽입/삭제가 O(1)인 이유

```
노드 구조:
  [data | next →] → [data | next →] → [data | None]
    Head                                  Tail

중간 삽입 (포인터 변경만):
  Before: A → B → C
  Insert X between A and B:
    X.next = B
    A.next = X
  After:  A → X → B → C
  → 포인터 2개 변경 → O(1) (삽입 위치 알고 있을 때)

단, 삽입 위치를 찾는 탐색은 O(N)
```

연결 리스트 연산 복잡도:

```
접근   i번째 노드    O(N)   — head부터 순차 이동
탐색   값 찾기       O(N)   — 순차 탐색
삽입   알고 있는 위치 O(1)  — 포인터만 변경
삭제   알고 있는 위치 O(1)  — 포인터만 변경
삽입   맨 앞         O(1)  — head 포인터만 변경
```

### 비교

| 연산 | Array | LinkedList |
|------|-------|-----------|
| 접근 (i번째) | **O(1)** | O(N) |
| 탐색 | O(N) | O(N) |
| 맨 앞 삽입/삭제 | O(N) | **O(1)** |
| 맨 뒤 삽입 | O(1)* | O(1)** |
| 중간 삽입/삭제 | O(N) | O(1)*** |
| 메모리 | 연속, 밀집 | 비연속, 포인터 오버헤드 |
| 캐시 친화성 | **높음** | 낮음 |

\* Dynamic Array amortized  ** Tail 포인터 있을 때  *** 위치를 알고 있을 때

**캐시 친화성이 중요한 이유**:
```
Array: 원소들이 메모리에 붙어 있음 → 캐시라인 1번 로드로 여러 원소 처리
LinkedList: 노드들이 메모리 곳곳에 흩어짐 → 노드마다 캐시 미스 발생

실제로 현대 CPU에서 N=1000 이하면 캐시 효과 때문에
O(N) Array가 O(1) LinkedList보다 빠른 경우가 많음
```

---

## 예시 코드 (Python)

```python
from __future__ import annotations
from typing import Optional
import time


# ── 단일 연결 리스트 ─────────────────────────────────

class Node:
    def __init__(self, data):
        self.data = data
        self.next: Optional[Node] = None


class LinkedList:
    def __init__(self):
        self.head: Optional[Node] = None
        self.tail: Optional[Node] = None
        self._size = 0

    def append(self, data):          # O(1) — tail 포인터
        node = Node(data)
        if self.tail:
            self.tail.next = node
        else:
            self.head = node
        self.tail = node
        self._size += 1

    def prepend(self, data):         # O(1) — head 변경
        node = Node(data)
        node.next = self.head
        self.head = node
        if self.tail is None:
            self.tail = node
        self._size += 1

    def delete(self, data) -> bool:  # O(N) — 탐색 후 O(1) 삭제
        prev, curr = None, self.head
        while curr:
            if curr.data == data:
                if prev:
                    prev.next = curr.next
                else:
                    self.head = curr.next
                if curr.next is None:
                    self.tail = prev
                self._size -= 1
                return True
            prev, curr = curr, curr.next
        return False

    def find(self, data) -> Optional[Node]:  # O(N)
        curr = self.head
        while curr:
            if curr.data == data:
                return curr
            curr = curr.next
        return None

    def reverse(self):               # O(N) — in-place 역순
        prev, curr = None, self.head
        self.tail = self.head
        while curr:
            nxt = curr.next
            curr.next = prev
            prev = curr
            curr = nxt
        self.head = prev

    def to_list(self) -> list:
        result, curr = [], self.head
        while curr:
            result.append(curr.data)
            curr = curr.next
        return result

    def __len__(self): return self._size
    def __repr__(self): return " → ".join(map(str, self.to_list()))


# ── 이중 연결 리스트 ─────────────────────────────────

class DNode:
    def __init__(self, data):
        self.data = data
        self.prev: Optional[DNode] = None
        self.next: Optional[DNode] = None


class DoublyLinkedList:
    """양방향 연결 리스트 — LRU 캐시 구현에 사용"""
    def __init__(self):
        # sentinel 노드 (더미 head/tail — 경계 조건 단순화)
        self.head = DNode(None)
        self.tail = DNode(None)
        self.head.next = self.tail
        self.tail.prev = self.head

    def insert_after(self, node: DNode, data) -> DNode:  # O(1)
        new = DNode(data)
        new.prev = node
        new.next = node.next
        node.next.prev = new
        node.next = new
        return new

    def remove(self, node: DNode):                        # O(1)
        node.prev.next = node.next
        node.next.prev = node.prev

    def move_to_front(self, node: DNode):                # O(1)
        self.remove(node)
        self.insert_after(self.head, node.data)

    def to_list(self) -> list:
        result, curr = [], self.head.next
        while curr != self.tail:
            result.append(curr.data)
            curr = curr.next
        return result


# ── 실전: NMS 이벤트 큐 (연결 리스트 기반) ───────────

class EventQueue:
    """
    스위치 이벤트 큐: 앞에서 꺼내고 뒤에 추가 → 연결 리스트 최적
    Array를 쓰면 앞 삭제 O(N), LinkedList는 O(1)
    """
    def __init__(self):
        self._ll = LinkedList()

    def enqueue(self, event: dict): self._ll.append(event)
    def dequeue(self) -> Optional[dict]:
        if not self._ll.head:
            return None
        data = self._ll.head.data
        self._ll.head = self._ll.head.next
        if self._ll.head is None:
            self._ll.tail = None
        self._ll._size -= 1
        return data
    def __len__(self): return len(self._ll)


# ── 성능 비교: 맨 앞 삽입 ────────────────────────────

N = 10000

# List (array) 앞 삽입: O(N) 매번
start = time.perf_counter()
lst = []
for i in range(N):
    lst.insert(0, i)   # 매번 전체 이동 → O(N²) 전체
arr_time = time.perf_counter() - start

# LinkedList 앞 삽입: O(1) 매번
start = time.perf_counter()
ll = LinkedList()
for i in range(N):
    ll.prepend(i)      # 항상 O(1) → O(N) 전체
ll_time = time.perf_counter() - start

print(f"맨 앞 삽입 {N}회:")
print(f"  list.insert(0): {arr_time*1000:.2f}ms  (O(N²) 전체)")
print(f"  LinkedList.prepend: {ll_time*1000:.2f}ms (O(N) 전체)")
print(f"  차이: {arr_time/ll_time:.1f}배")

# 기본 동작 확인
ll2 = LinkedList()
for v in [1, 2, 3, 4, 5]:
    ll2.append(v)
print(f"\n연결 리스트: {ll2}")
ll2.reverse()
print(f"역순:       {ll2}")
ll2.delete(3)
print(f"3 삭제:     {ll2}")
```

---

## 면접 예상 질문

- Q: Array와 LinkedList 중 어떤 걸 언제 쓰나?
  A: 랜덤 접근(인덱스로 특정 위치 조회)이 많으면 Array. 앞/중간에 삽입·삭제가 많으면 LinkedList. 단, 현대 CPU에서 캐시 친화성 때문에 N이 작으면 Array가 실제로 빠른 경우가 많음. Python의 list, deque는 각각 동적 배열, 이중 연결 리스트로 구현됨.

- Q: Dynamic Array의 amortized O(1)이란?
  A: append()는 대부분 O(1)이지만 배열이 꽉 찰 때마다 2배 크기로 재할당 + 전체 복사로 O(N) 발생. 총 N번 append 시 복사 횟수 = N/2 + N/4 + ... ≈ N → 평균 O(1). "가끔 비싼 연산이 있지만 평균 내면 O(1)"이 분할 상환 분석.

- Q: 연결 리스트로 O(1) 삽입인데 왜 실무에서 배열보다 느릴 수 있나?
  A: 캐시 미스. 배열은 메모리 연속 → 캐시라인 1번 로드로 여러 원소 처리. 연결 리스트는 노드가 힙 곳곳에 흩어져 노드마다 캐시 미스 발생. 특히 N이 작을 때 캐시 효과가 O 표기의 차이를 압도. 대용량 데이터나 실제 잦은 삽입/삭제에서 LinkedList 이점.

---

## 관련 개념

- [03-03 Stack/Queue](./03-03-stack-queue-deque.md) — LinkedList로 구현
- [03-04 Hash Table](./03-04-hash-table.md) — 체이닝에서 LinkedList 사용
- [03-07 Tree](./03-07-tree.md) — 노드+포인터 구조의 확장
