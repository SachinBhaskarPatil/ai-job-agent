"""OpenAI API client wrapper."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import APIError, OpenAI, OpenAIError

from config import OpenAIConfig

logger = logging.getLogger(__name__)


class OpenAIClientError(Exception):
    """Raised when an OpenAI API call fails."""


class OpenAIClient:
    """Reusable helper around the OpenAI SDK."""

    def __init__(self, config: OpenAIConfig) -> None:
        self._config = config
        self._client = OpenAI(api_key=config.api_key)

    @property
    def model(self) -> str:
        return self._config.model

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        """Send a chat completion request and return the assistant message text."""
        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens

            response = self._client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            logger.debug("OpenAI chat completion succeeded (%d chars)", len(content))
            return content.strip()
        except APIError as exc:
            logger.exception("OpenAI API error")
            raise OpenAIClientError(str(exc)) from exc
        except OpenAIError as exc:
            logger.exception("OpenAI client error")
            raise OpenAIClientError(str(exc)) from exc

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Request a JSON object response and parse it."""
        raw = self.chat(
            system_prompt,
            user_prompt,
            temperature=temperature,
        )
        cleaned = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.exception("Failed to parse OpenAI JSON response")
            raise OpenAIClientError("OpenAI returned invalid JSON") from exc

        if not isinstance(parsed, dict):
            raise OpenAIClientError("OpenAI JSON response must be an object")

        return parsed
