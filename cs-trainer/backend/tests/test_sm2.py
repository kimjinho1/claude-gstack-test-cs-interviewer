import pytest
from datetime import datetime
from backend.sm2 import sm2_update

def test_pass_reps0():
    # score=8: ease = 2.5 + 0.1 - 2*(0.08+2*0.02) = 2.36 (score<10 이면 감소)
    r = sm2_update(2.5, 1, 0, 8)
    assert r.repetitions == 1
    assert r.interval == 1
    assert r.ease_factor == pytest.approx(2.36, abs=0.01)

def test_pass_reps1():
    r = sm2_update(2.5, 1, 1, 8)
    assert r.repetitions == 2
    assert r.interval == 6

def test_pass_reps2():
    r = sm2_update(2.5, 6, 2, 8)
    assert r.repetitions == 3
    assert r.interval == round(6 * 2.5)

def test_fail_resets():
    r = sm2_update(2.5, 10, 5, 4)
    assert r.repetitions == 0
    assert r.interval == 1
    assert r.ease_factor == 2.5  # ease unchanged on fail

def test_ease_clamp():
    # Repeated failures should not drop ease below 1.3
    r = sm2_update(1.4, 1, 0, 7)
    assert r.ease_factor >= 1.3

def test_next_review_in_future():
    r = sm2_update(2.5, 1, 0, 8)
    assert r.next_review_at > datetime.utcnow()

def test_perfect_score():
    r = sm2_update(2.5, 6, 2, 10)
    assert r.ease_factor > 2.5
    assert r.interval == round(6 * 2.5)

def test_boundary_score_7():
    r = sm2_update(2.5, 1, 0, 7)
    assert r.repetitions == 1  # exactly 7 = pass
