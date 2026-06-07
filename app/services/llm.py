"""
app/services/llm.py
────────────────────
Groq async LLM client.
Provides two public functions:
  - complete()       → raw string response
  - complete_json()  → parsed + validated Pydantic model (retries up to 3×)
"""
import json
from typing import TypeVar, Type

from groq import AsyncGroq
from loguru import logger
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.exceptions import LLMProviderError

T = TypeVar("T", bound=BaseModel)

_client: AsyncGroq | None = None


def get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def complete(
    *,
    system: str,
    user: str,
    model: str,
    temperature: float = 0.7,
    json_mode: bool = True,
) -> str:
    """
    Send a chat completion request to Groq.
    Returns the raw string content of the response.
    """
    client = get_client()
    kwargs: dict = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
        max_tokens=4096,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug(f"LLM [{model}] tokens={response.usage.total_tokens if response.usage else '?'}")
        return content
    except Exception as exc:
        logger.error(f"LLM call failed: {exc}")
        raise LLMProviderError(
            f"Groq API error: {exc}",
            detail={"model": model},
        ) from exc


async def complete_json(
    *,
    system: str,
    user: str,
    model: str,
    schema: Type[T],
    temperature: float = 0.7,
    max_retries: int = 3,
) -> T:
    """
    Send a request and parse the JSON response into a Pydantic model.
    Retries up to max_retries times on JSON parse or validation failure.
    """
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            raw = await complete(
                system=system,
                user=user,
                model=model,
                temperature=temperature,
                json_mode=True,
            )
            data = json.loads(raw)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                f"LLM JSON parse failed (attempt {attempt}/{max_retries}): {exc}"
            )
            if attempt == max_retries:
                break
            # Slightly reduce temperature on retry to get more deterministic output
            temperature = max(0.1, temperature - 0.2)

    raise LLMProviderError(
        f"Failed to get valid JSON from model after {max_retries} attempts.",
        detail={"schema": schema.__name__, "last_error": str(last_error)},
    )
