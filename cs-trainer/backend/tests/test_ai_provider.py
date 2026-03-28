import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.ai_provider import AIProvider, EvalResult, FollowUpResult


# ─── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def cloud_provider(monkeypatch):
    monkeypatch.setenv("AI_MODE", "cloud")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    return AIProvider()


@pytest.fixture
def local_provider(monkeypatch):
    monkeypatch.setenv("AI_MODE", "local")
    return AIProvider()


# ─── _parse_json ─────────────────────────────────────────────────────────────

class TestParseJson:
    def test_plain_json(self):
        result = AIProvider._parse_json('{"score": 8, "feedback": "good"}')
        assert result["score"] == 8

    def test_json_code_block(self):
        text = '```json\n{"score": 7, "feedback": "ok"}\n```'
        result = AIProvider._parse_json(text)
        assert result["score"] == 7

    def test_code_block_no_lang(self):
        text = '```\n{"score": 5}\n```'
        result = AIProvider._parse_json(text)
        assert result["score"] == 5

    def test_whitespace_trimmed(self):
        result = AIProvider._parse_json('  {"score": 9}  ')
        assert result["score"] == 9

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            AIProvider._parse_json("not json at all")


# ─── Ollama evaluate ─────────────────────────────────────────────────────────

class TestOllamaEvaluate:
    @pytest.mark.asyncio
    async def test_success(self, local_provider):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": json.dumps({"score": 8, "feedback": "좋습니다", "missed_points": []})
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await local_provider.evaluate("TCP란?", "연결형 프로토콜입니다")
        assert result.score == 8
        assert result.feedback == "좋습니다"
        assert result.missed_points == []

    @pytest.mark.asyncio
    async def test_missed_points_included(self, local_provider):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": json.dumps({"score": 5, "feedback": "부족", "missed_points": ["흐름제어", "혼잡제어"]})
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await local_provider.evaluate("TCP란?", "모릅니다")
        assert result.missed_points == ["흐름제어", "혼잡제어"]

    @pytest.mark.asyncio
    async def test_network_error_raises(self, local_provider):
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            with pytest.raises(Exception, match="Connection refused"):
                await local_provider.evaluate("TCP란?", "모릅니다")


# ─── Claude evaluate ─────────────────────────────────────────────────────────

class TestCloudEvaluate:
    def _make_response(self, payload: dict, as_codeblock: bool = False):
        resp = MagicMock()
        resp.content = [MagicMock()]
        if as_codeblock:
            resp.content[0].text = f"```json\n{json.dumps(payload)}\n```"
        else:
            resp.content[0].text = json.dumps(payload)
        return resp

    @pytest.mark.asyncio
    async def test_success(self, cloud_provider):
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(
            return_value=self._make_response({"score": 9, "feedback": "훌륭합니다", "missed_points": []})
        )
        result = await cloud_provider.evaluate("TCP란?", "연결형 프로토콜")
        assert result.score == 9

    @pytest.mark.asyncio
    async def test_parses_codeblock_response(self, cloud_provider):
        """Claude가 ```json 블록으로 응답해도 파싱돼야 한다"""
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(
            return_value=self._make_response(
                {"score": 7, "feedback": "괜찮습니다", "missed_points": []}, as_codeblock=True
            )
        )
        result = await cloud_provider.evaluate("TCP란?", "연결형")
        assert result.score == 7

    @pytest.mark.asyncio
    async def test_timeout_falls_back_to_ollama(self, cloud_provider):
        from anthropic import APITimeoutError
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": json.dumps({"score": 6, "feedback": "Ollama 응답", "missed_points": []})
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await cloud_provider.evaluate("TCP란?", "모름")
        assert result.feedback == "Ollama 응답"

    @pytest.mark.asyncio
    async def test_rate_limit_falls_back_to_ollama(self, cloud_provider):
        from anthropic import APIStatusError
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(
            side_effect=APIStatusError("rate limit", response=MagicMock(status_code=429), body={})
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": json.dumps({"score": 5, "feedback": "ollama fallback", "missed_points": []})
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await cloud_provider.evaluate("TCP란?", "모름")
        assert result.score == 5

    @pytest.mark.asyncio
    async def test_all_fail_raises(self, cloud_provider):
        """Claude + Ollama 모두 실패하면 예외"""
        from anthropic import APITimeoutError
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Ollama down")
            )
            with pytest.raises(Exception):
                await cloud_provider.evaluate("TCP란?", "모름")


# ─── get_follow_up ────────────────────────────────────────────────────────────

class TestGetFollowUp:
    @pytest.mark.asyncio
    async def test_cloud_success(self, cloud_provider):
        resp = MagicMock()
        resp.content = [MagicMock()]
        resp.content[0].text = json.dumps({"follow_up_question": "더 설명해주세요"})
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(return_value=resp)
        result = await cloud_provider.get_follow_up("TCP란?", "모름", "부족합니다")
        assert result.follow_up_question == "더 설명해주세요"

    @pytest.mark.asyncio
    async def test_cloud_falls_back_to_ollama_on_error(self, cloud_provider):
        cloud_provider._claude = MagicMock()
        cloud_provider._claude.messages.create = AsyncMock(side_effect=Exception("fail"))
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "response": json.dumps({"follow_up_question": "Ollama 추가질문"})
        }
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
            result = await cloud_provider.get_follow_up("TCP란?", "모름", "부족")
        assert result.follow_up_question == "Ollama 추가질문"

    @pytest.mark.asyncio
    async def test_ollama_all_fail_returns_default(self, local_provider):
        """Ollama까지 실패하면 기본 메시지 반환"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("down")
            )
            result = await local_provider.get_follow_up("TCP란?", "모름", "부족")
        assert result.follow_up_question == "더 자세히 설명해주세요."
