"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-23
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("email", sa.String()),
        sa.Column("name", sa.String()),
        sa.Column("avatar_url", sa.String()),
        sa.Column("created_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_user_provider", "users", ["provider", "provider_id"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mode", sa.String()),
        sa.Column("topic", sa.String()),
        sa.Column("total_score", sa.Float()),
        sa.Column("duration_s", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "question_attempts",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("session_id", sa.String(), sa.ForeignKey("sessions.id")),
        sa.Column("question_id", sa.String()),
        sa.Column("question_text", sa.Text()),
        sa.Column("transcript", sa.Text()),
        sa.Column("score", sa.Integer()),
        sa.Column("feedback", sa.Text()),
        sa.Column("follow_up_count", sa.Integer(), server_default="0"),
        sa.Column("ease_factor", sa.Float(), server_default="2.5"),
        sa.Column("interval", sa.Integer(), server_default="1"),
        sa.Column("repetitions", sa.Integer(), server_default="0"),
        sa.Column("next_review_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_review", "question_attempts", ["next_review_at", "ease_factor"])

    op.create_table(
        "weak_topics",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("question_id", sa.String()),
        sa.Column("topic", sa.String()),
        sa.Column("file_ref", sa.String()),
        sa.Column("missed_points", sa.Text()),
        sa.Column("last_score", sa.Integer()),
        sa.Column("review_count", sa.Integer(), server_default="0"),
        sa.Column("updated_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_user_question"),
    )

    op.create_table(
        "question_cache",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("question_id", sa.String()),
        sa.Column("question_text", sa.Text()),
        sa.Column("answer_hint", sa.Text()),
        sa.Column("file_ref", sa.String()),
        sa.Column("part", sa.String()),
        sa.Column("file_hash", sa.String()),
        sa.Column("parsed_at", sa.DateTime()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id"),
    )


def downgrade() -> None:
    op.drop_table("question_cache")
    op.drop_table("weak_topics")
    op.drop_index("idx_review", table_name="question_attempts")
    op.drop_table("question_attempts")
    op.drop_table("sessions")
    op.drop_index("idx_user_provider", table_name="users")
    op.drop_table("users")
