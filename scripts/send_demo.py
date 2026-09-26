"""Send signed demo messages to the local webhook. Usage: uv run python scripts/send_demo.py"""

import json
import time

import httpx
from dotenv import dotenv_values

from app.signing import sign

env = dotenv_values(".env")
SECRET = env["WEBHOOK_SHARED_SECRET"]
URL = "http://localhost:8000/webhook"

good = json.dumps(
    {
        "name": "Raj",
        "email": "raj@acme.com",
        "message": "We need a marketing plan by next month, budget $10k.",
    }
).encode()


def send(label: str, body: bytes, timestamp: str | None = None, signature: str | None = None):
    ts = timestamp or str(int(time.time()))
    sig = signature or sign(SECRET, ts, body)
    r = httpx.post(URL, content=body, headers={"X-Timestamp": ts, "X-Signature": sig})
    print(f"{label:28} -> {r.status_code} {r.json()}")


send("1. genuine message", good)
send("2. same message again", good)
send("3. forged signature", good, signature="0" * 64)
send("4. valid but 1 hour old", good, timestamp=str(int(time.time()) - 3600))
send(
    "5. tampered body",
    good.replace(b"10k", b"1M"),
    signature=sign(SECRET, str(int(time.time())), good),
)
