# CS Interview Trainer

AI가 면접관이 되어 CS 지식을 평가하고, 부족한 부분을 추적해주는 개인 공부 도구.

직접 만든 CS 학습 자료(`/docs`)를 기반으로 질문을 생성하고, 음성으로 대답하면 Claude가 실시간으로 채점한다.

---

## 기능

- **인터뷰 모드** — 주제(네트워크/OS/자료구조/DB)를 선택하면 랜덤 질문 + 심화 꼬리질문 최대 2회
- **퀴즈 모드** — SM-2 알고리즘 기반 복습 스케줄링. 틀린 문제는 더 자주 등장
- **모의 면접 모드** — 혼합 주제 8~10문제, 30분 타이머, 실전 시뮬레이션
- **음성 답변** — Web Speech API로 말하면 텍스트 변환 후 제출
- **TTS 문제 읽기** — 질문이 자동으로 소리 내어 읽힘
- **약점 노트** — 점수 7점 미만 항목 자동 기록
- **히스토리** — 세션별 점수 및 소요 시간 추적

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Backend | FastAPI, SQLAlchemy, SQLite, Anthropic Claude API |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Recharts |
| AI | Claude (claude-sonnet) — 답변 채점 및 꼬리질문 생성 |
| 복습 알고리즘 | SM-2 (SuperMemo 2) |
| 배포 | Docker Compose (로컬), Fly.io (백엔드), Vercel (프론트엔드) |

---

## 로컬 실행

### 사전 준비
- Docker Desktop
- Anthropic API 키

### 실행

```bash
git clone https://github.com/kimjinho1/CS.git
cd CS/cs-trainer

# 환경변수 설정
echo "ANTHROPIC_API_KEY=sk-xxx" > .env

# 빌드 및 실행 (CS/ 루트에서)
cd ..
docker compose -f cs-trainer/docker-compose.yml up -d
```

브라우저에서 `http://localhost:5174` 접속.

---

## 배포

| 서비스 | 역할 | URL |
|--------|------|-----|
| Fly.io | FastAPI 백엔드 + SQLite | `cs-trainer-api.fly.dev` |
| Vercel | React 프론트엔드 | `cs-trainer.vercel.app` |

### 백엔드 (Fly.io)

```bash
cd CS/  # 루트 디렉토리에서 실행

fly auth login
fly launch --name cs-trainer-api --dockerfile cs-trainer/Dockerfile.backend --no-deploy
fly secrets set ANTHROPIC_API_KEY=sk-xxx
fly secrets set ALLOWED_ORIGINS=https://cs-trainer.vercel.app
fly volumes create storage_data --region nrt --size 1
fly deploy --dockerfile cs-trainer/Dockerfile.backend
```

### 백엔드 재배포 (코드/Dockerfile 수정 후)

```bash
cd CS/  # 루트 디렉토리에서 실행

fly deploy --dockerfile cs-trainer/Dockerfile.backend
```

환경변수만 바꾸는 경우 재배포 없이:

```bash
fly secrets set KEY=value  # 머신 자동 재시작
```

### 로컬 도커 재빌드 (코드 수정 후)

```bash
cd CS/  # 루트 디렉토리에서 실행

# 이미지 재빌드 후 재시작
docker compose -f cs-trainer/docker-compose.yml up -d --build

# 특정 서비스만 재빌드
docker compose -f cs-trainer/docker-compose.yml up -d --build backend
docker compose -f cs-trainer/docker-compose.yml up -d --build frontend
```

### 프론트엔드 (Vercel)

1. [vercel.com](https://vercel.com) → New Project → GitHub 연동
2. Root Directory: `cs-trainer/frontend`
3. Framework: Vite → Deploy

---

## 프로젝트 구조

```
CS/
├── docs/                   # CS 학습 자료 (백엔드가 읽어서 질문 생성)
│   ├── 01-network/
│   ├── 02-os/
│   ├── 03-data-structure/
│   └── 04-db/
└── cs-trainer/
    ├── backend/            # FastAPI
    │   ├── main.py
    │   ├── question_parser.py   # docs/ 파싱
    │   ├── routers/
    │   └── db.py
    ├── frontend/           # React + Vite
    │   ├── src/
    │   │   ├── pages/      # Interview, Quiz, Mock, History, Notes
    │   │   ├── components/ # QuestionCard, VoiceRecorder, EvalResult
    │   │   └── hooks/      # useSpeechRecognition
    │   └── vercel.json
    ├── Dockerfile.backend
    ├── docker-compose.yml
    └── fly.toml
```

---

## 개발 노트

이 프로젝트는 **Claude Code** (Anthropic의 AI 코딩 도구)와 함께 만들었다.

전체 구현 흐름:

1. `/office-hours` — 아이디어 구체화 및 설계 문서 작성
2. **Claude Code가 구현한 것**:
   - FastAPI 백엔드 전체 (라우터, DB 스키마, SM-2 알고리즘, Claude API 연동)
   - React 프론트엔드 전체 (5개 페이지, 컴포넌트, Web Speech API 훅)
   - Docker Compose + Nginx 설정
   - TypeScript 빌드 오류 수정 (QA 중 발견)
   - Fly.io + Vercel 배포 설정
3. `/qa` — 헤드리스 브라우저로 전체 페이지 QA 테스트 (헬스 스코어 91/100)
4. `/ship` — 변경사항 커밋 및 push

사람이 한 것: 아이디어, docs 폴더의 CS 학습 자료 작성, 방향 결정.
Claude Code가 한 것: 나머지 전부.
