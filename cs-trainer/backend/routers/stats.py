from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from ..auth.jwt_utils import get_current_user_id
from ..db import get_db, QuestionAttempt, Session as SessionModel, QuestionCache

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/")
def get_stats(
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    # Radar: 파트별 평균 점수 (현재 유저)
    part_scores: dict[str, list[int]] = defaultdict(list)

    attempts = (
        db.query(QuestionAttempt, QuestionCache)
        .join(SessionModel, QuestionAttempt.session_id == SessionModel.id)
        .join(QuestionCache, QuestionAttempt.question_id == QuestionCache.question_id, isouter=True)
        .filter(SessionModel.user_id == user_id)
        .all()
    )

    for attempt, qc in attempts:
        if qc and attempt.score is not None:
            part_scores[qc.part].append(attempt.score)

    radar = [
        {"part": part, "avg_score": round(sum(scores) / len(scores), 1)}
        for part, scores in sorted(part_scores.items())
        if scores
    ]

    # Trend: 최근 8주 주별 평균 (현재 유저)
    eight_weeks_ago = datetime.utcnow() - timedelta(weeks=8)
    recent_sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id, SessionModel.created_at >= eight_weeks_ago)
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
