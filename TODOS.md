# TODOS — cs-trainer

## cs-trainer / Mock Interview Mode

- **Mock 모드 맞춤형 질문 선택 개선**
  **Priority:** P3
  **What:** 사용자 실력 통계(question_attempts avg_score per part)를 기반으로 Mock 모드 8~10문제를 동적으로 선택. 현재는 파트별 단순 쿼터 + weak_topics 우선 방식.
  **Why:** 세션이 쌓일수록 더 정교한 선택이 가능. 약한 파트에 더 많은 문제를 배분하면 학습 효율 향상.
  **How to start:** `routers/questions.py`의 Mock 질문 선택 로직에서 `weak_topics` 우선 비율을 동적으로 조정.
  **Effort:** S (CC: ~5분)

## cs-trainer / Performance

- **GET /api/stats 결과 인메모리 캐싱 (v2 웹 배포 대비)**
  **Priority:** P3
  **What:** `/api/stats` 엔드포인트 결과를 `functools.lru_cache` 또는 간단한 TTL dict로 1시간 캐싱.
  **Why:** 로컬 단독 앱에서는 불필요하나 v2 웹 배포 시 세션 수백 개 이상에서 stats 쿼리가 병목이 될 수 있음.
  **How to start:** `routers/stats.py`에 `@cache(ttl=3600)` 데코레이터 또는 `cachetools.TTLCache` 적용.
  **Depends on:** v2 멀티유저 배포 이후에만 의미있음.
  **Effort:** S (CC: ~10분)

## Completed

<!-- 완료된 항목은 여기로 이동 -->
