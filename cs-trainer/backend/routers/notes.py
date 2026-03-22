import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from ..auth.jwt_utils import get_current_user_id
from ..db import get_db, WeakTopic

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteUpdate(BaseModel):
    missed_points: list[str] | None = None


@router.get("/")
def get_notes(
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    notes = (
        db.query(WeakTopic)
        .filter(WeakTopic.user_id == user_id)
        .order_by(WeakTopic.updated_at.desc())
        .all()
    )
    return [
        {
            "id": n.id,
            "question_id": n.question_id,
            "topic": n.topic,
            "missed_points": json.loads(n.missed_points) if n.missed_points else [],
            "last_score": n.last_score,
            "review_count": n.review_count,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        }
        for n in notes
    ]


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    user_id: str = Depends(get_current_user_id),
    db: DBSession = Depends(get_db),
):
    note = db.query(WeakTopic).filter(WeakTopic.id == note_id, WeakTopic.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"ok": True}
