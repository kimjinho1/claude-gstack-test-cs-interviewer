from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = "sqlite:///./storage/trainer.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    mode = Column(String)  # 'interview' | 'quiz' | 'mock'
    topic = Column(String)
    total_score = Column(Float)
    duration_s = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    question_attempts = relationship("QuestionAttempt", back_populates="session", lazy="selectin")

class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    question_id = Column(String)
    question_text = Column(Text)
    transcript = Column(Text)
    score = Column(Integer)
    feedback = Column(Text)
    follow_up_count = Column(Integer, default=0)
    ease_factor = Column(Float, default=2.5)
    interval = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="question_attempts")

class WeakTopic(Base):
    __tablename__ = "weak_topics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, unique=True)
    topic = Column(String)
    file_ref = Column(String)
    missed_points = Column(Text)  # JSON array string
    last_score = Column(Integer)
    review_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class QuestionCache(Base):
    __tablename__ = "question_cache"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, unique=True)
    question_text = Column(Text)
    answer_hint = Column(Text)
    file_ref = Column(String)
    part = Column(String)
    file_hash = Column(String)
    parsed_at = Column(DateTime, default=datetime.utcnow)

# Indexes
Index("idx_review", QuestionAttempt.next_review_at, QuestionAttempt.ease_factor)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import os
    os.makedirs("storage", exist_ok=True)
    Base.metadata.create_all(bind=engine)
