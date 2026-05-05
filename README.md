# CS Interview Trainer

AI가 면접관이 되어 CS 지식을 평가하고, 부족한 부분을 추적해주는 개인 공부 도구.

직접 만든 CS 학습 자료(`/docs`)를 기반으로 질문을 생성하고, 음성으로 대답하면 Claude가 실시간으로 채점한다.

**배포:** ~~[https://cs-pi-wine.vercel.app/](https://cs-pi-wine.vercel.app/)~~

---

## 개발 노트

> **이 프로젝트의 코드는 단 한 줄도 내가 직접 짜지 않았다.**

**[Claude Code](https://claude.ai/code)** (Anthropic의 AI 코딩 도구)와 **[gstack](https://github.com/garrytan/gstack)** (Claude Code용 개발 워크플로우 툴킷)이 모든 코드를 작성했다.

| 역할 | 담당 |
|------|------|
| 아이디어 | 사람 |
| 방향 결정 및 요구사항 정의 | 사람 |
| **`docs/` CS 학습 자료 작성** | **Claude Code** |
| **백엔드 코드 전체** | **Claude Code** |
| **프론트엔드 코드 전체** | **Claude Code** |
| **Docker / Nginx / CI-CD 설정** | **Claude Code** |
| **Fly.io + Vercel 배포 설정** | **Claude Code + 사람** |
| **버그 수정 및 QA** | **Claude Code** |

전체 구현 흐름:

1. `/office-hours` — 아이디어 구체화 및 설계 문서 작성
2. `/plan-ceo-review` — 제품 전략 및 스코프 검토
3. `/plan-eng-review` — 아키텍처 및 구현 계획 검토
4. **Plan 승인 후 구현** — Claude Code가 백엔드, 프론트엔드, Docker, 배포 설정 전부 작성
5. `/review` — 코드 리뷰
6. `/qa` — 헤드리스 브라우저로 전체 페이지 QA 테스트 (헬스 스코어 91/100)
7. `/ship` — 커밋 및 push
8. **이후 반복** — 추가 요구사항 및 수정 사항을 계속 요청하며 개선

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
- Google OAuth 클라이언트 ID/시크릿 (위 [Google Cloud Console 설정](#google-cloud-console-설정-oauth-앱-생성) 참고)

### 실행

```bash
git clone https://github.com/kimjinho1/CS.git
cd CS/cs-trainer

# 환경변수 설정
cat > .env << EOF
ANTHROPIC_API_KEY=sk-xxx
GOOGLE_CLIENT_ID=구글-클라이언트-ID
GOOGLE_CLIENT_SECRET=구글-클라이언트-시크릿
JWT_SECRET=local-dev-secret
EOF

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
| Vercel | React 프론트엔드 | Vercel 대시보드에서 확인 |

### Google Cloud Console 설정 (OAuth 앱 생성)

1. [console.cloud.google.com](https://console.cloud.google.com) 접속
2. 프로젝트 생성 또는 선택
3. **APIs & Services → OAuth consent screen**
   - User Type: External → Create
   - App name, support email 입력 → Save
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Name: 아무거나 (예: cs-trainer)
   - **Authorized redirect URIs** 추가:
     - 배포용: `https://cs-trainer-api.fly.dev/api/auth/google/callback`
     - 로컬용: `http://localhost:8001/api/auth/google/callback`
5. 생성 후 **Client ID**와 **Client Secret** 복사

### 백엔드 (Fly.io)

```bash
cd CS/  # 루트 디렉토리에서 실행

fly auth login
fly launch --name cs-trainer-api --dockerfile cs-trainer/Dockerfile.backend --no-deploy
fly volumes create storage_data --region nrt --size 1

# 환경변수 설정 (전체)
fly secrets set ANTHROPIC_API_KEY=sk-xxx
fly secrets set GOOGLE_CLIENT_ID=구글-클라이언트-ID
fly secrets set GOOGLE_CLIENT_SECRET=구글-클라이언트-시크릿
fly secrets set JWT_SECRET=$(openssl rand -hex 32)   # 랜덤 비밀키
fly secrets set API_BASE_URL=https://cs-trainer-api.fly.dev
fly secrets set FRONTEND_URL=https://실제-vercel-url.vercel.app   # Vercel 대시보드에서 확인
fly secrets set ALLOWED_ORIGINS=https://실제-vercel-url.vercel.app,http://localhost:5174
fly secrets set DOCS_PATH=/app/docs

fly deploy --dockerfile cs-trainer/Dockerfile.backend
```

> **주의**: `FRONTEND_URL`과 `ALLOWED_ORIGINS`에는 Vercel 대시보드에서 확인한 실제 URL을 넣어야 한다. `cs-trainer.vercel.app` 같은 커스텀 도메인을 설정하지 않은 경우 자동 생성된 URL(`xxx.vercel.app`)을 사용.

### 환경변수 설명

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `GOOGLE_CLIENT_ID` | Google OAuth 클라이언트 ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth 클라이언트 시크릿 |
| `JWT_SECRET` | JWT 서명 비밀키 (랜덤 문자열, 유출 금지) |
| `API_BASE_URL` | 백엔드 공개 URL (OAuth 콜백 URI 생성에 사용) |
| `FRONTEND_URL` | 프론트엔드 URL (OAuth 후 리다이렉트 대상) |
| `ALLOWED_ORIGINS` | CORS 허용 도메인 (쉼표 구분, 정확히 일치해야 함) |
| `DOCS_PATH` | CS 학습 자료 경로 (Docker 기준 `/app/docs`) |

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

# 백엔드만 재빌드 후 재시작 (프론트엔드 유지)
docker compose -f cs-trainer/docker-compose.yml build backend && docker compose -f cs-trainer/docker-compose.yml up -d backend
```

### 프론트엔드 (Vercel)

1. [vercel.com](https://vercel.com) → New Project → GitHub 연동
2. Root Directory: `cs-trainer/frontend`
3. Framework: Vite → Deploy

### 프론트엔드 재배포 (코드 수정 후)

GitHub에 push하면 Vercel이 자동으로 감지해서 재배포함.

```bash
git add .
git commit -m "feat: ..."
git push
```

### CI/CD — 백엔드 자동 배포 (GitHub Actions)

`main` 브랜치에 push할 때 `cs-trainer/backend/`, `Dockerfile.backend`, `docs/` 변경이 있으면 Fly.io에 자동 배포된다.

**최초 설정 (한 번만):**

1. Fly.io API 토큰 발급:
   ```bash
   fly auth token
   ```
2. GitHub 레포 → **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `FLY_API_TOKEN`
   - Value: 위에서 나온 토큰

이후 코드 push만 하면 자동 배포됨.

---

## 배포 트러블슈팅

### Vercel — SPA 라우팅 + API 프록시

`vercel.json`은 반드시 `routes` 포맷을 사용해야 한다. `rewrites` 포맷은 `/api/*` 프록시와 SPA 폴백을 동시에 처리하지 못한다.

```json
{
  "routes": [
    { "src": "/api/(.*)", "dest": "https://cs-trainer-api.fly.dev/api/$1" },
    { "handle": "filesystem" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

순서 중요: API 프록시 → 정적 파일 → SPA 폴백.

### Vercel — 실제 배포 URL 확인

`cs-trainer.vercel.app` 같은 URL은 내 프로젝트가 아닐 수 있다. Vercel 대시보드 → 프로젝트 → **Domains** 탭에서 실제 URL을 확인해야 한다.

### Fly.io — FRONTEND_URL 불일치 시 OAuth 리다이렉트 오류

Google OAuth 로그인 후 엉뚱한 사이트로 리다이렉트되면 `FRONTEND_URL`이 잘못 설정된 것이다.

```bash
fly secrets set FRONTEND_URL=https://실제-vercel-url.vercel.app
fly secrets set ALLOWED_ORIGINS=https://실제-vercel-url.vercel.app,http://localhost:5174
```

### Fly.io — OAuth `invalid_client` 오류

Fly.io에 Google OAuth 키가 제대로 설정됐는지 확인:

```bash
fly secrets set GOOGLE_CLIENT_ID=실제-클라이언트-ID
fly secrets set GOOGLE_CLIENT_SECRET=실제-클라이언트-시크릿
```

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

