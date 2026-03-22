import hashlib
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()

def parse_questions_from_file(file_path: Path) -> list[dict]:
    """
    Parse Q:/A: blocks from a markdown file.
    Returns list of {question_id, question_text, answer_hint, file_ref, part}
    Returns [] if no Q:/A: blocks found (logs warning).
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return []

    questions = []
    # Match Q: ... A: ... patterns (multiline)
    blocks = re.findall(r"- Q:\s*(.*?)\n\s*A:\s*(.*?)(?=\n\s*-|\Z)", content, re.DOTALL)

    if not blocks:
        logger.warning(f"No Q:/A: blocks found in {file_path}")
        return []

    # Derive part from folder name
    part = file_path.parent.name  # e.g., "01-network"
    stem = file_path.stem         # e.g., "01-04-tcp-udp"

    for i, (question, answer) in enumerate(blocks, 1):
        q_text = question.strip()
        a_text = answer.strip()
        if not q_text:
            continue
        question_id = f"{stem}:{i}"
        questions.append({
            "question_id": question_id,
            "question_text": q_text,
            "answer_hint": a_text,
            "file_ref": str(file_path.relative_to(file_path.parent.parent.parent)),
            "part": part,
            "file_hash": _file_hash(file_path),
        })

    return questions

def parse_all_questions(docs_path: Path) -> list[dict]:
    """Parse all markdown files under docs_path."""
    all_questions = []
    for md_file in sorted(docs_path.rglob("*.md")):
        if md_file.name == "curriculum.md":
            continue
        questions = parse_questions_from_file(md_file)
        all_questions.extend(questions)
    logger.info(f"Parsed {len(all_questions)} questions from {docs_path}")
    return all_questions

def needs_reparse(docs_path: Path, cached_questions: list) -> bool:
    """Check if any file hash has changed since last parse."""
    if not cached_questions:
        return True
    cached_hashes = {q.question_id.split(":")[0]: q.file_hash for q in cached_questions if hasattr(q, 'file_hash') and q.file_hash}
    for md_file in docs_path.rglob("*.md"):
        if md_file.name == "curriculum.md":
            continue
        stem = md_file.stem
        current_hash = _file_hash(md_file)
        if cached_hashes.get(stem) != current_hash:
            return True
    return False
