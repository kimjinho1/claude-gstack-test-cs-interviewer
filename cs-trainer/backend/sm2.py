from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class SM2Result:
    ease_factor: float
    interval: int
    repetitions: int
    next_review_at: datetime

def sm2_update(ease: float, interval: int, reps: int, score: int) -> SM2Result:
    """
    SM-2 spaced repetition algorithm.
    score: 0-10 (pass threshold = 7)
    """
    if score >= 7:  # pass
        if reps == 0:
            new_interval = 1
        elif reps == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease)
        new_reps = reps + 1
        new_ease = max(1.3, ease + 0.1 - (10 - score) * (0.08 + (10 - score) * 0.02))
    else:  # fail → reset
        new_reps = 0
        new_interval = 1
        new_ease = ease  # ease doesn't change on fail

    next_review_at = datetime.utcnow() + timedelta(days=new_interval)
    return SM2Result(
        ease_factor=round(new_ease, 3),
        interval=new_interval,
        repetitions=new_reps,
        next_review_at=next_review_at,
    )
