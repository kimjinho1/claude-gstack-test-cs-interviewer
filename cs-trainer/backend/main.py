import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect as sa_inspect
from alembic.config import Config
from alembic import command

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .routers import questions, evaluate, history, notes, stats, auth

_ALEMBIC_INI = str(Path(__file__).parent / "alembic.ini")


def _run_migrations() -> None:
    """기존 DB 감지 후 alembic stamp → upgrade head 순으로 실행"""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./storage/trainer.db")

    # storage 디렉터리 보장
    if "sqlite:///" in db_url:
        db_path = Path(db_url.split("sqlite:///", 1)[1])
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 기존 DB(alembic 도입 전)가 있으면 001로 stamp
        if db_path.exists():
            engine = create_engine(db_url)
            try:
                tables = set(sa_inspect(engine).get_table_names())
                if tables & {"users", "sessions"} and "alembic_version" not in tables:
                    logger.info("기존 DB 감지 — alembic 001로 stamp 후 마이그레이션 실행")
                    cfg = Config(_ALEMBIC_INI)
                    command.stamp(cfg, "001")
            finally:
                engine.dispose()

    cfg = Config(_ALEMBIC_INI)
    command.upgrade(cfg, "head")
    logger.info("DB 마이그레이션 완료")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_migrations()
    yield

app = FastAPI(title="CS Trainer", lifespan=lifespan)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(evaluate.router)
app.include_router(history.router)
app.include_router(notes.router)
app.include_router(stats.router)

@app.get("/api/health")
def health():
    return {"status": "ok"}
