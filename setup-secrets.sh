#!/usr/bin/env bash
# cs-trainer Fly.io secrets 초기 설정 스크립트
# 실행: bash setup-secrets.sh
set -euo pipefail

APP="cs-trainer-api"

echo "=== cs-trainer-api secrets 설정 ==="
echo ""

# ── 직접 입력해야 하는 값들 ────────────────────────────────
read -rp "ANTHROPIC_API_KEY (sk-ant-...): " ANTHROPIC_API_KEY
read -rp "GOOGLE_CLIENT_ID: " GOOGLE_CLIENT_ID
read -rsp "GOOGLE_CLIENT_SECRET: " GOOGLE_CLIENT_SECRET
echo ""

# ── 자동 생성 ────────────────────────────────────────────
JWT_SECRET=$(openssl rand -base64 48 | tr -d '\n')
echo "JWT_SECRET 자동 생성됨 (48바이트 랜덤)"

# ── 고정값 ───────────────────────────────────────────────
API_BASE_URL="https://cs-trainer-api.fly.dev"
FRONTEND_URL="https://cs-trainer.vercel.app"
ALLOWED_ORIGINS="https://cs-trainer.vercel.app"

echo ""
echo "설정할 값:"
echo "  ANTHROPIC_API_KEY = ${ANTHROPIC_API_KEY:0:20}..."
echo "  GOOGLE_CLIENT_ID  = $GOOGLE_CLIENT_ID"
echo "  JWT_SECRET        = ${JWT_SECRET:0:20}..."
echo "  API_BASE_URL      = $API_BASE_URL"
echo "  FRONTEND_URL      = $FRONTEND_URL"
echo "  ALLOWED_ORIGINS   = $ALLOWED_ORIGINS"
echo ""

read -rp "계속하시겠습니까? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo "취소됨"
  exit 0
fi

flyctl secrets set \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
  GOOGLE_CLIENT_SECRET="$GOOGLE_CLIENT_SECRET" \
  JWT_SECRET="$JWT_SECRET" \
  API_BASE_URL="$API_BASE_URL" \
  FRONTEND_URL="$FRONTEND_URL" \
  ALLOWED_ORIGINS="$ALLOWED_ORIGINS" \
  --app "$APP"

echo ""
echo "✓ Secrets 설정 완료"
echo ""
echo "다음 단계: flyctl deploy --dockerfile cs-trainer/Dockerfile.backend --remote-only"
