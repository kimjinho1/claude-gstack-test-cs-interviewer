import asyncio
import json
import logging
import os
from dataclasses import dataclass

import httpx
from anthropic import AsyncAnthropic, APIStatusError, APITimeoutError

from .prompts import EVALUATION_PROMPT, FOLLOW_UP_PROMPT

logger = logging.getLogger(__name__)

@dataclass
class EvalResult:
    score: int
    feedback: str
    missed_points: list[str]

@dataclass
class FollowUpResult:
    follow_up_question: str

class AIProvider:
    def __init__(self):
        self.mode = os.getenv("AI_MODE", "cloud").lower()  # "local" | "cloud"
        self._claude = None
        if self.mode == "cloud":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self._claude = AsyncAnthropic(api_key=api_key)

    async def evaluate(self, question: str, answer: str) -> EvalResult:
        prompt = EVALUATION_PROMPT.format(question=question, answer=answer)
        if self.mode == "cloud" and self._claude:
            for attempt in range(3):
                try:
                    return await self._claude_evaluate(prompt)
                except (APITimeoutError,) as e:
                    logger.warning(f"Claude timeout attempt {attempt+1}: {e}")
                    await asyncio.sleep(2 ** attempt)
                except APIStatusError as e:
                    if e.status_code == 429:
                        logger.warning(f"Claude rate limit attempt {attempt+1}")
                        await asyncio.sleep(2 ** attempt)
                    else:
                        logger.error(f"Claude API error: {e}")
                        break
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Claude JSON parse error attempt {attempt+1}: {e}")
            # Fallback to Ollama
            logger.info("Falling back to Ollama")
            return await self._ollama_evaluate(prompt)
        else:
            return await self._ollama_evaluate(prompt)

    async def get_follow_up(self, question: str, answer: str, feedback: str) -> FollowUpResult:
        prompt = FOLLOW_UP_PROMPT.format(question=question, answer=answer, feedback=feedback)
        if self.mode == "cloud" and self._claude:
            try:
                return await self._claude_follow_up(prompt)
            except Exception as e:
                logger.warning(f"Claude follow-up failed: {e}")
        return await self._ollama_follow_up(prompt)

    async def _claude_evaluate(self, prompt: str) -> EvalResult:
        response = await self._claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(response.content[0].text)
        return EvalResult(
            score=int(data["score"]),
            feedback=data["feedback"],
            missed_points=data.get("missed_points", []),
        )

    async def _claude_follow_up(self, prompt: str) -> FollowUpResult:
        response = await self._claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(response.content[0].text)
        return FollowUpResult(follow_up_question=data["follow_up_question"])

    async def _ollama_evaluate(self, prompt: str) -> EvalResult:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": "llama3.1:8b", "prompt": prompt, "stream": False, "format": "json"},
                )
                resp.raise_for_status()
                data = json.loads(resp.json()["response"])
                return EvalResult(
                    score=int(data["score"]),
                    feedback=data["feedback"],
                    missed_points=data.get("missed_points", []),
                )
        except Exception as e:
            logger.error(f"Ollama evaluate failed: {e}")
            raise

    async def _ollama_follow_up(self, prompt: str) -> FollowUpResult:
        ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{ollama_url}/api/generate",
                    json={"model": "llama3.1:8b", "prompt": prompt, "stream": False, "format": "json"},
                )
                resp.raise_for_status()
                data = json.loads(resp.json()["response"])
                return FollowUpResult(follow_up_question=data["follow_up_question"])
        except Exception as e:
            logger.error(f"Ollama follow-up failed: {e}")
            return FollowUpResult(follow_up_question="더 자세히 설명해주세요.")
