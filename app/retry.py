"""Retry temporary failures with growing, randomised waits. Never retry permanent ones (ADR 004)."""

import random
import time
from collections.abc import Callable
from typing import TypeVar

import gspread
import httpx
import litellm

T = TypeVar("T")

# Temporary problems: trying again may well work.
_TRANSIENT_LLM = (
    litellm.exceptions.RateLimitError,
    litellm.exceptions.Timeout,
    litellm.exceptions.APIConnectionError,
    litellm.exceptions.ServiceUnavailableError,
    litellm.exceptions.InternalServerError,
)


class GaveUp(Exception):
    """All attempts failed (or the error was permanent). Carries how many tries were made."""

    def __init__(self, cause: Exception, attempts: int):
        super().__init__(f"{type(cause).__name__}: {cause}")
        self.cause = cause
        self.attempts = attempts


def _retryable_status(code: int) -> bool:
    return code == 429 or 500 <= code < 600


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, (*_TRANSIENT_LLM, TimeoutError, ConnectionError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return _retryable_status(exc.response.status_code)
    if isinstance(exc, httpx.TransportError):  # timeouts, refused connections, DNS failures
        return True
    if isinstance(exc, gspread.exceptions.APIError):
        return _retryable_status(getattr(exc.response, "status_code", 0))
    return False  # bad credentials, invalid output, bugs: retrying can't fix these


def backoff_delay(attempt: int, base: float = 1.0, cap: float = 30.0, rng=random.random) -> float:
    """'Full jitter': wait a random time between 0 and min(cap, base * 2^(attempt-1)) seconds."""
    return rng() * min(cap, base * 2 ** (attempt - 1))


def call_with_retry[T](
    fn: Callable[[], T], max_attempts: int = 4, sleep: Callable[[float], None] = time.sleep
) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            if not is_retryable(e) or attempt == max_attempts:
                raise GaveUp(e, attempt) from e
            sleep(backoff_delay(attempt))
    raise AssertionError("unreachable")
