from app.signing import sign, verify

SECRET = "test-secret"
BODY = b'{"email":"a@x.com","message":"hi"}'
NOW = 1_000_000.0
TS = str(int(NOW))


def test_valid_signature_passes():
    assert verify(SECRET, TS, BODY, sign(SECRET, TS, BODY), now=NOW)


def test_wrong_secret_fails():
    assert not verify(SECRET, TS, BODY, sign("other-secret", TS, BODY), now=NOW)


def test_tampered_body_fails():
    sig = sign(SECRET, TS, BODY)
    assert not verify(SECRET, TS, BODY + b" ", sig, now=NOW)


def test_old_timestamp_fails_even_with_valid_signature():
    old = str(int(NOW) - 3600)
    assert not verify(SECRET, old, BODY, sign(SECRET, old, BODY), now=NOW)


def test_future_timestamp_fails():
    future = str(int(NOW) + 3600)
    assert not verify(SECRET, future, BODY, sign(SECRET, future, BODY), now=NOW)


def test_garbage_timestamp_fails():
    assert not verify(SECRET, "abc", BODY, sign(SECRET, "abc", BODY), now=NOW)


def test_empty_secret_never_accepts():
    assert not verify("", TS, BODY, sign("", TS, BODY), now=NOW)
