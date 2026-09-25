"""Langfuse tracing. If keys are missing, everything quietly becomes a no-op."""

from contextlib import nullcontext

from langfuse import Langfuse

from app.settings import settings

_client: Langfuse | None = None
if settings.langfuse_public_key and settings.langfuse_secret_key:
    _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


def observation(**kwargs):
    """Context manager: a traced step (span or LLM generation)."""
    if _client is None:
        return nullcontext(None)
    return _client.start_as_current_observation(**kwargs)


def flush() -> None:
    """Send buffered traces now. Call before a short script exits."""
    if _client is not None:
        _client.flush()
