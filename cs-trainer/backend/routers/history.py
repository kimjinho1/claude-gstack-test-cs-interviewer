import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..auth.jwt_utils import get_current_user_id
from ..db import get_db, Session as SessionModel, QuestionAttempt

router = APIRouter(prefix="/api/history", tags=["history"])


class SessionCreate(BaseModel):
    mode: str
    topic: str | None = None
    total_score: float | None = None
    duration_s: int | None = None
    question_attempts: list[dict] = []


@router.get("/")
def get_history(
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    sessions = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == user_id)
        .order_by(SessionModel.created_at.desc())
        .limit(50)
        .all()
    )
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "mode": s.mode,
            "topic": s.topic,
            "total_score": s.total_score,
            "duration_s": s.duration_s,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "question_count": len(s.question_attempts),
            "question_attempts": [
                {
                    "question_id": qa.question_id,
                    "question_text": qa.question_text,
                    "score": qa.score,
                    "feedback": qa.feedback,
                }
                for qa in s.question_attempts
            ],
        })
    return result


@router.post("/")
def create_session(
    body: SessionCreate,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    session_id = str(uuid.uuid4())
    session = SessionModel(
        id=session_id,
        user_id=user_id,
        mode=body.mode,
        topic=body.topic,
        total_score=body.total_score,
        duration_s=body.duration_s,
        created_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    return {"id": session_id}


class SessionUpdate(BaseModel):
    total_score: float | None = None
    duration_s: int | None = None


@router.patch("/{session_id}")
def update_session(
    session_id: str,
    body: SessionUpdate,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == user_id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if body.total_score is not None:
        session.total_score = body.total_score
    if body.duration_s is not None:
        session.duration_s = body.duration_s
    db.commit()
    return {"id": session_id}


@router.get("/{session_id}")
def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_id, SessionModel.user_id == user_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "mode": session.mode,
        "topic": session.topic,
        "total_score": session.total_score,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "question_attempts": [
            {
                "question_id": qa.question_id,
                "question_text": qa.question_text,
                "transcript": qa.transcript,
                "score": qa.score,
                "feedback": qa.feedback,
                "missed_points": qa.feedback,
            }
            for qa in session.question_attempts
        ],
    }
