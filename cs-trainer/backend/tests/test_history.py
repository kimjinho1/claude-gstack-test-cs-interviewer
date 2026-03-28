"""
routers/history.py 테스트
- POST /api/history/  — 세션 생성
- PATCH /api/history/{id} — 세션 업데이트
- GET  /api/history/  — 히스토리 목록
- GET  /api/history/{id} — 세션 상세
"""
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db import Base, get_db, Session as SessionModel
from backend.auth.jwt_utils import get_current_user_id

# ─── 인메모리 SQLite + TestClient 설정 ────────────────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

TEST_USER_ID = "user-test-001"


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user_id] = lambda: TEST_USER_ID

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """각 테스트마다 테이블 데이터만 삭제 (drop/recreate 하지 않음)"""
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


# ─── helpers ─────────────────────────────────────────────────────────────────

def create_session(**kwargs):
    payload = {"mode": "quiz", **kwargs}
    return client.post("/api/history/", json=payload).json()["id"]


def insert_session(session_id: str, user_id: str, mode: str = "quiz"):
    db = TestingSessionLocal()
    db.add(SessionModel(
        id=session_id,
        user_id=user_id,
        mode=mode,
        created_at=datetime.utcnow(),
    ))
    db.commit()
    db.close()


# ─── POST /api/history/ ───────────────────────────────────────────────────────

class TestCreateSession:
    def test_creates_session_returns_id(self):
        resp = client.post("/api/history/", json={"mode": "quiz", "topic": "01-network"})
        assert resp.status_code == 200
        assert "id" in resp.json()
        assert len(resp.json()["id"]) == 36  # UUID 형식

    def test_minimal_body(self):
        resp = client.post("/api/history/", json={"mode": "interview"})
        assert resp.status_code == 200

    def test_ids_are_unique(self):
        id1 = client.post("/api/history/", json={"mode": "quiz"}).json()["id"]
        id2 = client.post("/api/history/", json={"mode": "quiz"}).json()["id"]
        assert id1 != id2


# ─── PATCH /api/history/{id} ─────────────────────────────────────────────────

class TestUpdateSession:
    def test_update_score(self):
        sid = create_session()
        resp = client.patch(f"/api/history/{sid}", json={"total_score": 8.5})
        assert resp.status_code == 200
        assert resp.json()["id"] == sid

    def test_update_duration(self):
        sid = create_session()
        resp = client.patch(f"/api/history/{sid}", json={"duration_s": 300})
        assert resp.status_code == 200

    def test_update_both_fields(self):
        sid = create_session()
        resp = client.patch(f"/api/history/{sid}", json={"total_score": 7.0, "duration_s": 120})
        assert resp.status_code == 200

    def test_not_found_returns_404(self):
        resp = client.patch("/api/history/nonexistent-id", json={"total_score": 5.0})
        assert resp.status_code == 404

    def test_empty_body_is_ok(self):
        sid = create_session()
        resp = client.patch(f"/api/history/{sid}", json={})
        assert resp.status_code == 200

    def test_other_user_cannot_update(self):
        insert_session("other-session-id", "other-user-999")
        resp = client.patch("/api/history/other-session-id", json={"total_score": 9.0})
        assert resp.status_code == 404


# ─── GET /api/history/ ───────────────────────────────────────────────────────

class TestGetHistory:
    def test_empty_returns_list(self):
        resp = client.get("/api/history/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_created_sessions(self):
        create_session(mode="quiz")
        create_session(mode="interview")
        resp = client.get("/api/history/")
        assert len(resp.json()) == 2

    def test_sorted_newest_first(self):
        create_session(mode="quiz")
        id2 = create_session(mode="interview")
        data = client.get("/api/history/").json()
        assert data[0]["id"] == id2

    def test_does_not_return_other_users_sessions(self):
        insert_session("other-s", "other-user")
        data = client.get("/api/history/").json()
        assert all(s["id"] != "other-s" for s in data)


# ─── GET /api/history/{id} ───────────────────────────────────────────────────

class TestGetSession:
    def test_returns_session_detail(self):
        sid = create_session(mode="quiz", topic="01-network")
        resp = client.get(f"/api/history/{sid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sid
        assert data["mode"] == "quiz"

    def test_not_found_returns_404(self):
        resp = client.get("/api/history/does-not-exist")
        assert resp.status_code == 404

    def test_other_user_session_returns_404(self):
        insert_session("private-session", "other-user")
        resp = client.get("/api/history/private-session")
        assert resp.status_code == 404
