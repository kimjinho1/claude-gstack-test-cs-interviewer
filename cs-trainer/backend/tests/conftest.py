"""
공통 pytest fixtures
- 인메모리 SQLite DB 셋업
- FastAPI dependency override (get_db, get_current_user_id)
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.db import Base, get_db
from backend.auth.jwt_utils import get_current_user_id

SQLALCHEMY_DATABASE_URL = "sqlite://"
TEST_USER_ID = "user-test-001"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def override_get_user():
    return TEST_USER_ID


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """세션 시작 시 테이블 생성"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_tables():
    """각 테스트마다 테이블 데이터 초기화"""
    yield
    for table in reversed(Base.metadata.sorted_tables):
        engine.execute = None  # 안전하게
        with engine.connect() as conn:
            conn.execute(table.delete())
            conn.commit()


@pytest.fixture(scope="session")
def test_client():
    from backend.main import app
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_id] = override_get_user
    with TestClient(app) as c:
        yield c
