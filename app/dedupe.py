import hashlib
import json
import re


def normalize(text: str) -> str:
    """Make trivial differences (case, spaces, line breaks) disappear before hashing."""
    return re.sub(r"\s+", " ", text.strip().lower())


def fingerprint(sender: str, body: str) -> str:
    """Same sender + same body (after tidying) always gives the same 64-character code.

    We hash a JSON list, not 'sender|body', so ('a|b', 'c') and ('a', 'b|c') can never collide.
    """
    payload = json.dumps([normalize(sender), normalize(body)])
    return hashlib.sha256(payload.encode()).hexdigest()
