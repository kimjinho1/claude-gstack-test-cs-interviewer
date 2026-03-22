# CS 공부 커리큘럼 — 심화 (면접 대비 / 실무)

> 언어 기준: Python | 목표: 면접 대비 + 실무 이해
> 파일명 규칙: `[파트번호]-[주제번호]-[주제명].md`

---

## 01. 네트워크 `docs/01-network/`

| 번호 | 주제 | 파일명 | 진행 |
|------|------|--------|------|
| 01-01 | OSI 7계층 / TCP-IP 4계층 | `01-01-osi-tcpip.md` | [x] |
| 01-02 | VLAN / Trunk / Access Port | `01-02-vlan.md` | [x] |
| 01-03 | ARP (IP→MAC 주소 변환) | `01-03-arp.md` | [x] |
| 01-04 | TCP vs UDP | `01-04-tcp-udp.md` | [x] |
| 01-05 | TCP 3-way / 4-way Handshake | `01-05-tcp-handshake.md` | [x] |
| 01-06 | DNS 동작 원리 | `01-06-dns.md` | [x] |
| 01-07 | HTTP vs HTTPS | `01-07-http-https.md` | [x] |
| 01-08 | HTTP/1.1 vs HTTP/2 vs HTTP/3 | `01-08-http-versions.md` | [x] |
| 01-09 | 쿠키 / 세션 / JWT | `01-09-cookie-session-jwt.md` | [ ] |
| 01-10 | REST API 설계 원칙 | `01-10-rest-api.md` | [ ] |
| 01-11 | 웹소켓 vs HTTP | `01-11-websocket.md` | [ ] |
| 01-12 | CORS | `01-12-cors.md` | [ ] |
| 01-13 | 로드 밸런싱 | `01-13-load-balancing.md` | [ ] |
| 01-14 | CDN | `01-14-cdn.md` | [ ] |
| 01-15 | 방화벽 / 프록시 / NAT | `01-15-firewall-proxy-nat.md` | [ ] |

---

## 02. 운영체제 `docs/02-os/`

| 번호 | 주제 | 파일명 | 진행 |
|------|------|--------|------|
| 02-01 | 프로세스 vs 스레드 | `02-01-process-thread.md` | [ ] |
| 02-02 | 멀티프로세스 vs 멀티스레드 | `02-02-multiprocess-multithread.md` | [ ] |
| 02-03 | 인터럽트 / 시스템 콜 | `02-03-interrupt-syscall.md` | [ ] |
| 02-04 | CPU 스케줄링 (FCFS, SJF, RR, Priority) | `02-04-cpu-scheduling.md` | [ ] |
| 02-05 | 동기화 (뮤텍스, 세마포어, 모니터) | `02-05-synchronization.md` | [ ] |
| 02-06 | 교착상태 (Deadlock) | `02-06-deadlock.md` | [ ] |
| 02-07 | 메모리 관리 (페이징, 세그멘테이션) | `02-07-memory-management.md` | [ ] |
| 02-08 | 가상 메모리 / 페이지 교체 알고리즘 | `02-08-virtual-memory.md` | [ ] |
| 02-09 | 캐시 (L1/L2/L3, 히트/미스) | `02-09-cache.md` | [ ] |
| 02-10 | 파일 시스템 | `02-10-file-system.md` | [ ] |

---

## 03. 자료구조 / 알고리즘 `docs/03-data-structure/`

| 번호 | 주제 | 파일명 | 진행 |
|------|------|--------|------|
| 03-01 | 시간/공간 복잡도 (Big-O) | `03-01-big-o.md` | [ ] |
| 03-02 | Array / LinkedList | `03-02-array-linkedlist.md` | [ ] |
| 03-03 | Stack / Queue / Deque | `03-03-stack-queue-deque.md` | [ ] |
| 03-04 | Hash Table (충돌, 해결 방법) | `03-04-hash-table.md` | [ ] |
| 03-05 | 정렬 (Quick, Merge, Heap, Counting) | `03-05-sorting.md` | [ ] |
| 03-06 | 탐색 (BFS, DFS, 이진 탐색) | `03-06-search.md` | [ ] |
| 03-07 | Tree (BST, AVL, Red-Black Tree) | `03-07-tree.md` | [ ] |
| 03-08 | Heap / Priority Queue | `03-08-heap.md` | [ ] |
| 03-09 | Graph (인접 행렬 vs 인접 리스트) | `03-09-graph.md` | [ ] |
| 03-10 | Trie | `03-10-trie.md` | [ ] |
| 03-11 | 동적 프로그래밍 (DP) | `03-11-dp.md` | [ ] |
| 03-12 | 그리디 | `03-12-greedy.md` | [ ] |
| 03-13 | 백트래킹 | `03-13-backtracking.md` | [ ] |
| 03-14 | 최단 경로 (Dijkstra, Bellman-Ford, Floyd) | `03-14-shortest-path.md` | [ ] |
| 03-15 | 최소 신장 트리 (Kruskal, Prim) | `03-15-mst.md` | [ ] |

---

## 04. 데이터베이스 `docs/04-db/`

| 번호 | 주제 | 파일명 | 진행 |
|------|------|--------|------|
| 04-01 | RDBMS vs NoSQL | `04-01-rdbms-nosql.md` | [ ] |
| 04-02 | 트랜잭션 / ACID | `04-02-transaction-acid.md` | [ ] |
| 04-03 | 조인 (Inner, Outer, Cross, Self) | `04-03-join.md` | [ ] |
| 04-04 | 정규화 / 역정규화 | `04-04-normalization.md` | [ ] |
| 04-05 | 인덱스 (B-Tree, 클러스터/논클러스터) | `04-05-index.md` | [ ] |
| 04-06 | 격리 수준 (Isolation Level) | `04-06-isolation-level.md` | [ ] |
| 04-07 | 락 (공유락, 배타락, 데드락) | `04-07-lock.md` | [ ] |
| 04-08 | 실행 계획 / 쿼리 최적화 | `04-08-query-optimization.md` | [ ] |
| 04-09 | Redis (캐시 전략, 자료구조) | `04-09-redis.md` | [ ] |
| 04-10 | 파티셔닝 / 샤딩 / 레플리케이션 | `04-10-partitioning-sharding.md` | [ ] |
| 04-11 | ORM N+1 문제 | `04-11-orm-n+1.md` | [ ] |

---

## Claude Code 사용법

주제 공부할 때 번호로 말하면 돼:

```
"01-01 OSI 7계층 정리해줘"
"03-04 Hash Table 정리해줘"
```

Claude Code가 해당 번호/파일명으로 자동 저장 + commit 해줌.
