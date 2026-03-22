import random
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from ..db import get_db, QuestionCache, WeakTopic, QuestionAttempt
from ..question_parser import parse_all_questions, needs_reparse

router = APIRouter(prefix="/api/questions", tags=["questions"])
DOCS_PATH = Path(__file__).parent.parent.parent.parent / "docs"

def _ensure_cache(db: DBSession) -> list[QuestionCache]:
    cached = db.query(QuestionCache).all()
    if needs_reparse(DOCS_PATH, cached):
        db.query(QuestionCache).delete()
        questions = parse_all_questions(DOCS_PATH)
        for q in questions:
            db.add(QuestionCache(**q))
        db.commit()
        cached = db.query(QuestionCache).all()
    return cached

@router.get("/")
def get_questions(part: str | None = Query(None), db: DBSession = Depends(get_db)):
    cached = _ensure_cache(db)
    if part:
        cached = [q for q in cached if q.part == part]
    return [{"question_id": q.question_id, "question_text": q.question_text, "part": q.part} for q in cached]

@router.get("/parts")
def get_parts(db: DBSession = Depends(get_db)):
    _ensure_cache(db)
    parts = db.query(QuestionCache.part).distinct().all()
    return sorted([p[0] for p in parts])

@router.get("/review")
def get_review_questions(db: DBSession = Depends(get_db)):
    """SM-2 daily review: questions due today."""
    now = datetime.utcnow()
    due_attempts = (
        db.query(QuestionAttempt)
        .filter(QuestionAttempt.next_review_at <= now)
        .order_by(QuestionAttempt.next_review_at)
        .limit(20)
        .all()
    )
    result = []
    seen: set[str] = set()
    for attempt in due_attempts:
        if attempt.question_id in seen:
            continue
        seen.add(attempt.question_id)
        q = db.query(QuestionCache).filter(QuestionCache.question_id == attempt.question_id).first()
        if q:
            result.append({
                "question_id": q.question_id,
                "question_text": q.question_text,
                "part": q.part,
                "last_score": attempt.score,
                "next_review_at": attempt.next_review_at.isoformat() if attempt.next_review_at else None,
            })
    return result

@router.get("/mock")
def get_mock_questions(db: DBSession = Depends(get_db)):
    """8-10 mixed questions for mock interview. Weak topics prioritized."""
    cached = _ensure_cache(db)
    parts = sorted(set(q.part for q in cached))
    weak_ids = {wt.question_id for wt in db.query(WeakTopic).all()}

    selected: list[QuestionCache] = []
    base_per_part = max(2, 10 // max(len(parts), 1))

    for part in parts:
        part_qs = [q for q in cached if q.part == part]
        weak_qs = [q for q in part_qs if q.question_id in weak_ids]
        normal_qs = [q for q in part_qs if q.question_id not in weak_ids]

        count = min(base_per_part + (1 if weak_qs else 0), len(part_qs))
        pool = (random.sample(weak_qs, min(len(weak_qs), count)) +
                random.sample(normal_qs, min(len(normal_qs), max(0, count - len(weak_qs)))))
        selected.extend(pool[:count])

    random.shuffle(selected)
    result = selected[:10]
    return [{"question_id": q.question_id, "question_text": q.question_text, "part": q.part} for q in result]
