# 03-13 백트래킹 (Backtracking)

## 개념

**백트래킹**: 가능한 모든 해를 탐색하되, **유망하지 않은 경로는 가지치기(Pruning)**해 탐색 공간을 줄이는 기법.

```
브루트포스: 모든 경우를 전부 확인 O(N!)
백트래킹:  조건에 맞지 않으면 즉시 포기 + 되돌아감 → 실제로 훨씬 빠름

핵심 패턴:
  def backtrack(state):
      if is_solution(state):
          record(state)
          return
      for choice in choices(state):
          if is_valid(choice):       ← 가지치기
              apply(choice)
              backtrack(state)
              undo(choice)           ← 되돌아감
```

---

## 동작 원리

```
N-Queens 문제 (4×4):
  Q _ _ _   1행에 Q 놓기
  _ _ Q _   → 2행: (1,2열 불가) → 3열에 시도
  _ _ _ _   → 3행: 모든 자리 불가 → 백트래킹!
  ...

가지치기: 같은 열, 같은 대각선에 이미 Queen 있으면 즉시 skip
→ 4×4에서 256가지 → 실제 탐색 수십 개로 줄어듦
```

---

## 예시 코드 (Python)

```python
from typing import Optional


# ── N-Queens ──────────────────────────────────────────

def n_queens(n: int) -> list[list[int]]:
    """
    N×N 체스판에 N개 Queen 배치
    solutions[i] = i번째 해의 각 행에서 Queen의 열 위치
    """
    solutions = []
    cols      = set()  # 사용된 열
    diag1     = set()  # 사용된 ↘ 대각선 (row-col)
    diag2     = set()  # 사용된 ↗ 대각선 (row+col)

    def backtrack(row: int, placement: list):
        if row == n:
            solutions.append(placement[:])
            return
        for col in range(n):
            if col in cols or (row-col) in diag1 or (row+col) in diag2:
                continue  # 가지치기
            cols.add(col); diag1.add(row-col); diag2.add(row+col)
            placement.append(col)
            backtrack(row+1, placement)
            placement.pop()
            cols.remove(col); diag1.remove(row-col); diag2.remove(row+col)

    backtrack(0, [])
    return solutions


# ── 순열/조합 ─────────────────────────────────────────

def permutations(nums: list) -> list[list]:
    result = []
    def backtrack(path, remaining):
        if not remaining:
            result.append(path[:])
            return
        for i, v in enumerate(remaining):
            path.append(v)
            backtrack(path, remaining[:i] + remaining[i+1:])
            path.pop()
    backtrack([], nums)
    return result


def combinations(nums: list, k: int) -> list[list]:
    result = []
    def backtrack(start, path):
        if len(path) == k:
            result.append(path[:])
            return
        for i in range(start, len(nums)):
            path.append(nums[i])
            backtrack(i+1, path)
            path.pop()
    backtrack(0, [])
    return result


# ── 스도쿠 풀이 ───────────────────────────────────────

def solve_sudoku(board: list[list[int]]) -> bool:
    """
    9×9 스도쿠 백트래킹
    빈 칸(0) 찾아 1~9 시도, 유효하면 다음 칸으로
    """
    def is_valid(r, c, num):
        # 행 확인
        if num in board[r]: return False
        # 열 확인
        if num in [board[i][c] for i in range(9)]: return False
        # 3×3 박스 확인
        br, bc = 3*(r//3), 3*(c//3)
        for i in range(br, br+3):
            for j in range(bc, bc+3):
                if board[i][j] == num: return False
        return True

    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                for num in range(1, 10):
                    if is_valid(r, c, num):
                        board[r][c] = num
                        if solve_sudoku(board):
                            return True
                        board[r][c] = 0    # 되돌아감
                return False   # 모든 숫자 실패 → 백트래킹
    return True


# ── 실전: VLAN 접근 권한 조합 ─────────────────────────

def find_valid_vlan_sets(vlans: list[int],
                         required: int,
                         max_total: int) -> list[list[int]]:
    """
    VLAN 중 required개 선택, 합이 max_total 이하인 조합
    (포트 VLAN 할당 시 총 트래픽 제한)
    """
    result = []
    def backtrack(start, current, total):
        if len(current) == required:
            result.append(current[:])
            return
        for i in range(start, len(vlans)):
            if total + vlans[i] > max_total:
                break          # 정렬된 경우 이후도 불가 → 가지치기
            current.append(vlans[i])
            backtrack(i+1, current, total + vlans[i])
            current.pop()
    backtrack(0, [], 0)
    return result


# ── 실행 ─────────────────────────────────────────────

print("=== N-Queens ===")
for n in [4, 8]:
    sols = n_queens(n)
    print(f"  {n}-Queens: {len(sols)}개 해")
    if n == 4:
        print(f"  첫 번째 해 (열 위치): {sols[0]}")

print("\n=== 순열/조합 ===")
print(f"  [1,2,3] 순열: {permutations([1,2,3])}")
print(f"  [1,2,3,4] C 2: {combinations([1,2,3,4], 2)}")

print("\n=== VLAN 조합 ===")
vlans = sorted([10, 20, 30, 40, 50])
valid = find_valid_vlan_sets(vlans, required=3, max_total=80)
print(f"  VLAN {vlans}, 3개 선택, 합≤80:")
for combo in valid:
    print(f"    {combo} (합={sum(combo)})")
```

---

## 면접 예상 질문

- Q: 백트래킹과 브루트포스의 차이는?
  A: 브루트포스는 모든 경우를 전부 생성 후 검증(사후 필터링). 백트래킹은 탐색 중 유망하지 않은 분기를 조기에 차단(가지치기). N-Queens N=8의 경우 브루트포스는 8^8=16M가지, 백트래킹은 실제 수천 번 탐색으로 줄어듦.

- Q: 백트래킹과 DFS의 관계는?
  A: 백트래킹은 DFS의 일종. 차이는 가지치기 — DFS는 모든 노드를 방문하지만 백트래킹은 유망하지 않으면 해당 서브트리 전체를 건너뜀. DFS + 가지치기 = 백트래킹.

- Q: 백트래킹의 시간 복잡도는?
  A: 문제마다 다름. 최악은 O(N!) (모든 순열 생성). 가지치기 효과로 실제는 훨씬 적음. N-Queens N=15는 브루트포스로 사실상 불가능하지만 백트래킹으로 수백만 번 탐색으로 해결. 정확한 분석보다 가지치기 효과에 주목.

---

## 관련 개념

- [03-06 탐색 DFS](./03-06-search.md) — 백트래킹의 기반
- [03-11 DP](./03-11-dp.md) — 백트래킹을 DP로 최적화하는 경우
