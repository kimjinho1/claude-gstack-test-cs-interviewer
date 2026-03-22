import os
import secrets
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session as DBSession

from ..auth.base import OAuthProvider
from ..auth.google import GoogleOAuthProvider
from ..auth.jwt_utils import create_token, get_current_user_id
from ..db import User, get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── 프로바이더 레지스트리 ──────────────────────────────────────
# 카카오, 네이버 등 추가 시 여기에만 등록하면 됨
PROVIDERS: dict[str, OAuthProvider] = {
    "google": GoogleOAuthProvider(),
    # "kakao": KakaoOAuthProvider(),
    # "naver": NaverOAuthProvider(),
}


def _redirect_uri(provider_name: str) -> str:
    base = os.getenv("API_BASE_URL", "http://localhost:8001")
    return f"{base}/api/auth/{provider_name}/callback"


@router.get("/{provider}/login")
def oauth_login(provider: str):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not supported")
    state = secrets.token_urlsafe(16)
    url = PROVIDERS[provider].get_authorization_url(_redirect_uri(provider), state)
    return RedirectResponse(url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str | None = None,
    db: DBSession = Depends(get_db),
):
    if provider not in PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' not supported")

    p = PROVIDERS[provider]
    try:
        tokens = await p.exchange_code(code, _redirect_uri(provider))
        user_info = await p.get_user_info(tokens)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {e}")

    # 기존 유저 조회 or 신규 생성
    user = (
        db.query(User)
        .filter(User.provider == user_info.provider, User.provider_id == user_info.provider_id)
        .first()
    )
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            provider=user_info.provider,
            provider_id=user_info.provider_id,
            email=user_info.email,
            name=user_info.name,
            avatar_url=user_info.avatar_url,
            created_at=datetime.utcnow(),
        )
        db.add(user)
    else:
        user.name = user_info.name
        user.avatar_url = user_info.avatar_url
    db.commit()

    token = create_token(user.id)
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5174")
    return RedirectResponse(f"{frontend_url}/?token={token}")


@router.get("/me")
def get_me(user_id: str = Depends(get_current_user_id), db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "provider": user.provider,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }
