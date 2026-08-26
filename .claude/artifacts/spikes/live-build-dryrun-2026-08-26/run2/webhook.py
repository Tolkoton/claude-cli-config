"""Accept a signed, timestamped webhook and hand it to a queue.

Does NOT: retry, dead-letter, or run a server.
The queue and the clock are passed in so delivery and expiry are observable
without infrastructure.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Protocol

#: A request signed more than this long ago is refused even if the signature is
#: valid — that is the whole point of replay protection.
MAX_AGE_SECONDS = 300


class Queue(Protocol):
    def put(self, payload: dict) -> None: ...


Reply = tuple[int, dict]


def handle_webhook(
    signature: str,
    timestamp: int,
    raw_body: bytes,
    secret: str,
    queue: Queue,
    now: int,
) -> Reply:
    """Verify first, then check freshness, then parse. Order matters: authenticating
    the raw bytes is what keeps attacker-controlled input out of the JSON parser, and
    signing covers the bytes as sent — re-serializing a parsed dict would change
    whitespace and key order and break genuine requests."""
    if not _signature_matches(signature, timestamp, raw_body, secret):
        return 401, {"error": "bad signature"}
    if not _is_fresh(timestamp, now):
        # Correctly signed and genuinely too old: a captured request being replayed.
        return 401, {"error": "timestamp too old"}
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        # Authentic sender, malformed message. Not a 401 — we know who this is.
        return 400, {"error": "body is not valid json"}
    queue.put(payload)
    return 202, {"queued": True}


def _signature_matches(
    signature: str, timestamp: int, raw_body: bytes, secret: str
) -> bool:
    """The timestamp is inside the signed material. If it were not, an attacker could
    replay a captured body with a fresh timestamp and it would still verify."""
    signed = f"{timestamp}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _is_fresh(timestamp: int, now: int) -> bool:
    return abs(now - timestamp) <= MAX_AGE_SECONDS
