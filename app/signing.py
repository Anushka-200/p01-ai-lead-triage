"""Request signing: proves a webhook call came from someone who knows our shared secret.

The sender signs "<timestamp>.<body>" with HMAC-SHA256. We recompute it and compare.
The timestamp is part of the signed text, so a captured request can't be replayed later.
"""

import hashlib
import hmac
import time


def sign(secret: str, timestamp: str, body: bytes) -> str:
    message = timestamp.encode() + b"." + body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify(
    secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
    max_age_s: int = 300,
    now: float | None = None,
) -> bool:
    if not secret:  # never accept anything if no secret is configured
        return False
    try:
        age = abs((now if now is not None else time.time()) - float(timestamp))
    except ValueError:
        return False
    if age > max_age_s:
        return False
    # compare_digest takes the same time however many characters match (no timing leak)
    return hmac.compare_digest(sign(secret, timestamp, body), signature)
