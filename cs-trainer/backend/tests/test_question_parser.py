import pytest
from pathlib import Path
import tempfile
import textwrap
from backend.question_parser import parse_questions_from_file, parse_all_questions, needs_reparse

@pytest.fixture
def tmp_docs(tmp_path):
    part_dir = tmp_path / "01-network"
    part_dir.mkdir()
    return tmp_path, part_dir

def test_parse_normal(tmp_docs):
    tmp_path, part_dir = tmp_docs
    md = part_dir / "01-01-test.md"
    md.write_text(textwrap.dedent("""
        ## 면접 예상 질문

        - Q: TCP와 UDP의 차이는?
          A: TCP는 연결형, UDP는 비연결형입니다.

        - Q: 3-way handshake란?
          A: SYN, SYN-ACK, ACK 3단계로 연결을 수립합니다.
    """))
    result = parse_questions_from_file(md)
    assert len(result) == 2
    assert result[0]["question_id"] == "01-01-test:1"
    assert "TCP" in result[0]["question_text"]
    assert result[0]["part"] == "01-network"

def test_parse_no_questions(tmp_docs, caplog):
    _, part_dir = tmp_docs
    md = part_dir / "01-02-empty.md"
    md.write_text("# 빈 파일\n\n개념만 있고 질문 없음\n")
    import logging
    with caplog.at_level(logging.WARNING):
        result = parse_questions_from_file(md)
    assert result == []
    assert "No Q:/A:" in caplog.text

def test_needs_reparse_empty_cache(tmp_docs):
    tmp_path, _ = tmp_docs
    assert needs_reparse(tmp_path, []) is True

def test_parse_all_skips_curriculum(tmp_docs):
    tmp_path, part_dir = tmp_docs
    # Add curriculum.md to root - should be skipped
    (tmp_path / "curriculum.md").write_text("# curriculum")
    md = part_dir / "01-01-test.md"
    md.write_text("- Q: Test question?\n  A: Test answer.\n")
    result = parse_all_questions(tmp_path)
    assert all(q["file_ref"] != "curriculum.md" for q in result)
