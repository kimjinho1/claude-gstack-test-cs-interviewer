"""add missing columns for existing databases

Revision ID: 002
Revises: 001
Create Date: 2026-03-23

이 마이그레이션은 alembic 도입 전 create_all로 만들어진 기존 DB에
누락된 컬럼을 안전하게 추가한다. 신규 DB는 001에서 이미 생성되므로
존재 여부를 확인 후 건너뜀.
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    return column in {col["name"] for col in inspector.get_columns(table)}


def upgrade() -> None:
    # question_attempts.next_review_at — SM-2 도입 시 추가된 컬럼
    if not _column_exists("question_attempts", "next_review_at"):
        op.add_column(
            "question_attempts",
            sa.Column("next_review_at", sa.DateTime(), nullable=True),
        )

    # question_attempts.ease_factor, interval, repetitions, follow_up_count
    for col_name, col_type, default in [
        ("ease_factor", sa.Float(), "2.5"),
        ("interval", sa.Integer(), "1"),
        ("repetitions", sa.Integer(), "0"),
        ("follow_up_count", sa.Integer(), "0"),
    ]:
        if not _column_exists("question_attempts", col_name):
            op.add_column(
                "question_attempts",
                sa.Column(col_name, col_type, server_default=default, nullable=True),
            )

    # weak_topics.review_count
    if not _column_exists("weak_topics", "review_count"):
        op.add_column(
            "weak_topics",
            sa.Column("review_count", sa.Integer(), server_default="0", nullable=True),
        )

    # sessions.duration_s
    if not _column_exists("sessions", "duration_s"):
        op.add_column(
            "sessions",
            sa.Column("duration_s", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    pass  # 컬럼 삭제는 데이터 손실 위험 — downgrade 미지원
