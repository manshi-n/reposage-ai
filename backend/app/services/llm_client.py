"""
Thin wrapper around the Groq API used by every AI agent.

All AI features call `ask()`. If GROQ_API_KEY is missing, the function
returns a clear fallback message so static repository analysis can still
complete without crashing.
"""

from typing import Optional

from groq import Groq

from app.core.config import settings


_client: Optional[Groq] = None


def _get_client() -> Optional[Groq]:
    global _client

    if not settings.GROQ_API_KEY:
        return None

    if _client is None:
        _client = Groq(
            api_key=settings.GROQ_API_KEY
        )

    return _client


def ask(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
) -> str:
    client = _get_client()

    if client is None:
        return (
            "[AI agent unavailable: set GROQ_API_KEY in backend/.env "
            "to enable architecture summaries, documentation, test "
            "generation, refactoring, and repository chat.]"
        )

    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.2,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content

    if not content:
        return "[AI agent returned an empty response.]"

    return content.strip()