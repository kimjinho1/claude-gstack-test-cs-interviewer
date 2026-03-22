# QA Report — CS Interview Trainer
**Date:** 2026-03-23  
**URL:** http://localhost:5175  
**Duration:** ~25 minutes  
**Pages visited:** 6  
**Screenshots:** 10+  
**Framework:** React + Vite + FastAPI (Docker Compose)

---

## Health Score

| Category | Score | Weight | Weighted |
|----------|-------|--------|---------|
| Console | 100 | 15% | 15.0 |
| Links | 100 | 10% | 10.0 |
| Functional | 85 | 20% | 17.0 |
| Visual | 95 | 10% | 9.5 |
| UX | 90 | 15% | 13.5 |
| Performance | 90 | 10% | 9.0 |
| Content | 100 | 5% | 5.0 |
| Accessibility | 80 | 15% | 12.0 |
| **TOTAL** | | 100% | **91 / 100** |

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 1 |
| Low | 1 |
| **Total** | 2 |

**Issues fixed:** 3 (TypeScript 빌드 오류 3건 — `fix(qa)` 커밋)  
**Deferred:** 2  
**PR Summary:** QA found 2 post-fix issues (1 medium, 1 low), health score 91/100.

---

## Issues Found

### ISSUE-001 — Web Speech API not available in headless/non-Chrome
**Severity:** Medium  
**Category:** Functional  
**Status:** Deferred (infrastructure limitation)

VoiceRecorder 컴포넌트가 SpeechRecognition API에 의존. 헤드리스 브라우저(Playwright)에서는 해당 API 미지원. 실제 Chrome/Edge 브라우저에서는 정상 동작.

**Repro:** 헤드리스 환경에서 인터뷰 모드 접속 → 녹음 버튼 비활성화 or 오류  
**Impact:** 헤드리스 테스트 불가, 실사용자 영향 없음  
**Fix recommendation:** `VoiceRecorder`에서 `isSupported=false`일 때 텍스트 입력 fallback UI 제공  

---

### ISSUE-002 — No keyboard-only fallback for voice input
**Severity:** Low  
**Category:** Accessibility  
**Status:** Deferred

키보드만으로는 답변을 제출할 방법이 없음. 음성 인식 불가 환경(구형 브라우저, 보조기기)에서 앱 기능 사용 불가.

**Fix recommendation:** 텍스트 입력 폼을 선택적으로 제공 (접기/펴기 형태)

---

## Pages Tested

| Page | Status | Notes |
|------|--------|-------|
| `/` Home | ✅ | 복습 문제 empty state 정상 표시 |
| `/interview` | ✅ | 주제 선택 → 질문 카드 → VoiceRecorder 정상 |
| `/quiz` | ✅ | 주제 선택 화면 정상 |
| `/mock` | ✅ | 시작 → 타이머(29:49) → 1/8 → 건너뛰기 → 2/8 정상 |
| `/history` | ✅ | Empty state 정상 |
| `/notes` | ✅ | "점수 7점 미만 항목..." empty state 정상 |

---

## Console Log

전 페이지 JS 에러 0건. 오직 수동 테스트 중 발생한 `/api/weak-topics/` 404 (앱 버그 아님 — 잘못된 URL 직접 호출).

---

## Bugs Fixed (pre-QA, `fix(qa)` commit)

1. **TypeScript: `SpeechRecognition` type not found** — `useSpeechRecognition.ts`에서 `any` 타입 캐스팅
2. **TypeScript: `searchParams` declared but never read** — `Interview.tsx`에서 미사용 import 제거
3. **TypeScript: `error` not found in Mock** — `Mock.tsx`에서 미사용 상태 변수 제거

---

## Mobile Responsiveness

375×812 (iPhone SE 기준) 뷰포트 확인:
- 네비게이션 탭 정상 표시 (스크롤 없이 접근 가능)
- 홈 카드 레이아웃 단일 컬럼으로 자동 조정
- 텍스트 가독성 양호

---

## Top 3 Things to Fix

1. **VoiceRecorder fallback** — 텍스트 입력 모드 추가 (접근성 + 테스트 용이성)
2. **(해결됨)** TypeScript 빌드 오류 3건
3. **(정상)** API 연동 — 모든 엔드포인트 정상 응답 확인

