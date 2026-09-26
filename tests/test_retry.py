import gspread
import httpx
import pytest

from app.retry import GaveUp, backoff_delay, call_with_retry, is_retryable


def http_error(code: int) -> httpx.HTTPStatusError:
    req = httpx.Request("POST", "https://x")
    return httpx.HTTPStatusError("boom", request=req, response=httpx.Response(code, request=req))


@pytest.mark.parametrize("code", [429, 500, 502, 503])
def test_temporary_http_errors_are_retryable(code):
    assert is_retryable(http_error(code))


@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_permanent_http_errors_are_not_retryable(code):
    assert not is_retryable(http_error(code))


def test_network_problems_are_retryable():
    assert is_retryable(httpx.ConnectTimeout("slow"))
    assert is_retryable(TimeoutError())
    assert is_retryable(ConnectionError())


def test_bugs_and_bad_data_are_not_retryable():
    assert not is_retryable(ValueError("bad"))
    assert not is_retryable(KeyError("x"))


def test_gspread_rate_limit_is_retryable_but_forbidden_is_not():
    def gs_error(code: int):
        resp = httpx.Response(code, json={"error": {"code": code, "message": "m", "status": "s"}})
        return gspread.exceptions.APIError(resp)

    assert is_retryable(gs_error(429))
    assert not is_retryable(gs_error(403))


def test_backoff_range_grows_and_is_capped():
    top = lambda n: backoff_delay(n, rng=lambda: 1.0)
    assert [top(1), top(2), top(3), top(4)] == [1, 2, 4, 8]
    assert top(10) == 30  # cap
    assert backoff_delay(3, rng=lambda: 0.0) == 0  # jitter can shorten the wait


def test_success_after_two_failures():
    calls, sleeps = [], []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("down")
        return "ok"

    assert call_with_retry(flaky, sleep=sleeps.append) == "ok"
    assert len(calls) == 3 and len(sleeps) == 2


def test_gives_up_after_max_attempts_and_reports_count():
    calls, sleeps = [], []

    def always_down():
        calls.append(1)
        raise ConnectionError("down")

    with pytest.raises(GaveUp) as info:
        call_with_retry(always_down, max_attempts=4, sleep=sleeps.append)
    assert info.value.attempts == 4 and len(calls) == 4
    assert len(sleeps) == 3  # no pointless wait after the last failure


def test_permanent_error_is_not_retried():
    calls = []

    def bad():
        calls.append(1)
        raise ValueError("invalid")

    with pytest.raises(GaveUp) as info:
        call_with_retry(bad, sleep=lambda s: None)
    assert len(calls) == 1 and info.value.attempts == 1
