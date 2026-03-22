import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.ai_provider import AIProvider, EvalResult

@pytest.fixture
def cloud_provider(monkeypatch):
    monkeypatch.setenv("AI_MODE", "cloud")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    provider = AIProvider()
    return provider

@pytest.fixture
def local_provider(monkeypatch):
    monkeypatch.setenv("AI_MODE", "local")
    return AIProvider()

@pytest.mark.asyncio
async def test_ollama_evaluate_success(local_provider):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "response": json.dumps({"score": 8, "feedback": "좋습니다", "missed_points": []})
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        result = await local_provider.evaluate("TCP란?", "연결형 프로토콜입니다")

    assert result.score == 8
    assert result.feedback == "좋습니다"

@pytest.mark.asyncio
async def test_cloud_fallback_to_ollama_on_timeout(cloud_provider):
    from anthropic import APITimeoutError

    mock_ollama_response = MagicMock()
    mock_ollama_response.json.return_value = {
        "response": json.dumps({"score": 6, "feedback": "Ollama fallback", "missed_points": ["핵심 포인트"]})
    }
    mock_ollama_response.raise_for_status = MagicMock()

    # Claude times out 3 times
    cloud_provider._claude = MagicMock()
    cloud_provider._claude.messages = MagicMock()
    cloud_provider._claude.messages.create = AsyncMock(side_effect=APITimeoutError(request=MagicMock()))

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_ollama_response)
        result = await cloud_provider.evaluate("TCP란?", "연결형입니다")

    assert result.score == 6
    assert result.feedback == "Ollama fallback"

@pytest.mark.asyncio
async def test_sm2_score_boundary():
    """score=7 is pass, score=6 is fail"""
    from backend.sm2 import sm2_update
    pass_result = sm2_update(2.5, 1, 0, 7)
    fail_result = sm2_update(2.5, 1, 0, 6)
    assert pass_result.repetitions == 1
    assert fail_result.repetitions == 0
