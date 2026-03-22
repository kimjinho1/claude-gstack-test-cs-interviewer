import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..auth.jwt_utils import get_current_user_id
from ..db import get_db, QuestionAttempt, WeakTopic, Session as SessionModel
from ..ai_provider import AIProvider
from ..sm2 import sm2_update

router = APIRouter(prefix="/api", tags=["evaluate"])
_ai = AIProvider()


class EvaluateRequest(BaseModel):
    session_id: str
    question_id: str
    question_text: str
    transcript: str
    follow_up_count: int = 0


class EvaluateResponse(BaseModel):
    score: int
    feedback: str
    missed_points: list[str]
    follow_up_question: str | None = None


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(
    req: EvaluateRequest,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    # 세션이 현재 유저 소유인지 확인
    session = db.query(SessionModel).filter(
        SessionModel.id == req.session_id,
        SessionModel.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        result = await _ai.evaluate(req.question_text, req.transcript)
    except Exception as e:
        raise HTTPException(status_code=503, detail={"error": "AI evaluation failed", "message": str(e)})

    # 이 유저의 이전 SM-2 상태 조회
    prev = (
        db.query(QuestionAttempt)
        .join(SessionModel, QuestionAttempt.session_id == SessionModel.id)
        .filter(
            QuestionAttempt.question_id == req.question_id,
            SessionModel.user_id == user_id,
        )
        .order_by(QuestionAttempt.id.desc())
        .first()
    )
    ease = prev.ease_factor if prev else 2.5
    interval = prev.interval if prev else 1
    reps = prev.repetitions if prev else 0

    sm2 = sm2_update(ease, interval, reps, result.score)

    attempt = QuestionAttempt(
        session_id=req.session_id,
        question_id=req.question_id,
        question_text=req.question_text,
        transcript=req.transcript,
        score=result.score,
        feedback=result.feedback,
        follow_up_count=req.follow_up_count,
        ease_factor=sm2.ease_factor,
        interval=sm2.interval,
        repetitions=sm2.repetitions,
        next_review_at=sm2.next_review_at,
    )
    db.add(attempt)

    # 약점 노트 업데이트 (user_id 포함)
    if result.score < 7:
        existing = db.query(WeakTopic).filter(
            WeakTopic.question_id == req.question_id,
            WeakTopic.user_id == user_id,
        ).first()
        if existing:
            existing.last_score = result.score
            existing.missed_points = json.dumps(result.missed_points)
            existing.review_count += 1
            existing.updated_at = datetime.utcnow()
        else:
            db.add(WeakTopic(
                user_id=user_id,
                question_id=req.question_id,
                topic=req.question_id.split(":")[0],
                file_ref="",
                missed_points=json.dumps(result.missed_points),
                last_score=result.score,
            ))
    else:
        db.query(WeakTopic).filter(
            WeakTopic.question_id == req.question_id,
            WeakTopic.user_id == user_id,
        ).delete()

    db.commit()

    follow_up = None
    if result.score < 7 and req.follow_up_count < 2:
        try:
            fu = await _ai.get_follow_up(req.question_text, req.transcript, result.feedback)
            follow_up = fu.follow_up_question
        except Exception:
            pass

    return EvaluateResponse(
        score=result.score,
        feedback=result.feedback,
        missed_points=result.missed_points,
        follow_up_question=follow_up,
    )
