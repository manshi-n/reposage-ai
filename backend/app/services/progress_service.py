"""
Cross-process analysis progress tracking.

Analyses run either inline (BackgroundTasks, same process as the API) or
via a Celery worker (a separate OS process). A plain in-memory dict can
only be seen by the process that wrote to it, so progress pushed from a
Celery worker was never visible to the FastAPI process serving the
`/analyses/{id}/ws` websocket. Redis is already a dependency (see
app/api/routes/auth.py), so it's used here as the shared store instead.

Events are appended to a per-analysis Redis list. Consumers (the
websocket handler) track how many entries they've already read and only
fetch new ones, the same pattern the old in-memory queue used.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import redis

from app.core.config import settings

PROGRESS_KEY_PREFIX = "analysis_progress:"
PROGRESS_TTL_SECONDS = 3600  # 1 hour is comfortably longer than any analysis run


def _redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _key(analysis_id: str) -> str:
    return f"{PROGRESS_KEY_PREFIX}{analysis_id}"


def push_progress(
    analysis_id: str,
    status: str,
    percent: int,
    error_message: Optional[str] = None,
) -> None:
    """Append a progress event. Safe to call from any process (API or worker)."""
    event: Dict[str, Any] = {
        "status": status,
        "progress_percent": percent,
    }

    if error_message:
        event["error_message"] = error_message

    try:
        client = _redis_client()
        key = _key(analysis_id)
        client.rpush(key, json.dumps(event))
        client.expire(key, PROGRESS_TTL_SECONDS)
    except redis.RedisError:
        # Progress reporting is best-effort; a Redis hiccup shouldn't fail the analysis.
        pass


def get_progress_events(
    analysis_id: str,
    start_index: int = 0,
) -> List[Dict[str, Any]]:
    """Return every progress event from start_index onward."""
    try:
        client = _redis_client()
        raw_events = client.lrange(_key(analysis_id), start_index, -1)
    except redis.RedisError:
        return []

    events: List[Dict[str, Any]] = []
    for raw_event in raw_events:
        try:
            events.append(json.loads(raw_event))
        except ValueError:
            continue

    return events