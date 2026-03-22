from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from ..db import get_db, QuestionAttempt, Session as SessionModel, QuestionCache

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/")
def get_stats(db: DBSession = Depends(get_db)):
    # Radar chart: average score per part
    part_scores: dict[str, list[int]] = defaultdict(list)

    attempts = db.query(QuestionAttempt, QuestionCache).join(
        QuestionCache, QuestionAttempt.question_id == QuestionCache.question_id, isouter=True
    ).all()

    for attempt, qc in attempts:
        if qc and attempt.score is not None:
            part_scores[qc.part].append(attempt.score)

    radar = [
        {"part": part, "avg_score": round(sum(scores) / len(scores), 1)}
        for part, scores in sorted(part_scores.items())
        if scores
    ]

    # Trend chart: weekly average score over last 8 weeks
    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
    recent_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.created_at >= eight_weeks_ago)
        .order_by(SessionModel.created_at)
        .all()
    )

    weekly: dict[str, list[float]] = defaultdict(list)
    for s in recent_sessions:
        if s.total_score is not None and s.created_at:
            week_key = s.created_at.strftime("%Y-W%W")
            weekly[week_key].append(s.total_score)

    trend = [
        {"week": week, "avg_score": round(sum(scores) / len(scores), 1)}
        for week, scores in sorted(weekly.items())
    ]

    return {"radar": radar, "trend": trend}
