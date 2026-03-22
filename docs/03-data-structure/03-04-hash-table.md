# 03-04 Hash Table (해시 테이블)

## 개념

Key → 해시 함수 → 인덱스 → Value. **평균 O(1)** 삽입/삭제/탐색.

```
hash("SW-01") → 3  →  bucket[3] = {"ip": "192.168.1.1"}
hash("SW-02") → 7  →  bucket[7] = {"ip": "192.168.1.2"}
hash("SW-03") → 3  →  충돌! (같은 버킷)
```

---

## 동작 원리

### 해시 함수

좋은 해시 함수의 조건:
1. 결정적 (같은 키 → 항상 같은 인덱스)
2. 균등 분포 (버킷 전체에 고르게)
3. 빠른 계산 O(1)

```python
# 간단한 정수 해싱
index = key % table_size

# 문자열 해싱 (djb2 알고리즘)
def hash_str(key: str, size: int) -> int:
    h = 5381
    for ch in key:
        h = ((h << 5) + h) + ord(ch)  # h*33 + c
    return h % size
```

### 충돌 해결 방법

#### 1. Chaining (체이닝) — Python dict 방식

같은 버킷에 연결 리스트로 이어 붙임.

```
bucket[3] → [("SW-01", data1)] → [("SW-03", data3)] → None

삽입: bucket[h] 리스트에 추가
조회: bucket[h] 리스트 순회하며 키 비교

최선: O(1) — 버킷당 원소 1개
최악: O(N) — 모든 키가 같은 버킷 (나쁜 해시 함수)
평균: O(1) — 적재율 α = N/M 이 작을 때 (N=원소 수, M=버킷 수)
```

#### 2. Open Addressing (개방 주소법) — 충돌 시 다른 빈 버킷 사용

```
Linear Probing (선형 탐사):
  충돌 시 → 다음 빈 슬롯 찾을 때까지 +1씩 이동
  문제: 클러스터링 (연속된 슬롯이 꽉 차면 탐색 길어짐)

Quadratic Probing (이차 탐사):
  충돌 시 → +1², +2², +3² 간격으로 탐사
  클러스터링 완화

Double Hashing (이중 해싱):
  충돌 시 두 번째 해시 함수로 간격 결정
  h(k, i) = (h1(k) + i × h2(k)) % M
  가장 균등한 분포
```

### 적재율 (Load Factor)

```
적재율 α = 저장된 원소 수 / 버킷 수

α가 커지면:
  - 충돌 빈도 증가 → 성능 저하
  - Chaining: α > 0.75 → 리해싱 (버킷 2배 확장)
  - Open Addressing: α > 0.5~0.7 → 리해싱

Python dict 리해싱:
  버킷 수 2배 → 모든 원소 재삽입 → O(N)
  amortized O(1) (가끔만 발생)
```

### Python dict 내부

```
CPython dict (3.6+):
  - Open Addressing + Compact hash table
  - 초기 버킷: 8개
  - 적재율 2/3 초과 시 리해싱
  - 삽입 순서 보장 (Python 3.7+)
  - 동일 키 비교: 먼저 해시값, 다르면 패스, 같으면 == 비교

id() vs hash():
  기본 객체: hash = id 기반 (주소)
  str: 내용 기반 → 같은 값이면 같은 해시
  list: unhashable (가변 → 해시 불가)
```

---

## 예시 코드 (Python)

```python
from typing import Optional


# ── 해시 테이블 직접 구현 ────────────────────────────

class HashTable:
    """Chaining 방식 해시 테이블"""
    INITIAL_SIZE = 8
    LOAD_FACTOR  = 0.75

    def __init__(self):
        self._size    = self.INITIAL_SIZE
        self._count   = 0
        self._buckets: list[list] = [[] for _ in range(self._size)]

    def _hash(self, key) -> int:
        return hash(key) % self._size

    def put(self, key, value):
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket[i] = (key, value)  # 업데이트
                return
        bucket.append((key, value))
        self._count += 1
        if self._count / self._size > self.LOAD_FACTOR:
            self._rehash()

    def get(self, key, default=None):
        idx = self._hash(key)
        for k, v in self._buckets[idx]:
            if k == key:
                return v
        return default

    def delete(self, key) -> bool:
        idx = self._hash(key)
        bucket = self._buckets[idx]
        for i, (k, _) in enumerate(bucket):
            if k == key:
                bucket.pop(i)
                self._count -= 1
                return True
        return False

    def _rehash(self):
        old_buckets = self._buckets
        self._size *= 2
        self._buckets = [[] for _ in range(self._size)]
        self._count = 0
        for bucket in old_buckets:
            for k, v in bucket:
                self.put(k, v)
        print(f"  [rehash] 버킷 수 확장: {self._size//2} → {self._size}")

    def load_factor(self) -> float:
        return self._count / self._size

    def stats(self):
        lengths = [len(b) for b in self._buckets]
        used = sum(1 for l in lengths if l > 0)
        print(f"  버킷: {self._size}개, 사용: {used}개, "
              f"원소: {self._count}개, 적재율: {self.load_factor():.2f}")
        max_chain = max(lengths)
        if max_chain > 1:
            print(f"  최대 체인 길이: {max_chain} (충돌 {max_chain-1}회)")


# ── LRU 캐시: 해시맵 + 이중 연결 리스트 ─────────────

class LRUCache:
    """
    O(1) get/put 모두 보장하는 LRU 캐시
    해시맵: key → 노드 (O(1) 조회)
    이중 연결 리스트: 최근 사용 순서 유지 (O(1) 이동)

    실제 NMS에서 장비 상태 캐시에 사용
    """
    class _Node:
        def __init__(self, key=None, val=None):
            self.key = key
            self.val = val
            self.prev = self.next = None

    def __init__(self, capacity: int):
        self.cap = capacity
        self.map: dict = {}
        # 더미 head(최오래됨) / tail(최최근) sentinel
        self.head, self.tail = self._Node(), self._Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _insert_front(self, node):   # tail 바로 앞 = 가장 최근
        node.prev = self.tail.prev
        node.next = self.tail
        self.tail.prev.next = node
        self.tail.prev = node

    def get(self, key) -> int:
        if key not in self.map:
            return -1
        node = self.map[key]
        self._remove(node)
        self._insert_front(node)      # 최근 사용으로 이동
        return node.val

    def put(self, key: int, value: int):
        if key in self.map:
            self._remove(self.map[key])
        node = self._Node(key, value)
        self.map[key] = node
        self._insert_front(node)
        if len(self.map) > self.cap:
            lru = self.head.next       # 가장 오래된 노드
            self._remove(lru)
            del self.map[lru.key]

    def keys(self) -> list:
        result, curr = [], self.head.next
        while curr != self.tail:
            result.append(curr.key)
            curr = curr.next
        return result[::-1]  # 최근 → 오래된 순


# ── 실전: 장비 MAC 테이블 (해시 테이블 활용) ─────────

class MACTable:
    """
    스위치 MAC 테이블: MAC주소 → (포트, VLAN, timestamp)
    O(1) 학습/조회/에이징
    """
    def __init__(self, max_entries: int = 8192):
        self._table: dict[str, dict] = {}
        self._max = max_entries
        import time
        self._time = time.time

    def learn(self, mac: str, port: int, vlan: int):
        self._table[mac] = {"port": port, "vlan": vlan, "ts": self._time()}

    def lookup(self, mac: str) -> Optional[dict]:
        return self._table.get(mac)

    def age_out(self, timeout: float = 300):
        import time
        now = time.time()
        expired = [k for k, v in self._table.items() if now - v["ts"] > timeout]
        for mac in expired:
            del self._table[mac]
        return len(expired)

    def __len__(self): return len(self._table)


# ── 실행 ─────────────────────────────────────────────

print("=== 해시 테이블 동작 ===")
ht = HashTable()
for i in range(10):
    ht.put(f"SW-{i:02d}", {"ip": f"192.168.1.{i+1}", "vlan": 10})
ht.stats()
print(f"  SW-03: {ht.get('SW-03')}")
ht.delete("SW-03")
print(f"  SW-03 삭제 후: {ht.get('SW-03', '없음')}")

print("\n=== LRU 캐시 ===")
lru = LRUCache(3)
for k, v in [(1, 100), (2, 200), (3, 300)]:
    lru.put(k, v)
print(f"  초기: {lru.keys()}")
lru.get(1)              # 1을 최근 사용으로
print(f"  get(1) 후: {lru.keys()}")
lru.put(4, 400)         # 4 추가 → 가장 오래된 2 제거
print(f"  put(4) 후: {lru.keys()} (2 제거됨)")

print("\n=== MAC 테이블 ===")
mac_table = MACTable()
mac_table.learn("AA:BB:CC:DD:EE:01", port=1, vlan=10)
mac_table.learn("AA:BB:CC:DD:EE:02", port=2, vlan=20)
result = mac_table.lookup("AA:BB:CC:DD:EE:01")
print(f"  MAC 조회: {result}")
print(f"  테이블 크기: {len(mac_table)}")
```

---

## 면접 예상 질문

- Q: 해시 충돌이란? 해결 방법은?
  A: 서로 다른 키가 같은 해시 인덱스로 매핑되는 현상. 해결: ① Chaining — 같은 버킷에 LinkedList로 연결(Python dict 방식). 삽입 쉽지만 포인터 오버헤드. ② Open Addressing — 충돌 시 빈 슬롯 탐색(Linear/Quadratic Probing, Double Hashing). 캐시 친화적이나 클러스터링 문제.

- Q: 해시 테이블의 평균 O(1)이 보장되는 조건은?
  A: 좋은 해시 함수(균등 분포)와 낮은 적재율. Python dict는 2/3 초과 시 리해싱(버킷 2배 확장)으로 적재율 유지. 적재율이 낮으면 충돌 드물어 평균 탐색 체인 길이 ≈ 1 → O(1). 나쁜 해시 함수 → 모든 키 같은 버킷 → O(N).

- Q: LRU 캐시를 O(1)으로 구현하는 방법은?
  A: 해시맵 + 이중 연결 리스트. 해시맵: key → 노드 O(1) 조회. 이중 연결 리스트: 최근 사용 순서 유지, 노드 앞으로 이동 O(1), 가장 오래된 것(head 다음) 제거 O(1). get/put 모두 O(1). Python의 `collections.OrderedDict`가 이 구조.

---

## 관련 개념

- [03-02 Array/LinkedList](./03-02-array-linkedlist.md) — Chaining에서 LinkedList 사용
- [03-01 Big-O](./03-01-big-o.md) — amortized O(1) 분석
- [03-07 Tree](./03-07-tree.md) — TreeMap은 O(log N)이지만 순서 보장
